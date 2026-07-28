"""Phase 18 — Universal AI Project Twin (v3.0.0)."""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch


class FakeKernel:
    def __init__(self):
        self._services = {}
        self._config = {}

    def get_service(self, name):
        return self._services.get(name)

    def get_config(self):
        return self._config

    def register_service(self, service):
        self._services[service.name] = service
        service.kernel = self


def make_mock_service(name, **attrs):
    svc = MagicMock()
    svc.name = name
    svc.kernel = None
    for k, v in attrs.items():
        setattr(svc, k, v)
    return svc


class FakeStore:
    def __init__(self):
        self.documents = {}
        self.events = []
        self.relationships = []
        self.symbols_by_name = {}
        self.causal_edges = []
        self.decision_records = []
        self.snapshots = []
        self._event_id = 0
        self._doc_id = 0

    def statistics(self):
        return {
            "documents": len(self.documents),
            "events": len(self.events),
            "reflections": 0,
            "relationships": len(self.relationships),
            "symbols": sum(len(v) for v in self.symbols_by_name.values()),
            "workspaces": 0,
            "sessions": 0,
            "causal_edges": len(self.causal_edges),
            "decision_records": len(self.decision_records),
            "architecture_snapshots": len(self.snapshots),
            "chunks": 0,
        }

    def get_document(self, path, include_chunks=True):
        return self.documents.get(path)

    def session_events(self, workspace_id=None, session_id=None, start=None, end=None):
        return self.events

    def recent_events(self, limit=10):
        return self.events[:limit]

    def find_symbols(self, name, limit=30):
        return self.symbols_by_name.get(name, [])

    def add_relationship(self, source, target, relation, metadata=None):
        self.relationships.append({"source": source, "target": target, "relation": relation, "metadata": metadata})

    def transaction(self):
        return self._FakeTransaction(self)

    class _FakeTransaction:
        def __init__(self, store):
            self.store = store
        def __enter__(self):
            return self.store._FakeConnection(self.store)
        def __exit__(self, *args):
            pass

    class _FakeConnection:
        def __init__(self, store):
            self.store = store
        def execute(self, sql, params=None):
            return self.store._FakeCursor(self.store, sql)
        def commit(self):
            pass

    class _FakeCursor(list):
        def __init__(self, store, sql):
            self.store = store
            self.sql = sql
        def fetchone(self):
            return {"count": 0}
        def fetchall(self):
            return []

    def record_reflection(self, summary, payload):
        pass

    def list_architecture_snapshots(self):
        return self.snapshots

    def get_event_by_id(self, event_id):
        for e in self.events:
            if e.get("id") == event_id or e.get("id") == int(event_id):
                return e
        return None


def setup_phase18_services(kernel):
    """Set up all mock services needed for Phase 18 engines."""
    from services.confidence_engine import ConfidenceEngine

    kg = make_mock_service("KnowledgeGraphService")
    kg.related_weighted.return_value = []
    kg.propagate_confidence.return_value = {"/test": 1.0}
    kg.multi_source_correlate.return_value = {}
    kg.where_used.return_value = {"symbols": [], "relationships": []}

    causal = make_mock_service("CausalGraphService")
    causal.get_causal_edges.return_value = []
    causal.get_downstream_events.return_value = []
    causal.get_upstream_events.return_value = []

    cognitive = make_mock_service("CognitiveLayerService")
    cognitive.explain_change.return_value = {"citations": [], "scope": "test"}

    evolution = make_mock_service("ArchitectureEvolutionService")
    evolution.get_evolution.return_value = {"history": []}
    evolution.compare_snapshots.return_value = {"added": [], "removed": []}

    decisions = make_mock_service("DecisionTrackingService")
    decisions.get_decision.return_value = None
    decisions.get_decisions.return_value = []

    connector_svc = make_mock_service("ConnectorService")
    connector_svc.get_manager.return_value = None

    evidence_ingestion = make_mock_service("EvidenceIngestionService")
    evidence_ingestion.get_stats.return_value = {"ingested": 0}

    retrieval = make_mock_service("RetrievalService")
    retrieval.search.return_value = []

    context = make_mock_service("ContextBuilderService")
    context.build_rag_context.return_value = ""

    timeline = make_mock_service("ExecutionTimelineService")

    scheduler = make_mock_service("ConnectorSchedulerService")

    conf = ConfidenceEngine(kernel)
    conf.start()
    kernel._services["ConfidenceEngine"] = conf
    kernel._services["KnowledgeGraphService"] = kg
    kernel._services["CausalGraphService"] = causal
    kernel._services["CognitiveLayerService"] = cognitive
    kernel._services["ArchitectureEvolutionService"] = evolution
    kernel._services["DecisionTrackingService"] = decisions
    kernel._services["ConnectorService"] = connector_svc
    kernel._services["EvidenceIngestionService"] = evidence_ingestion
    kernel._services["RetrievalService"] = retrieval
    kernel._services["ContextBuilderService"] = context
    kernel._services["ExecutionTimelineService"] = timeline
    kernel._services["ConnectorSchedulerService"] = scheduler

    from services.reasoning_engine import ReasoningEngine
    re_engine = ReasoningEngine(kernel)
    re_engine.start()
    kernel._services["ReasoningEngine"] = re_engine

    from services.project_intelligence_engine import ProjectIntelligenceEngine
    pi = ProjectIntelligenceEngine(kernel)
    pi.start()
    kernel._services["ProjectIntelligenceEngine"] = pi

    from services.root_cause_analysis_service import RootCauseAnalysisService
    rca = RootCauseAnalysisService(kernel)
    rca.start()
    kernel._services["RootCauseAnalysisService"] = rca

    from services.impact_analysis_service import ImpactAnalysisService
    ia = ImpactAnalysisService(kernel)
    ia.start()
    kernel._services["ImpactAnalysisService"] = ia

    from services.decision_lineage_service import DecisionLineageService
    dl = DecisionLineageService(kernel)
    dl.start()
    kernel._services["DecisionLineageService"] = dl

    from services.explainable_ai_service import ExplainableAIService
    eai = ExplainableAIService(kernel)
    eai.start()
    kernel._services["ExplainableAIService"] = eai

    # Phase 18 services
    from services.ai_twin_orchestrator import AITwinOrchestrator
    orch = AITwinOrchestrator(kernel)
    orch.start()
    kernel._services["AITwinOrchestrator"] = orch

    from services.twin_integrity_validator import TwinIntegrityValidator
    validator = TwinIntegrityValidator(kernel)
    validator.start()
    kernel._services["TwinIntegrityValidator"] = validator

    from services.unified_project_twin import UnifiedProjectTwin
    unified = UnifiedProjectTwin(kernel)
    unified.start()
    kernel._services["UnifiedProjectTwin"] = unified

    from services.universal_twin_report import UniversalTwinReport
    report = UniversalTwinReport(kernel)
    report.start()
    kernel._services["UniversalTwinReport"] = report

    return kernel


# --- AITwinOrchestrator Tests ---

class TestAITwinOrchestrator(unittest.TestCase):
    def setUp(self):
        self.kernel = FakeKernel()
        self.store = FakeStore()
        self.kernel._services["KnowledgeStoreService"] = self.store
        self.kernel = setup_phase18_services(self.kernel)
        self.engine = self.kernel.get_service("AITwinOrchestrator")

    def test_twin_status(self):
        result = self.engine.twin_status()
        self.assertIn("conclusion", result)
        self.assertIn("AI Twin status", result["conclusion"])
        self.assertIn("confidence", result)
        self.assertIn("supporting_evidence", result)
        self.assertIn("connector_sources", result)
        self.assertIn("reasoning_trace", result)
        self.assertIn("timestamp", result)

    def test_twin_status_with_docs(self):
        self.store.documents["a.py"] = {"id": 1}
        self.store.documents["b.py"] = {"id": 2}
        result = self.engine.twin_status()
        self.assertIn("2 documents", result["conclusion"].lower())

    def test_twin_health(self):
        result = self.engine.twin_health()
        self.assertIn("conclusion", result)
        self.assertIn("AI Twin health", result["conclusion"])

    def test_connector_status_summary(self):
        result = self.engine.connector_status_summary()
        self.assertIn("conclusion", result)
        self.assertIn("No connectors", result["conclusion"])

    def test_observation_status(self):
        result = self.engine.observation_status()
        self.assertIn("conclusion", result)
        self.assertIn("No observation", result["conclusion"])

    def test_reasoning_status(self):
        result = self.engine.reasoning_status()
        self.assertIn("conclusion", result)
        self.assertIn("engines available", result["conclusion"])

    def test_sync_status(self):
        result = self.engine.sync_status()
        self.assertIn("conclusion", result)

    def test_evidence_metrics(self):
        result = self.engine.evidence_metrics()
        self.assertIn("conclusion", result)

    def test_project_health_delegates(self):
        result = self.engine.project_health()
        self.assertIn("conclusion", result)

    def test_wrap_result_format(self):
        from services.ai_twin_orchestrator import _wrap_result
        result = _wrap_result("test", 0.95, [{"id": "ev1"}], ["fs"],
                              ["filesystem"], [{"step": "s1"}], [])
        self.assertEqual(result["confidence"], 0.95)
        self.assertEqual(result["conclusion"], "test")
        self.assertIn("timestamp", result)


# --- TwinIntegrityValidator Tests ---

class TestTwinIntegrityValidator(unittest.TestCase):
    def setUp(self):
        self.kernel = FakeKernel()
        self.store = FakeStore()
        self.kernel._services["KnowledgeStoreService"] = self.store
        self.kernel = setup_phase18_services(self.kernel)
        self.engine = self.kernel.get_service("TwinIntegrityValidator")

    def test_check_kg_consistency(self):
        result = self.engine.check_kg_consistency()
        self.assertIn("conclusion", result)
        self.assertIn("KG consistency", result["conclusion"])

    def test_check_kg_consistency_with_issues(self):
        self.store.symbols_by_name["Foo"] = [{"id": 1, "name": "Foo"}]
        result = self.engine.check_kg_consistency()
        self.assertIn("conclusion", result)

    def test_check_evidence_consistency(self):
        result = self.engine.check_evidence_consistency()
        self.assertIn("conclusion", result)

    def test_check_relationship_consistency(self):
        result = self.engine.check_relationship_consistency()
        self.assertIn("conclusion", result)

    def test_check_connector_consistency(self):
        result = self.engine.check_connector_consistency()
        self.assertIn("conclusion", result)

    def test_check_sync_consistency(self):
        result = self.engine.check_sync_consistency()
        self.assertIn("conclusion", result)

    def test_check_provenance_integrity(self):
        result = self.engine.check_provenance_integrity()
        self.assertIn("conclusion", result)

    def test_check_all(self):
        result = self.engine.check_all()
        self.assertIn("conclusion", result)
        self.assertIn("Integrity check", result["conclusion"])

    def test_wrap_result_format(self):
        from services.twin_integrity_validator import _wrap_result
        result = _wrap_result("test", 0.8, [], [], [], [{"step": "s1"}], [])
        self.assertEqual(result["confidence"], 0.8)
        self.assertIn("timestamp", result)


# --- UnifiedProjectTwin Tests ---

class TestUnifiedProjectTwin(unittest.TestCase):
    def setUp(self):
        self.kernel = FakeKernel()
        self.store = FakeStore()
        self.kernel._services["KnowledgeStoreService"] = self.store
        self.kernel = setup_phase18_services(self.kernel)
        self.engine = self.kernel.get_service("UnifiedProjectTwin")

    def test_overview(self):
        result = self.engine.overview()
        self.assertIn("conclusion", result)
        self.assertIn("AI Project Twin overview", result["conclusion"])
        self.assertIn("confidence", result)

    def test_overview_with_data(self):
        self.store.documents["a.py"] = {"id": 1}
        self.store.documents["b.py"] = {"id": 2}
        self.store.events.append({"id": 1, "event_type": "FILE_CREATED"})
        result = self.engine.overview()
        self.assertIn("2 documents", result["conclusion"].lower())

    def test_project_summary(self):
        result = self.engine.project_summary()
        self.assertIn("conclusion", result)
        self.assertIn("Project summary", result["conclusion"])

    def test_connector_twin(self):
        result = self.engine.connector_twin()
        self.assertIn("connector(s)", result["conclusion"])

    def test_reasoning_twin_no_query(self):
        result = self.engine.reasoning_twin()
        self.assertIn("conclusion", result)

    def test_reasoning_twin_with_query(self):
        result = self.engine.reasoning_twin("test query", "cross_connector")
        self.assertIn("conclusion", result)

    def test_wrap_result_format(self):
        from services.unified_project_twin import _wrap_result
        result = _wrap_result("test", 0.9, [], [], [], [], [])
        self.assertEqual(result["confidence"], 0.9)
        self.assertIn("timestamp", result)


# --- UniversalTwinReport Tests ---

class TestUniversalTwinReport(unittest.TestCase):
    def setUp(self):
        self.kernel = FakeKernel()
        self.store = FakeStore()
        self.kernel._services["KnowledgeStoreService"] = self.store
        self.kernel = setup_phase18_services(self.kernel)
        self.engine = self.kernel.get_service("UniversalTwinReport")

    def test_generate(self):
        result = self.engine.generate()
        self.assertIn("conclusion", result)
        self.assertIn("Universal AI Twin Report", result["conclusion"])
        self.assertIn("report", result)
        self.assertIn("overview", result["report"])
        self.assertIn("health", result["report"])
        self.assertIn("integrity", result["report"])
        self.assertIn("status", result["report"])

    def test_generate_summary(self):
        result = self.engine.generate_summary()
        self.assertIn("conclusion", result)
        self.assertIn("Twin summary", result["conclusion"])
        self.assertIn("health", result)
        self.assertIn("status", result)
        self.assertIn("integrity", result)

    def test_wrap_result_format(self):
        from services.universal_twin_report import _wrap_result
        result = _wrap_result("test", 0.85, [], [], [], [], [])
        self.assertEqual(result["confidence"], 0.85)
        self.assertIn("timestamp", result)


# --- Universal Observation Policy Compliance Tests ---

class TestUniversalObservationPolicy(unittest.TestCase):
    def test_wrap_result_contains_urp_fields(self):
        from services.ai_twin_orchestrator import _wrap_result
        result = _wrap_result("test", 0.9, [{"id": "ev1"}], ["github"],
                              ["official_api"], [{"step": "s1"}], [{"target": "x"}])
        required = ["conclusion", "confidence", "supporting_evidence",
                    "connector_sources", "observation_surfaces",
                    "reasoning_trace", "supporting_relationships", "timestamp"]
        for field in required:
            self.assertIn(field, result, "Missing required field: " + field)

    def test_no_hidden_reasoning(self):
        from services.ai_twin_orchestrator import _wrap_result
        result = _wrap_result("test", 0.5, [], [], [], [], [])
        self.assertIn("supporting_evidence", result)
        self.assertIn("reasoning_trace", result)

    def test_connector_provenance_preserved(self):
        from services.twin_integrity_validator import _wrap_result
        result = _wrap_result("test", 0.8, [{"id": "ev1", "connector_id": "github"}],
                              ["github"], ["official_api"], [], [])
        self.assertIn("github", result["connector_sources"])
        self.assertEqual(result["supporting_evidence"][0].get("connector_id"), "github")


# --- MCP Tool Integration Tests ---

class TestMCPToolsPhase18(unittest.TestCase):
    def setUp(self):
        self.kernel = FakeKernel()
        store = FakeStore()
        self.kernel._services["KnowledgeStoreService"] = store
        self.kernel = setup_phase18_services(self.kernel)

        mock_decisions = make_mock_service("DecisionTrackingService")
        mock_decisions.get_decision.return_value = {"id": "dec1", "decision_type": "refactor", "summary": "test", "evidence_citations": [], "created_at": "t1"}
        mock_decisions.get_decisions.return_value = []
        self.kernel._services["DecisionTrackingService"] = mock_decisions

        vec = make_mock_service("VectorSearchService")
        vec.enabled = False
        self.kernel._services["VectorSearchService"] = vec

        aware = make_mock_service("SemanticAwarenessService")
        aware.get_signals.return_value = []
        self.kernel._services["SemanticAwarenessService"] = aware

        scheduler = make_mock_service("ConnectorSchedulerService")
        self.kernel._services["ConnectorSchedulerService"] = scheduler

        from services.mcp_tool_service import MCPToolService
        self.mcp = MCPToolService(self.kernel)
        self.mcp.start()

    def test_list_tools_includes_new(self):
        tools = self.mcp.list_tools()
        names = [t["name"] for t in tools]
        expected = ["ai_twin_status", "ai_twin_health", "ai_twin_integrity",
                    "ai_twin_overview", "ai_twin_summary", "ai_twin_connectors",
                    "ai_twin_reasoning", "ai_twin_report"]
        for name in expected:
            self.assertIn(name, names, "Missing tool: " + name)

    def test_ai_twin_status_tool(self):
        result = self.mcp.call_tool("ai_twin_status", {})
        self.assertIn("ai_twin_status", result)
        self.assertIn("conclusion", result["ai_twin_status"])

    def test_ai_twin_health_tool(self):
        result = self.mcp.call_tool("ai_twin_health", {})
        self.assertIn("ai_twin_health", result)
        self.assertIn("conclusion", result["ai_twin_health"])

    def test_ai_twin_integrity_tool(self):
        result = self.mcp.call_tool("ai_twin_integrity", {})
        self.assertIn("ai_twin_integrity", result)
        self.assertIn("kg_consistency", result["ai_twin_integrity"])

    def test_ai_twin_integrity_all_tool(self):
        result = self.mcp.call_tool("ai_twin_integrity", {"all": True})
        self.assertIn("ai_twin_integrity", result)
        self.assertIn("conclusion", result["ai_twin_integrity"])
        self.assertIn("Integrity check", result["ai_twin_integrity"]["conclusion"])

    def test_ai_twin_overview_tool(self):
        result = self.mcp.call_tool("ai_twin_overview", {})
        self.assertIn("ai_twin_overview", result)
        self.assertIn("conclusion", result["ai_twin_overview"])

    def test_ai_twin_summary_tool(self):
        result = self.mcp.call_tool("ai_twin_summary", {})
        self.assertIn("ai_twin_summary", result)
        self.assertIn("health", result["ai_twin_summary"])

    def test_ai_twin_connectors_tool(self):
        result = self.mcp.call_tool("ai_twin_connectors", {})
        self.assertIn("ai_twin_connectors", result)
        self.assertIn("conclusion", result["ai_twin_connectors"])

    def test_ai_twin_reasoning_tool(self):
        result = self.mcp.call_tool("ai_twin_reasoning", {"query": "test", "mode": "cross_connector"})
        self.assertIn("ai_twin_reasoning", result)
        self.assertIn("conclusion", result["ai_twin_reasoning"])

    def test_ai_twin_report_tool(self):
        result = self.mcp.call_tool("ai_twin_report", {})
        self.assertIn("ai_twin_report", result)
        self.assertIn("report", result["ai_twin_report"])

    def test_all_previous_tools_preserved(self):
        tools = self.mcp.list_tools()
        names = [t["name"] for t in tools]
        legacy = ["search_memory", "build_context", "get_document", "get_recent_events",
                  "reindex_memory", "cross_reference", "explain_change", "get_causal_chain",
                  "compare_snapshots", "list_decisions", "get_decision", "search_semantic",
                  "get_similar", "get_awareness_signals", "list_connectors",
                  "get_connector_status", "get_connector_health_all", "get_evidence_stats",
                  "get_connector_evidence", "github_connector_status", "connector_sync",
                  "connector_metrics", "connector_last_sync", "connector_health_details",
                  "explain_project_state", "analyze_project_risk", "root_cause_analysis",
                  "impact_analysis", "project_health", "reasoning_trace",
                  "evidence_lineage", "dependency_graph",
                  "ai_twin_status", "ai_twin_health", "ai_twin_integrity",
                  "ai_twin_overview", "ai_twin_summary", "ai_twin_connectors",
                  "ai_twin_reasoning", "ai_twin_report"]
        for name in legacy:
            self.assertIn(name, names, "Tool missing: " + name)
        self.assertEqual(len(names), 44)  # 32 legacy + 8 Phase 18 + 1 Phase 19 + 1 Phase 7 + 2 Phase 8

    def test_unknown_tool_returns_error(self):
        result = self.mcp.call_tool("nonexistent_tool", {})
        self.assertIn("error", result)


# --- Service mcp_server.py Registration Tests ---

class TestMCPServerRegistration18(unittest.TestCase):
    def test_build_mcp_kernel_includes_phase18_services(self):
        from mcp.mcp_server import build_mcp_kernel
        kernel, services = build_mcp_kernel(tempfile.mkdtemp())
        service_names = [s.name for s in services]
        expected = ["AITwinOrchestrator", "TwinIntegrityValidator",
                    "UnifiedProjectTwin", "UniversalTwinReport"]
        for name in expected:
            self.assertIn(name, service_names, "Missing service: " + name)
        mcp_idx = service_names.index("MCPToolService")
        for name in expected:
            self.assertLess(service_names.index(name), mcp_idx,
                            "%s must be registered before MCPToolService" % name)
        for s in reversed(services):
            s.stop()

    def test_build_mcp_kernel_version_3_0_0(self):
        from mcp.mcp_server import build_mcp_kernel, MCPServer
        kernel, services = build_mcp_kernel(tempfile.mkdtemp())
        server = MCPServer()
        response = server.handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}})
        self.assertEqual(response["result"]["serverInfo"]["version"], "3.0.0")
        for s in reversed(services):
            s.stop()

    def test_build_mcp_kernel_40_tools(self):
        from mcp.mcp_server import build_mcp_kernel
        kernel, services = build_mcp_kernel(tempfile.mkdtemp())
        mcp_tool = kernel.get_service("MCPToolService")
        tools = mcp_tool.list_tools()
        self.assertEqual(len(tools), 44)
        for s in reversed(services):
            s.stop()


if __name__ == "__main__":
    unittest.main()
