"""Event-driven semantic awareness — observes events and surfaces evidence-backed patterns.

Subscribes only to existing EventBus events. Never infers intent, motivation,
hidden reasoning, or future actions. Produces awareness signals that cite the
triggering evidence.
"""

import json
from datetime import datetime, timezone

from services.service import Service


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


SIGNAL_TTL_DAYS = 7


class SemanticAwarenessService(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None
        self.embedding = None
        self._recent_edits = []
        self._max_recent = 100
        self._min_similar_count = 3
        self._enabled = True

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        if not self.store:
            raise RuntimeError("SemanticAwarenessService requires KnowledgeStoreService.")
        self.embedding = self.kernel.get_service("EmbeddingService")
        config = self.kernel.get_config()
        self._enabled = config.get("awareness", {}).get("enabled", True)
        self._min_similar_count = int(config.get("awareness", {}).get("min_similar_count", 3))
        if self._enabled:
            self.kernel.event_bus.subscribe("FILE_CREATED", self._on_event)
            self.kernel.event_bus.subscribe("FILE_MODIFIED", self._on_event)
            print("[AWARENESS] Ready.")
        else:
            print("[AWARENESS] Disabled by configuration.")

    def stop(self):
        self._enabled = False
        super().stop()

    def _on_event(self, data):
        if not self._enabled:
            return
        path = (data or {}).get("path", "")
        if not path:
            return
        event_type = (data or {}).get("event_type", "FILE_MODIFIED")
        self._recent_edits.append({"path": path, "event_type": event_type, "timestamp": _utc_now()})
        if len(self._recent_edits) > self._max_recent:
            self._recent_edits.pop(0)
        self._check_module_cluster(path)

    def _check_module_cluster(self, path):
        module = self._module_from_path(path)
        if not module:
            return
        count = sum(1 for e in self._recent_edits if self._module_from_path(e["path"]) == module)
        if count >= self._min_similar_count:
            if not self._signal_exists("module_cluster", module, count):
                self._record_signal(
                    signal_type="module_cluster",
                    summary="%d similar edits detected in module %s" % (count, module),
                    evidence_citations=[{"path": e["path"], "timestamp": e["timestamp"]} for e in self._recent_edits[-count:]],
                    payload={"module": module, "edit_count": count},
                )

    @staticmethod
    def _module_from_path(path):
        parts = path.replace("\\", "/").split("/")
        for i, part in enumerate(parts):
            if part == "src":
                return "/".join(parts[i:])
        return None

    def _signal_exists(self, signal_type, key, count):
        with self.store.transaction() as connection:
            row = connection.execute(
                "SELECT 1 FROM awareness_signals WHERE signal_type = ? AND payload LIKE ? AND created_at > ? LIMIT 1",
                (signal_type, '%"module": "' + key + '"%', _utc_now()),
            ).fetchone()
        return row is not None

    def _record_signal(self, signal_type, summary, evidence_citations, payload=None):
        now = _utc_now()
        with self.store.transaction() as connection:
            connection.execute(
                """INSERT INTO awareness_signals(signal_type, summary, evidence_citations, payload, created_at, ttl_after)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (signal_type, summary,
                 json.dumps(evidence_citations, ensure_ascii=False),
                 json.dumps(payload or {}, ensure_ascii=False),
                 now, now),
            )

    def get_signals(self, signal_type=None, limit=20):
        clauses = []
        params = []
        if signal_type:
            clauses.append("signal_type = ?")
            params.append(signal_type)
        query = "SELECT * FROM awareness_signals" + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self.store.transaction() as connection:
            rows = [dict(row) for row in connection.execute(query, params)]
        for row in rows:
            row["evidence_citations"] = json.loads(row.get("evidence_citations") or "[]")
            row["payload"] = json.loads(row.get("payload") or "{}")
        return rows

    def cleanup_expired(self):
        with self.store.transaction() as connection:
            connection.execute(
                "DELETE FROM awareness_signals WHERE ttl_after IS NOT NULL AND ttl_after < ?",
                (_utc_now(),),
            )
