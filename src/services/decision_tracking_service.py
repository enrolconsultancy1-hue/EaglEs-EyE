"""Explicit engineering decision records linked to workspace, session, and evidence citations."""

from services.service import Service


class DecisionTrackingService(Service):
    def __init__(self, kernel):
        super().__init__(kernel); self.store = None

    def start(self):
        super().start(); self.store = self.kernel.get_service("KnowledgeStoreService")
        if not self.store: raise RuntimeError("DecisionTrackingService requires KnowledgeStoreService.")

    def record_decision(self, workspace_id, session_id, decision_type, summary, evidence_citations=None, payload=None):
        if evidence_citations and not isinstance(evidence_citations, list):
            raise ValueError("evidence_citations must be a list of citation strings.")
        return self.store.add_decision_record(workspace_id, session_id, decision_type, summary, evidence_citations, payload)

    def get_decisions(self, workspace_id=None, session_id=None):
        return self.store.list_decision_records(workspace_id, session_id)

    def get_decision(self, decision_id):
        records = self.store.list_decision_records()
        for r in records:
            if r["id"] == decision_id:
                return r
        return None
