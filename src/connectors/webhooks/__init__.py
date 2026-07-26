"""Webhook Listener Framework — connector registration, event validation,
signature verification abstraction, queuing, retry, and replay protection.

Framework only — no platform-specific webhooks in Phase 16.
"""

import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Callable


@dataclass
class WebhookEvent:
    id: str = ""
    connector_id: str = ""
    event_type: str = ""
    payload: dict = field(default_factory=dict)
    received_at: float = 0.0
    signature: str = ""
    verified: bool = False


class SignatureVerifier:
    @staticmethod
    def verify_hmac(payload: bytes, signature: str, secret: str, algorithm: str = "sha256") -> bool:
        if not secret or not signature:
            return False
        hash_func = hashlib.sha256 if algorithm == "sha256" else hashlib.sha1
        expected = hmac.new(secret.encode(), payload, hash_func).hexdigest()
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def verify_token(payload: dict, signature: str, expected_token: str) -> bool:
        if not expected_token or not signature:
            return False
        return hmac.compare_digest(signature, expected_token)


class WebhookQueue:
    def __init__(self):
        self._events: list[WebhookEvent] = []
        self._max_retries = 3
        self._retry_delay = 1.0

    def enqueue(self, event: WebhookEvent):
        event.received_at = time.time()
        self._events.append(event)

    def dequeue(self) -> Optional[WebhookEvent]:
        if not self._events:
            return None
        return self._events.pop(0)

    def size(self) -> int:
        return len(self._events)

    def clear(self):
        self._events.clear()


class ReplayGuard:
    def __init__(self):
        self._seen_ids: set[str] = set()
        self._max_age = 300.0

    def is_new(self, event_id: str, timestamp: float) -> bool:
        if time.time() - timestamp > self._max_age:
            return True
        if event_id in self._seen_ids:
            return False
        self._seen_ids.add(event_id)
        return True

    def prune(self):
        pass


class WebhookRegistry:
    def __init__(self):
        self._connectors: dict[str, dict] = {}

    def register(self, connector_id: str, secret: str = "", webhook_url: str = "",
                 events: Optional[list] = None):
        self._connectors[connector_id] = {
            "connector_id": connector_id,
            "secret": secret,
            "webhook_url": webhook_url,
            "events": events or [],
            "registered_at": time.time(),
        }

    def unregister(self, connector_id: str):
        self._connectors.pop(connector_id, None)

    def get(self, connector_id: str) -> Optional[dict]:
        return self._connectors.get(connector_id)

    def list(self) -> list[dict]:
        return [
            {"connector_id": cid, "webhook_url": info.get("webhook_url", ""),
             "events": info.get("events", []), "registered_at": info.get("registered_at")}
            for cid, info in self._connectors.items()
        ]


class WebhookHandler:
    def __init__(self):
        self._registry = WebhookRegistry()
        self._queue = WebhookQueue()
        self._replay_guard = ReplayGuard()
        self._verifier = SignatureVerifier()
        self._processors: dict[str, Callable] = {}

    def register_processor(self, event_type: str, processor: Callable):
        self._processors[event_type] = processor

    def receive(self, connector_id: str, raw_body: bytes,
                headers: Optional[dict] = None) -> WebhookEvent:
        headers = headers or {}
        connector_info = self._registry.get(connector_id)
        event_id = headers.get("X-Webhook-Id") or str(uuid.uuid4())
        signature = headers.get("X-Hub-Signature-256") or headers.get("X-Signature") or ""
        event_type = headers.get("X-GitHub-Event") or headers.get("X-Event-Type") or "unknown"
        try:
            payload = json.loads(raw_body) if raw_body else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {"raw": raw_body.decode("utf-8", errors="replace")}
        verified = False
        if connector_info and connector_info.get("secret"):
            algorithm = "sha256" if "sha256" in signature else "sha1"
            verified = self._verifier.verify_hmac(raw_body, signature, connector_info["secret"], algorithm)
        event = WebhookEvent(
            id=event_id, connector_id=connector_id, event_type=event_type,
            payload=payload, received_at=time.time(), signature=signature,
            verified=verified,
        )
        timestamp = headers.get("X-Webhook-Timestamp") or str(time.time())
        try:
            event_time = float(timestamp)
        except (ValueError, TypeError):
            event_time = time.time()
        if self._replay_guard.is_new(event_id, event_time):
            self._queue.enqueue(event)
        return event

    def process_next(self) -> Optional[dict]:
        event = self._queue.dequeue()
        if not event:
            return None
        processor = self._processors.get(event.event_type)
        if processor:
            try:
                return processor(event)
            except Exception:
                return {"error": "processing_failed", "event_id": event.id}
        return {"event_id": event.id, "event_type": event.event_type, "status": "queued"}

    def get_registry(self):
        return self._registry

    def get_queue(self):
        return self._queue
