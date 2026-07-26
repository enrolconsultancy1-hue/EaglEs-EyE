"""ConnectorSchedulerService — background periodic synchronization.

Supports periodic sync, manual sync, health checks, exponential backoff,
and configurable retry policies. Disabled by default.
"""

import threading
import time
from typing import Optional, Callable

from services.service import Service


class ScheduleEntry:
    def __init__(self, connector_id: str, interval_seconds: float,
                 sync_fn: Callable, enabled: bool = True):
        self.connector_id = connector_id
        self.interval_seconds = interval_seconds
        self.sync_fn = sync_fn
        self.enabled = enabled
        self.last_run: float = 0.0
        self.consecutive_failures: int = 0
        self.max_backoff_seconds: float = 3600.0
        self._timer: Optional[threading.Timer] = None

    def should_run(self) -> bool:
        if not self.enabled:
            return False
        elapsed = time.time() - self.last_run
        backoff = min(self.interval_seconds * (2 ** self.consecutive_failures),
                      self.max_backoff_seconds)
        return elapsed >= backoff


class ConnectorSchedulerService(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self._entries: dict[str, ScheduleEntry] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._check_interval = 5.0

    def start(self):
        super().start()
        config = self.kernel.get_config() or {}
        scheduler_config = config.get("connector_scheduler", {})
        if scheduler_config.get("enabled", False):
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
        print("[CONNECTOR SCHEDULER] Ready.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        super().stop()

    def register(self, connector_id: str, interval_seconds: float,
                 sync_fn: Callable, enabled: bool = True):
        with self._lock:
            self._entries[connector_id] = ScheduleEntry(
                connector_id=connector_id, interval_seconds=interval_seconds,
                sync_fn=sync_fn, enabled=enabled,
            )

    def unregister(self, connector_id: str):
        with self._lock:
            self._entries.pop(connector_id, None)

    def trigger_sync(self, connector_id: str) -> Optional[dict]:
        with self._lock:
            entry = self._entries.get(connector_id)
            if not entry:
                return {"error": f"No schedule entry for connector: {connector_id}"}
        try:
            result = entry.sync_fn()
            entry.last_run = time.time()
            entry.consecutive_failures = 0
            return {"connector_id": connector_id, "status": "completed", "result": result}
        except Exception as e:
            entry.consecutive_failures += 1
            return {"connector_id": connector_id, "status": "failed", "error": str(e)}

    def get_schedule(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "connector_id": e.connector_id,
                    "interval_seconds": e.interval_seconds,
                    "enabled": e.enabled,
                    "last_run": e.last_run,
                    "consecutive_failures": e.consecutive_failures,
                }
                for e in self._entries.values()
            ]

    def _run_loop(self):
        while self._running:
            with self._lock:
                for entry in list(self._entries.values()):
                    if entry.should_run():
                        try:
                            result = entry.sync_fn()
                            entry.last_run = time.time()
                            entry.consecutive_failures = 0
                        except Exception:
                            entry.consecutive_failures += 1
            time.sleep(self._check_interval)
