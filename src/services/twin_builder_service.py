"""Build reproducible local twin artifacts from recorded session evidence."""

import json
import os

from services.service import Service


class TwinBuilderService(Service):
    def __init__(self, kernel):
        super().__init__(kernel); self.store = self.timeline = None; self.twins_path = None

    def start(self):
        super().start(); self.store = self.kernel.get_service("KnowledgeStoreService"); self.timeline = self.kernel.get_service("ExecutionTimelineService")
        if not self.store or not self.timeline: raise RuntimeError("TwinBuilderService requires KnowledgeStoreService and ExecutionTimelineService.")
        self.twins_path = self.kernel.get_config().get("twins_path", os.path.join(os.path.dirname(self.store.database_path), "Twins"))

    def build(self, session_id):
        session = self.store.get_session(session_id)
        if not session: raise ValueError("Unknown session: %s" % session_id)
        events = self.timeline.events(workspace_id=session["workspace_id"], session_id=session_id)
        directory = os.path.join(self.twins_path, session["workspace_id"], session_id); os.makedirs(directory, exist_ok=True)
        summary = {"session": session, "event_count": len(events), "evidence": [event["citation"] for event in events], "scope": "Observable evidence only."}
        self._write(os.path.join(directory, "timeline.json"), events); self._write(os.path.join(directory, "events.json"), events); self._write(os.path.join(directory, "summary.json"), summary)
        return {"path": directory, "summary": summary}

    @staticmethod
    def _write(path, payload):
        temporary = path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as target: json.dump(payload, target, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(temporary, path)
