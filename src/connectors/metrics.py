"""Connector Metrics — per-connector sync duration, API requests, failures,
retries, evidence created, throughput, and connector uptime.

Thread-safe counters exposed through the ConnectorManager and MCP tools.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConnectorMetricsSnapshot:
    connector_id: str = ""
    sync_count: int = 0
    total_sync_duration_ms: float = 0.0
    api_requests: int = 0
    failures: int = 0
    retries: int = 0
    evidence_created: int = 0
    observations: int = 0
    throughput_items_per_sec: float = 0.0
    uptime_seconds: float = 0.0
    last_sync_at: float = 0.0
    last_error_at: float = 0.0
    last_error_message: str = ""

    def to_dict(self) -> dict:
        return {
            "connector_id": self.connector_id,
            "sync_count": self.sync_count,
            "total_sync_duration_ms": self.total_sync_duration_ms,
            "api_requests": self.api_requests,
            "failures": self.failures,
            "retries": self.retries,
            "evidence_created": self.evidence_created,
            "observations": self.observations,
            "throughput_items_per_sec": self.throughput_items_per_sec,
            "uptime_seconds": self.uptime_seconds,
            "last_sync_at": self.last_sync_at,
            "last_error_at": self.last_error_at,
            "last_error_message": self.last_error_message,
        }


class MetricsCollector:
    def __init__(self):
        self._lock = threading.Lock()
        self._metrics: dict[str, ConnectorMetricsSnapshot] = {}
        self._started_at: dict[str, float] = {}

    def register_connector(self, connector_id: str):
        with self._lock:
            if connector_id not in self._metrics:
                self._metrics[connector_id] = ConnectorMetricsSnapshot(connector_id=connector_id)
                self._started_at[connector_id] = time.time()

    def record_sync(self, connector_id: str, duration_ms: float, items: int):
        with self._lock:
            m = self._metrics.get(connector_id)
            if m:
                m.sync_count += 1
                m.total_sync_duration_ms += duration_ms
                m.evidence_created += items
                m.last_sync_at = time.time()
                elapsed = time.time() - self._started_at.get(connector_id, time.time())
                m.throughput_items_per_sec = m.evidence_created / elapsed if elapsed > 0 else 0.0

    def record_api_request(self, connector_id: str):
        with self._lock:
            m = self._metrics.get(connector_id)
            if m:
                m.api_requests += 1

    def record_failure(self, connector_id: str, error_message: str = ""):
        with self._lock:
            m = self._metrics.get(connector_id)
            if m:
                m.failures += 1
                m.last_error_at = time.time()
                m.last_error_message = error_message

    def record_retry(self, connector_id: str):
        with self._lock:
            m = self._metrics.get(connector_id)
            if m:
                m.retries += 1

    def record_observation(self, connector_id: str):
        with self._lock:
            m = self._metrics.get(connector_id)
            if m:
                m.observations += 1

    def get_metrics(self, connector_id: str) -> Optional[ConnectorMetricsSnapshot]:
        with self._lock:
            m = self._metrics.get(connector_id)
            if m:
                m.uptime_seconds = time.time() - self._started_at.get(connector_id, time.time())
                return m
            return None

    def get_all_metrics(self) -> dict[str, dict]:
        with self._lock:
            now = time.time()
            result = {}
            for cid, m in self._metrics.items():
                m.uptime_seconds = now - self._started_at.get(cid, now)
                result[cid] = m.to_dict()
            return result

    def get_health_details(self, connector_id: str, health_dict: Optional[dict] = None) -> dict:
        metrics = self.get_metrics(connector_id)
        base = metrics.to_dict() if metrics else {"connector_id": connector_id}
        if health_dict:
            base["health"] = health_dict
        return base
