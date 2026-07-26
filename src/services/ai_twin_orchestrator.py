"""AI Twin Orchestrator — coordinates all services into a single coherent
AI Twin lifecycle. Exposes stable Dashboard APIs for status, health, connectors,
observations, reasoning, sync, and evidence metrics.

Every result preserves evidence provenance per the Universal Reasoning Policy.
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


class AITwinOrchestrator(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None
        self.kg = None
        self.connector_svc = None
        self.evidence_ingestion = None
        self.scheduler = None
        self.reasoning = None
        self.project_intelligence = None
        self.confidence = None

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        self.kg = self.kernel.get_service("KnowledgeGraphService")
        self.connector_svc = self.kernel.get_service("ConnectorService")
        self.evidence_ingestion = self.kernel.get_service("EvidenceIngestionService")
        self.scheduler = self.kernel.get_service("ConnectorSchedulerService")
        self.reasoning = self.kernel.get_service("ReasoningEngine")
        self.project_intelligence = self.kernel.get_service("ProjectIntelligenceEngine")
        self.confidence = self.kernel.get_service("ConfidenceEngine")
        if not all((self.store, self.confidence)):
            raise RuntimeError("AITwinOrchestrator requires KnowledgeStoreService and ConfidenceEngine.")

    def twin_status(self):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "twin_status_start"})

        stats = self.store.statistics() if self.store else {}
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
        connector_healthy = 0
        if self.connector_svc and self.connector_svc.get_manager():
            manager = self.connector_svc.get_manager()
            for cid in manager.list_ids():
                connector_count += 1
                connector_sources.add(cid)
                try:
                    status = manager.connector_status(cid)
                    if status.get("state") in ("running", "connected"):
                        connector_healthy += 1
                except Exception:
                    pass

        supporting_evidence.append({
            "citation": "connector:status_summary",
            "total_connectors": connector_count,
            "healthy_connectors": connector_healthy,
        })

        reasoning_trace.append({
            "step": "connector_check",
            "total": connector_count,
            "healthy": connector_healthy,
        })

        scores = []
        doc_score = min(total_docs / 100.0, 1.0) if total_docs > 0 else 0.1
        scores.append(doc_score)
        rel_score = min(total_relationships / max(total_symbols, 1) / 2.0, 1.0) if total_symbols > 0 else 0.1
        scores.append(rel_score)
        conn_score = connector_healthy / max(connector_count, 1) if connector_count > 0 else 0.5
        scores.append(conn_score)
        confidence = round(sum(scores) / max(len(scores), 1), 2) if scores else 0.5

        state = "active" if confidence >= 0.5 else "degraded"
        conclusion = "AI Twin status: %s (confidence: %.2f). %d documents, %d events, %d symbols, %d relationships, %d/%d connectors healthy." % (
            state, confidence, total_docs, total_events, total_symbols, total_relationships,
            connector_healthy, connector_count)

        reasoning_trace.append({"step": "twin_status_complete", "state": state})

        return _wrap_result(conclusion, confidence, supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    def twin_health(self):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "twin_health_start"})

        pi_health = None
        if self.project_intelligence:
            pi_health = self.project_intelligence.project_health()
            supporting_evidence.append({
                "citation": "project_intelligence:health",
                "health_result": pi_health,
            })
            if pi_health.get("connector_sources"):
                connector_sources.update(pi_health["connector_sources"])
            if pi_health.get("supporting_evidence"):
                supporting_evidence.extend(pi_health["supporting_evidence"])
            reasoning_trace.append({"step": "project_intelligence_health_obtained"})

        if self.connector_svc and self.connector_svc.get_manager():
            manager = self.connector_svc.get_manager()
            for cid in manager.list_ids():
                connector_sources.add(cid)

        health_status = "healthy"
        overall_confidence = 0.5
        if pi_health:
            overall_confidence = pi_health.get("confidence", 0.5)
            health_status = "healthy" if overall_confidence >= 0.7 else ("degraded" if overall_confidence >= 0.4 else "critical")

        conclusion = "AI Twin health: %s (confidence: %.2f)" % (health_status, overall_confidence)

        supporting_evidence.append({
            "citation": "twin:health_status",
            "health_status": health_status,
            "confidence": overall_confidence,
        })
        reasoning_trace.append({"step": "twin_health_complete", "status": health_status})

        return _wrap_result(conclusion, overall_confidence, supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    def connector_status_summary(self):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "connector_status_summary_start"})

        connectors = []
        if self.connector_svc and self.connector_svc.get_manager():
            manager = self.connector_svc.get_manager()
            for cid in manager.list_ids():
                connector_sources.add(cid)
                try:
                    status = manager.connector_status(cid)
                    connectors.append(status)
                    supporting_evidence.append({
                        "citation": "connector:status:%s" % cid,
                        "connector_id": cid,
                        "state": status.get("state"),
                    })
                except Exception as e:
                    supporting_evidence.append({
                        "citation": "connector:error:%s" % cid,
                        "connector_id": cid,
                        "error": str(e),
                    })

        reasoning_trace.append({"step": "connectors_checked", "count": len(connectors)})

        healthy = sum(1 for c in connectors if c.get("state") in ("running", "connected"))
        confidence = healthy / max(len(connectors), 1) if connectors else 0.0
        conclusion = "Connector status: %d/%d healthy" % (healthy, len(connectors)) if connectors else "No connectors registered"

        reasoning_trace.append({"step": "connector_status_summary_complete"})

        return _wrap_result(conclusion, round(confidence, 2), supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    def observation_status(self):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "observation_status_start"})

        if self.connector_svc and self.connector_svc.get_manager():
            manager = self.connector_svc.get_manager()
            for cid in manager.list_ids():
                connector_sources.add(cid)
                try:
                    connector = manager.get_connector(cid)
                    if hasattr(connector, "discover_observation_surfaces"):
                        surfaces = connector.discover_observation_surfaces()
                        for s in surfaces:
                            observation_surfaces.add(s)
                        supporting_evidence.append({
                            "citation": "connector:surfaces:%s" % cid,
                            "connector_id": cid,
                            "surfaces": surfaces,
                        })
                except Exception:
                    pass

        reasoning_trace.append({"step": "observation_surfaces_discovered", "count": len(observation_surfaces)})

        confidence = min(len(observation_surfaces) / 10.0, 1.0) if observation_surfaces else 0.0
        conclusion = "Observation status: %d surfaces across %d connector(s)" % (
            len(observation_surfaces), len(connector_sources))
        if not connector_sources:
            conclusion = "No observation sources available"

        reasoning_trace.append({"step": "observation_status_complete"})

        return _wrap_result(conclusion, round(confidence, 2), supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    def reasoning_status(self):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "reasoning_status_start"})

        reasoning_available = self.reasoning is not None
        pi_available = self.project_intelligence is not None
        confidence_available = self.confidence is not None

        supporting_evidence.append({
            "citation": "services:reasoning_available",
            "reasoning_engine": reasoning_available,
            "project_intelligence": pi_available,
            "confidence_engine": confidence_available,
        })

        if self.connector_svc and self.connector_svc.get_manager():
            for cid in self.connector_svc.get_manager().list_ids():
                connector_sources.add(cid)

        available = sum([reasoning_available, pi_available, confidence_available])
        confidence = available / 3.0
        conclusion = "Reasoning status: %d/%d engines available" % (available, 3)

        reasoning_trace.append({"step": "reasoning_status_complete"})

        return _wrap_result(conclusion, round(confidence, 2), supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    def sync_status(self):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "sync_status_start"})

        sync_info = {}
        if self.connector_svc and self.connector_svc.get_manager():
            manager = self.connector_svc.get_manager()
            for cid in manager.list_ids():
                connector_sources.add(cid)
                try:
                    connector = manager.get_connector(cid)
                    if hasattr(connector, "get_sync_engine"):
                        sync_engine = connector.get_sync_engine()
                        last = sync_engine.last_sync(cid) if hasattr(sync_engine, "last_sync") else None
                        sync_info[cid] = {"last_sync": last}
                        supporting_evidence.append({
                            "citation": "sync:last_sync:%s" % cid,
                            "connector_id": cid,
                            "last_sync": last,
                        })
                except Exception:
                    pass

        if self.scheduler:
            scheduler_status = "available"
            supporting_evidence.append({
                "citation": "scheduler:status",
                "status": scheduler_status,
            })
        else:
            scheduler_status = "unavailable"

        reasoning_trace.append({"step": "sync_info_collected", "connectors_with_sync": len(sync_info)})

        confidence = min(len(sync_info) / max(len(connector_sources), 1), 1.0) if connector_sources else 0.5
        conclusion = "Sync status: %d connector(s) with sync info, scheduler %s" % (
            len(sync_info), scheduler_status)

        reasoning_trace.append({"step": "sync_status_complete"})

        return _wrap_result(conclusion, round(confidence, 2), supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    def project_health(self, workspace_id=None):
        if not self.project_intelligence:
            return _wrap_result("Project intelligence engine unavailable", 0.0, [],
                                [], [], [{"step": "unavailable"}], [])
        return self.project_intelligence.project_health(workspace_id)

    def evidence_metrics(self):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "evidence_metrics_start"})

        if self.evidence_ingestion:
            stats = self.evidence_ingestion.get_stats() if hasattr(self.evidence_ingestion, "get_stats") else {}
            supporting_evidence.append({
                "citation": "evidence:ingestion_stats",
                "stats": stats,
            })
        else:
            supporting_evidence.append({
                "citation": "evidence:unavailable",
                "note": "EvidenceIngestionService unavailable",
            })

        if self.connector_svc and self.connector_svc.get_manager():
            for cid in self.connector_svc.get_manager().list_ids():
                connector_sources.add(cid)

        confidence = 0.5 if self.evidence_ingestion else 0.0
        conclusion = "Evidence metrics: pipeline %s" % ("available" if self.evidence_ingestion else "unavailable")

        reasoning_trace.append({"step": "evidence_metrics_complete"})

        return _wrap_result(conclusion, confidence, supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)
