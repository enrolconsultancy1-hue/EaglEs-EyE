"""Decision Lineage Service — track decisions, supporting evidence,
related observations, timeline, confidence, and source connectors.

Every decision lineage preserves connector provenance per Universal Reasoning Policy.
"""

from datetime import datetime, timezone
from services.service import Service


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _wrap_result(conclusion, confidence, supporting_evidence, connector_sources,
                 observation_surfaces, reasoning_trace, supporting_relationships):
    return {
        "conclusion": conclusion,
        "confidence": confidence,
        "supporting_evidence": supporting_evidence,
        "connector_sources": connector_sources,
        "observation_surfaces": observation_surfaces,
        "reasoning_trace": reasoning_trace,
        "supporting_relationships": supporting_relationships,
        "timestamp": _utc_now(),
    }


class DecisionLineageService(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None
        self.decisions = None
        self.evidence_ingestion = None
        self.confidence = None
        self.connector_svc = None
        self.reasoning = None

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        self.decisions = self.kernel.get_service("DecisionTrackingService")
        self.evidence_ingestion = self.kernel.get_service("EvidenceIngestionService")
        self.confidence = self.kernel.get_service("ConfidenceEngine")
        self.connector_svc = self.kernel.get_service("ConnectorService")
        self.reasoning = self.kernel.get_service("ReasoningEngine")
        if not all((self.store, self.decisions, self.confidence, self.reasoning)):
            raise RuntimeError("DecisionLineageService requires DecisionTrackingService, ConfidenceEngine, and ReasoningEngine.")

    def trace(self, decision_id):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "lineage_trace_start", "decision_id": decision_id})

        record = self.decisions.get_decision(decision_id) if hasattr(self.decisions, "get_decision") else None
        if not record:
            conclusion = "Decision not found: %s" % decision_id
            return _wrap_result(conclusion, 0.0, supporting_evidence,
                                [], [], reasoning_trace, supporting_relationships)

        supporting_evidence.append({
            "citation": "decision:%s" % decision_id,
            "decision_id": decision_id,
            "decision_type": record.get("decision_type", ""),
            "summary": record.get("summary", ""),
            "timestamp": record.get("created_at", ""),
        })

        evidence_citations = record.get("evidence_citations", [])
        for citation in evidence_citations:
            supporting_evidence.append({"citation": citation})

        reasoning_trace.append({"step": "decision_found", "citations": len(evidence_citations)})

        workspace_id = record.get("workspace_id")
        session_id = record.get("session_id")

        if session_id or workspace_id:
            events = self.store.session_events(workspace_id, session_id) if workspace_id else (
                self.store.session_events(session_id=session_id) if session_id else [])
            for e in events:
                supporting_relationships.append({
                    "source": "decision:%s" % decision_id,
                    "target": "event:%s" % e["id"],
                    "relation": "supported_by_event",
                    "path": e.get("path", ""),
                    "timestamp": e.get("created_at", ""),
                })

            reasoning_trace.append({"step": "related_events", "count": len(events)})

        if self.connector_svc and self.connector_svc.get_manager():
            for cid in self.connector_svc.get_manager().list_ids():
                connector_sources.add(cid)
                try:
                    connector = self.connector_svc.get_manager().get_connector(cid)
                    surfaces = connector.get_active_surfaces() if hasattr(connector, "get_active_surfaces") else []
                    for s in surfaces:
                        observation_surfaces.add(s)
                except Exception:
                    pass

        if self.evidence_ingestion:
            ingested_stats = self.evidence_ingestion.get_stats() if hasattr(self.evidence_ingestion, "get_stats") else {}
            supporting_evidence.append({
                "citation": "evidence:ingestion",
                "stats": ingested_stats,
            })

        confidence, conf_details = self.confidence.score_evidence(supporting_evidence) if self.confidence else (0.5, {})

        conclusion = "Decision lineage for '%s' (%s): %d evidence citations, %d related events, confidence %.2f" % (
            decision_id, record.get("decision_type", ""), len(evidence_citations),
            len(supporting_relationships), confidence)

        reasoning_trace.append({"step": "lineage_trace_complete"})

        result = _wrap_result(conclusion, confidence, supporting_evidence,
                              sorted(connector_sources), sorted(observation_surfaces),
                              reasoning_trace, supporting_relationships)
        result["decision"] = record
        return result

    def list_lineages(self, workspace_id=None, session_id=None):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "list_lineages_start"})

        records = self.decisions.get_decisions(workspace_id, session_id) if hasattr(self.decisions, "get_decisions") else []
        for rec in records:
            supporting_evidence.append({
                "citation": "decision:%s" % rec.get("id"),
                "decision_type": rec.get("decision_type", ""),
                "summary": rec.get("summary", "")[:100],
                "timestamp": rec.get("created_at", ""),
            })

        reasoning_trace.append({"step": "decisions_collected", "count": len(records)})

        if self.connector_svc and self.connector_svc.get_manager():
            for cid in self.connector_svc.get_manager().list_ids():
                connector_sources.add(cid)

        confidence, _ = self.confidence.score_evidence(supporting_evidence) if self.confidence else (0.5, {})
        conclusion = "Decision lineages: %d decision(s) found" % len(records)

        reasoning_trace.append({"step": "list_lineages_complete"})

        result = _wrap_result(conclusion, confidence, supporting_evidence,
                              sorted(connector_sources), sorted(observation_surfaces),
                              reasoning_trace, supporting_relationships)
        result["decisions"] = records
        return result
