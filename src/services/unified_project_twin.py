"""UnifiedProjectTwin — presents a single coherent AI Twin representation
integrating files, git, docs, evidence, tasks, decisions, relationships,
architecture, history, risks, health, and connectors.

Every conclusion preserves evidence provenance per the Universal Reasoning Policy.
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


class UnifiedProjectTwin(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None
        self.kg = None
        self.orchestrator = None
        self.connector_svc = None
        self.reasoning = None
        self.project_intelligence = None
        self.confidence = None
        self.evolution = None
        self.decisions = None

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        self.kg = self.kernel.get_service("KnowledgeGraphService")
        self.orchestrator = self.kernel.get_service("AITwinOrchestrator")
        self.connector_svc = self.kernel.get_service("ConnectorService")
        self.reasoning = self.kernel.get_service("ReasoningEngine")
        self.project_intelligence = self.kernel.get_service("ProjectIntelligenceEngine")
        self.confidence = self.kernel.get_service("ConfidenceEngine")
        self.evolution = self.kernel.get_service("ArchitectureEvolutionService")
        self.decisions = self.kernel.get_service("DecisionTrackingService")
        if not all((self.store, self.confidence)):
            raise RuntimeError("UnifiedProjectTwin requires KnowledgeStoreService and ConfidenceEngine.")

    def _stats(self):
        return self.store.statistics() if self.store else {}

    def overview(self):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "twin_overview_start"})

        stats = self._stats()
        total_docs = stats.get("documents", 0)
        total_events = stats.get("events", 0)
        total_symbols = stats.get("symbols", 0)
        total_relationships = stats.get("relationships", 0)

        supporting_evidence.append({
            "citation": "store:statistics",
            "documents": total_docs,
            "events": total_events,
            "symbols": total_symbols,
            "relationships": total_relationships,
        })

        connector_count = 0
        if self.connector_svc and self.connector_svc.get_manager():
            for cid in self.connector_svc.get_manager().list_ids():
                connector_count += 1
                connector_sources.add(cid)

        decision_count = 0
        if self.decisions:
            try:
                decision_count = len(self.decisions.get_decisions())
            except Exception:
                pass

        snapshots = []
        if self.evolution:
            try:
                snapshots = self.store.list_architecture_snapshots() if hasattr(self.store, "list_architecture_snapshots") else []
            except Exception:
                pass

        supporting_evidence.append({
            "citation": "twin:overview_counts",
            "connectors": connector_count,
            "decisions": decision_count,
            "architecture_snapshots": len(snapshots),
        })

        scores = [
            min(total_docs / 100.0, 1.0) if total_docs > 0 else 0.1,
            min(total_relationships / max(total_symbols, 1) / 2.0, 1.0) if total_symbols > 0 else 0.1,
            min(connector_count / 5.0, 1.0),
            min(decision_count / 10.0, 1.0),
        ]
        confidence = round(sum(scores) / max(len(scores), 1), 2) if scores else 0.5

        conclusion = "AI Project Twin overview: %d documents, %d events, %d symbols, %d relationships, %d connector(s), %d decision(s), %d snapshot(s). Confidence: %.2f" % (
            total_docs, total_events, total_symbols, total_relationships,
            connector_count, decision_count, len(snapshots), confidence)

        reasoning_trace.append({"step": "twin_overview_complete"})

        return _wrap_result(conclusion, confidence, supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    def project_summary(self, workspace_id=None):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "project_summary_start"})

        stats = self._stats()
        supporting_evidence.append({
            "citation": "store:statistics",
            "stats": stats,
        })

        pi_health = None
        if self.project_intelligence:
            pi_health = self.project_intelligence.project_health(workspace_id)
            if pi_health:
                supporting_evidence.append({
                    "citation": "project_intelligence:health",
                    "health": pi_health,
                })

        if self.connector_svc and self.connector_svc.get_manager():
            for cid in self.connector_svc.get_manager().list_ids():
                connector_sources.add(cid)

        health_status = "unknown"
        overall_confidence = 0.5
        if pi_health:
            overall_confidence = pi_health.get("confidence", 0.5)
            health_status = "healthy" if overall_confidence >= 0.7 else ("degraded" if overall_confidence >= 0.4 else "critical")

        conclusion = "Project summary: status %s (confidence: %.2f), %d documents" % (
            health_status, overall_confidence, stats.get("documents", 0))

        reasoning_trace.append({"step": "project_summary_complete", "status": health_status})

        return _wrap_result(conclusion, overall_confidence, supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    def connector_twin(self):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "connector_twin_start"})

        connector_details = []
        if self.connector_svc and self.connector_svc.get_manager():
            manager = self.connector_svc.get_manager()
            for cid in manager.list_ids():
                connector_sources.add(cid)
                try:
                    status = manager.connector_status(cid)
                    connector_details.append({
                        "connector_id": cid,
                        "state": status.get("state"),
                    })
                    supporting_evidence.append({
                        "citation": "connector:status:%s" % cid,
                        "connector_id": cid,
                        "state": status.get("state"),
                    })
                except Exception:
                    pass

        reasoning_trace.append({"step": "connectors_collected", "count": len(connector_details)})

        confidence = min(len(connector_details) / 5.0, 1.0)
        conclusion = "Connector twin: %d connector(s) registered" % len(connector_details)

        reasoning_trace.append({"step": "connector_twin_complete"})

        return _wrap_result(conclusion, round(confidence, 2), supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    def reasoning_twin(self, query=None, mode="cross_connector"):
        if not self.reasoning:
            return _wrap_result("Reasoning engine unavailable", 0.0, [],
                                [], [], [{"step": "unavailable"}], [])
        if query:
            if mode == "cross_connector":
                return self.reasoning.reason_cross_connector(query)
            elif mode == "dependencies":
                return self.reasoning.reason_dependencies(query)
            elif mode == "timeline":
                return self.reasoning.reason_timeline(path=query)
            elif mode == "historical":
                return self.reasoning.reason_historical(query)
        return self.reasoning.reason_evidence_correlation()
