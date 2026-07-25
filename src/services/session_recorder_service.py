"""Durable session boundaries and observable event capture."""

import uuid

from services.service import Service


class SessionRecorderService(Service):
    def __init__(self, kernel):
        super().__init__(kernel); self.store = None

    def start(self):
        super().start(); self.store = self.kernel.get_service("KnowledgeStoreService")
        if not self.store: raise RuntimeError("SessionRecorderService requires KnowledgeStoreService.")

    def start_session(self, workspace_id, metadata=None):
        workspace = self.store.get_workspace(workspace_id)
        if not workspace or workspace["status"] != "active": raise ValueError("Workspace must be active: %s" % workspace_id)
        return self.store.create_session("session-" + uuid.uuid4().hex, workspace_id, metadata)

    def record(self, session_id, event_type, path, payload=None):
        session = self.store.get_session(session_id)
        if not session or session["status"] != "active": raise ValueError("Session must be active: %s" % session_id)
        self.store.record_event(event_type, path, payload or {}, session["workspace_id"], session_id)

    def close_session(self, session_id):
        return self.store.close_session(session_id)

    def recover_active_sessions(self, workspace_id=None):
        return self.store.list_sessions(workspace_id, active_only=True)
