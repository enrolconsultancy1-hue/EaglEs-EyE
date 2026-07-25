"""Workspace- and session-scoped ordering over observable event evidence."""

import json

from services.service import Service


class ExecutionTimelineService(Service):
    def __init__(self, kernel):
        super().__init__(kernel); self.store = None

    def start(self):
        super().start(); self.store = self.kernel.get_service("KnowledgeStoreService")
        if not self.store: raise RuntimeError("ExecutionTimelineService requires KnowledgeStoreService.")

    def events(self, workspace_id=None, session_id=None, start=None, end=None):
        rows = self.store.session_events(workspace_id, session_id, start, end)
        return [{"sequence": index + 1, "event_id": row["id"], "event_type": row["event_type"],
                 "path": row["path"], "workspace_id": row["workspace_id"], "session_id": row["session_id"],
                 "payload": json.loads(row["payload"] or "{}"), "observed_at": row["created_at"],
                 "citation": "event:%s" % row["id"]} for index, row in enumerate(rows)]
