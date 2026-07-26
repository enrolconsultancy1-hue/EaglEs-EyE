"""Generic REST Connector — reusable base for REST-based project systems.

Supports GET endpoints, authentication abstraction, pagination, retry,
health monitoring, incremental synchronization, and JSON normalization.
Future connectors inherit from this whenever practical.
"""

import json
import time
import urllib.error
import urllib.request
from typing import Optional, Callable
from urllib.parse import urlencode

from connectors.connector import Connector
from connectors.auth import ConnectorAuth, PATAuth, BearerTokenAuth, APIKeyAuth
from connectors.metrics import MetricsCollector
from connectors.sync import SyncEngine, SyncStore
from connectors.models import (
    Observation, Evidence, Source, RawPayload, NormalizedPayload,
    TraceInformation, Artifact,
)
from connectors.exceptions import ConnectorTimeoutError


class PaginationHelper:
    @staticmethod
    def parse_link_header(link_header: str) -> dict[str, str]:
        links = {}
        if not link_header:
            return links
        for part in link_header.split(","):
            match = __import__("re").match(r'<([^>]+)>;\s*rel="([^"]+)"', part.strip())
            if match:
                links[match.group(2)] = match.group(1)
        return links

    @staticmethod
    def extract_next_url(response_headers: dict, response_data: dict, page: int) -> Optional[str]:
        link_header = response_headers.get("Link", "")
        if link_header:
            links = PaginationHelper.parse_link_header(link_header)
            if "next" in links:
                return links["next"]
        return None


class RetryPolicy:
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor

    def get_delay(self, attempt: int) -> float:
        return self.base_delay * (self.backoff_factor ** attempt)


class RESTConnector(Connector):
    id: str = "rest"
    name: str = "REST Connector"
    version: str = "1.0.0"
    vendor: str = "EaglEs EyE"
    description: str = "Generic REST API connector"
    capabilities: list = ["api"]
    permissions: list = ["read", "observe"]

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config or {})
        self._base_url = self.config.get("base_url", "")
        self._auth: Optional[ConnectorAuth] = None
        self._metrics = MetricsCollector()
        self._sync_engine = SyncEngine(store=SyncStore())
        self._retry_policy = RetryPolicy(
            max_retries=self.config.get("max_retries", 3),
            base_delay=self.config.get("retry_base_delay", 1.0),
            backoff_factor=self.config.get("retry_backoff", 2.0),
        )
        self._setup_auth()
        self._metrics.register_connector(self.id)

    def _setup_auth(self):
        auth_config = self.config.get("auth", {})
        provider = auth_config.get("provider", "")
        if provider == "pat":
            self._auth = PATAuth(token=auth_config.get("token", ""))
        elif provider == "bearer":
            self._auth = BearerTokenAuth(token=auth_config.get("token", ""))
        elif provider == "api_key":
            self._auth = APIKeyAuth(
                api_key=auth_config.get("api_key", ""),
                header_name=auth_config.get("header_name", "X-API-Key"),
            )
        else:
            self._auth = None

    def connect(self) -> bool:
        self._metrics.register_connector(self.id)
        if self._auth:
            return self._auth.authenticate()
        return True

    def disconnect(self) -> bool:
        return True

    def discover(self) -> list:
        return [Source(id=self._base_url, type="rest_api",
                       path=self._base_url, version=self.version)]

    def observe(self) -> list:
        return []

    def collect(self) -> list:
        return []

    def _request(self, method: str, endpoint: str,
                 params: Optional[dict] = None,
                 headers: Optional[dict] = None,
                 data: Optional[dict] = None,
                 timeout: int = 30) -> tuple[int, dict, dict]:
        url = f"{self._base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        if params:
            url += "?" + urlencode(params)
        req_headers = {"Accept": "application/json"}
        if self._auth:
            req_headers.update(self._auth.get_headers())
        if headers:
            req_headers.update(headers)
        body = json.dumps(data).encode() if data else None
        if body:
            req_headers["Content-Type"] = "application/json"
        last_error = None
        for attempt in range(self._retry_policy.max_retries + 1):
            try:
                req = urllib.request.Request(url, data=body, headers=req_headers,
                                              method=method)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    response_data = json.loads(resp.read().decode())
                    response_headers = dict(resp.headers)
                    self._metrics.record_api_request(self.id)
                    return resp.status, response_data, response_headers
            except urllib.error.HTTPError as e:
                self._metrics.record_api_request(self.id)
                status = e.code
                if status in (429, 502, 503, 504) and attempt < self._retry_policy.max_retries:
                    delay = self._retry_policy.get_delay(attempt)
                    self._metrics.record_retry(self.id)
                    time.sleep(delay)
                    last_error = e
                    continue
                error_body = e.read().decode() if e.fp else str(e)
                try:
                    error_data = json.loads(error_body)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    error_data = {"error": error_body}
                return status, error_data, dict(e.headers)
            except urllib.error.URLError as e:
                self._metrics.record_failure(self.id, str(e))
                if attempt < self._retry_policy.max_retries:
                    delay = self._retry_policy.get_delay(attempt)
                    self._metrics.record_retry(self.id)
                    time.sleep(delay)
                    last_error = e
                    continue
                return 0, {"error": f"Connection failed: {e.reason}"}, {}
            except Exception as e:
                self._metrics.record_failure(self.id, str(e))
                return 0, {"error": str(e)}, {}
        self._metrics.record_failure(self.id, str(last_error))
        return 0, {"error": f"Max retries exceeded: {last_error}"}, {}

    def _get(self, endpoint: str, params: Optional[dict] = None,
             headers: Optional[dict] = None, timeout: int = 30) -> tuple[int, dict, dict]:
        return self._request("GET", endpoint, params=params, headers=headers, timeout=timeout)

    def _paginate(self, endpoint: str, params: Optional[dict] = None,
                  headers: Optional[dict] = None,
                  max_pages: int = 100) -> list[dict]:
        all_results = []
        page = 1
        params = dict(params or {})
        while page <= max_pages:
            status, data, resp_headers = self._get(endpoint, params=params, headers=headers)
            if status < 200 or status >= 300:
                break
            if isinstance(data, list):
                all_results.extend(data)
            elif isinstance(data, dict):
                items = data.get("items") or data.get("data") or data.get("results") or data
                if isinstance(items, list):
                    all_results.extend(items)
                else:
                    all_results.append(data)
            next_url = PaginationHelper.extract_next_url(resp_headers, data, page)
            if not next_url:
                if isinstance(data, list) and len(data) == 0:
                    break
                if isinstance(data, dict) and "next" in data.get("pagination", {}):
                    params["page"] = page + 1
                    page += 1
                    continue
                break
            page += 1
        return all_results

    def get_metrics_collector(self):
        return self._metrics

    def get_sync_engine(self):
        return self._sync_engine
