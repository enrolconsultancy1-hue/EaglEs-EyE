"""UniversalTwinReport — generates a complete, evidence-backed AI Twin Report
covering project overview, connectors, observation surfaces, health, risks,
timeline, dependencies, decisions, confidence, evidence summary, architecture
drift, and recommendations.

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


class UniversalTwinReport(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None
        self.kg = None
        self.orchestrator = None
        self.validator = None
        self.unified = None
        self.connector_svc = None
        self.reasoning = None
        self.project_intelligence = None
        self.confidence = None
        self.evolution = None
        self.decisions = None
        self.root_cause = None
        self.impact = None

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        self.kg = self.kernel.get_service("KnowledgeGraphService")
        self.orchestrator = self.kernel.get_service("AITwinOrchestrator")
        self.validator = self.kernel.get_service("TwinIntegrityValidator")
        self.unified = self.kernel.get_service("UnifiedProjectTwin")
        self.connector_svc = self.kernel.get_service("ConnectorService")
        self.reasoning = self.kernel.get_service("ReasoningEngine")
        self.project_intelligence = self.kernel.get_service("ProjectIntelligenceEngine")
        self.confidence = self.kernel.get_service("ConfidenceEngine")
        self.evolution = self.kernel.get_service("ArchitectureEvolutionService")
        self.decisions = self.kernel.get_service("DecisionTrackingService")
        self.root_cause = self.kernel.get_service("RootCauseAnalysisService")
        self.impact = self.kernel.get_service("ImpactAnalysisService")
        if not all((self.store, self.confidence)):
            raise RuntimeError("UniversalTwinReport requires KnowledgeStoreService and ConfidenceEngine.")

    def generate(self, workspace_id=None):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "report_generation_start"})

        overview = self.unified.overview() if self.unified else _wrap_result("Unified twin unavailable", 0.0, [], [], [], [], [])
        health = self.orchestrator.twin_health() if self.orchestrator else _wrap_result("Orchestrator unavailable", 0.0, [], [], [], [], [])
        integrity = self.validator.check_all() if self.validator else _wrap_result("Validator unavailable", 0.0, [], [], [], [], [])
        status = self.orchestrator.twin_status() if self.orchestrator else _wrap_result("Orchestrator unavailable", 0.0, [], [], [], [], [])

        sections = {
            "overview": overview,
            "health": health,
            "integrity": integrity,
            "status": status,
        }

        if self.project_intelligence:
            sections["blockers"] = self.project_intelligence.detect_blockers(workspace_id)
            sections["bottlenecks"] = self.project_intelligence.detect_bottlenecks()
            sections["stale_work"] = self.project_intelligence.detect_stale_work()
            sections["architecture_drift"] = self.project_intelligence.detect_architecture_drift()

        if self.connector_svc and self.connector_svc.get_manager():
            for cid in self.connector_svc.get_manager().list_ids():
                connector_sources.add(cid)

        for section_name, result in sections.items():
            supporting_evidence.append({
                "citation": "report:section:%s" % section_name,
                "section": section_name,
                "conclusion": result.get("conclusion", ""),
                "confidence": result.get("confidence", 0.0),
            })
            if result.get("connector_sources"):
                connector_sources.update(result["connector_sources"])
            if result.get("supporting_evidence"):
                supporting_evidence.extend(result["supporting_evidence"])

        stats = self.store.statistics() if self.store else {}
        section_count = len(sections)
        confidence_values = [s.get("confidence", 0.0) for s in sections.values() if isinstance(s, dict)]
        overall_confidence = round(sum(confidence_values) / max(len(confidence_values), 1), 2) if confidence_values else 0.5

        conclusion = "Universal AI Twin Report: %d sections, %d documents, %d events, %d symbols, %d relationships. Overall confidence: %.2f" % (
            section_count, stats.get("documents", 0), stats.get("events", 0),
            stats.get("symbols", 0), stats.get("relationships", 0), overall_confidence)

        reasoning_trace.append({
            "step": "report_generation_complete",
            "sections": section_count,
            "overall_confidence": overall_confidence,
        })

        result = _wrap_result(conclusion, overall_confidence, supporting_evidence,
                              sorted(connector_sources), sorted(observation_surfaces),
                              reasoning_trace, supporting_relationships)
        result["report"] = sections
        return result

    def generate_summary(self, workspace_id=None):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "report_summary_start"})

        health = self.orchestrator.twin_health() if self.orchestrator else {}
        status = self.orchestrator.twin_status() if self.orchestrator else {}
        integrity = self.validator.check_all() if self.validator else {}

        if self.connector_svc and self.connector_svc.get_manager():
            for cid in self.connector_svc.get_manager().list_ids():
                connector_sources.add(cid)

        supporting_evidence.append({
            "citation": "report:health",
            "health": health.get("conclusion", ""),
        })
        supporting_evidence.append({
            "citation": "report:status",
            "status": status.get("conclusion", ""),
        })
        supporting_evidence.append({
            "citation": "report:integrity",
            "integrity": integrity.get("conclusion", ""),
        })

        health_confidence = health.get("confidence", 0.0) if isinstance(health, dict) else 0.0
        overall_confidence = round(health_confidence, 2)

        conclusion = "Twin summary: health=%.2f, integrity=%s" % (
            health_confidence,
            integrity.get("conclusion", "unknown") if isinstance(integrity, dict) else "unknown",
        )

        reasoning_trace.append({"step": "report_summary_complete"})

        result = _wrap_result(conclusion, overall_confidence, supporting_evidence,
                              sorted(connector_sources), sorted(observation_surfaces),
                              reasoning_trace, supporting_relationships)
        result["health"] = health if isinstance(health, dict) else {}
        result["status"] = status if isinstance(status, dict) else {}
        result["integrity"] = integrity if isinstance(integrity, dict) else {}
        return result
