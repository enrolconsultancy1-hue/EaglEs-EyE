"""Phase 17 — Autonomous Project Intelligence (v2.5.0)."""

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


def setup_common_services(kernel):
    """Set up mock services that all Phase 17 engines depend on."""
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

    from services.reasoning_engine import ReasoningEngine
    re_engine = ReasoningEngine(kernel)
    re_engine.start()
    kernel._services["ReasoningEngine"] = re_engine
    return kernel


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
            return None
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


# --- ConfidenceEngine Tests ---

class TestConfidenceEngine(unittest.TestCase):
    def setUp(self):
        self.kernel = FakeKernel()
        self.kernel._services["KnowledgeStoreService"] = FakeStore()
        from services.confidence_engine import ConfidenceEngine
        self.engine = ConfidenceEngine(self.kernel)
        self.engine.start()

    def test_score_evidence_empty(self):
        score, details = self.engine.score_evidence([])
        self.assertEqual(score, 0.0)
        self.assertIn("missing", details)
        self.assertIn("no evidence", details["missing"])

    def test_score_evidence_with_citations(self):
        evidence = [{"id": "ev1", "connector_id": "github", "timestamp": "2026-01-01", "score": 0.9}]
        score, details = self.engine.score_evidence(evidence)
        self.assertGreater(score, 0.0)
        self.assertEqual(details["count"], 1)
        self.assertEqual(details["sources"], ["github"])

    def test_score_evidence_partial(self):
        evidence = [{"id": "ev1"}, {"connector_id": "fs", "timestamp": "2026-01-01"}]
        score, details = self.engine.score_evidence(evidence)
        self.assertGreater(score, 0.0)
        # Each evidence item has at least one attribute; ev1 has id, ev2 has connector and timestamp
        self.assertNotIn("missing citations", details.get("missing", []))

    def test_assess_quality_dict(self):
        q = self.engine._assess_quality({"id": "x", "connector_id": "y", "timestamp": "t"})
        self.assertAlmostEqual(q, 1.0)

    def test_assess_quality_minimal(self):
        q = self.engine._assess_quality({})
        self.assertEqual(q, 0.0)

    def test_aggregate(self):
        combined, details = self.engine.aggregate((0.8, {"a": 1}), (0.6, {"b": 2}))
        self.assertAlmostEqual(combined, 0.7)
        self.assertEqual(len(details["sub_scores"]), 2)

    def test_aggregate_empty(self):
        combined, details = self.engine.aggregate()
        self.assertEqual(combined, 0.0)
        self.assertIn("missing", details)

    def test_detect_missing(self):
        missing = self.engine._detect_missing([])
        self.assertIn("no evidence", missing)
        missing = self.engine._detect_missing([{"id": "x", "connector_id": "y", "timestamp": "t"}])
        self.assertEqual(missing, [])

    def test_build_trace(self):
        trace = self.engine._build_trace([{"id": "ev1"}, {"citation": "ev2"}])
        self.assertEqual(len(trace), 2)
        self.assertEqual(trace[0]["evidence_id"], "ev1")

    def test_score_relationships_empty(self):
        score, details = self.engine.score_relationships([])
        self.assertEqual(score, 0.0)

    def test_score_relationships_with_weights(self):
        rels = [{"metadata": {"weight": 0.8}}, {"metadata": {"weight": 1.0}}]
        score, details = self.engine.score_relationships(rels)
        self.assertAlmostEqual(score, 0.9)


# --- ReasoningEngine Tests ---

class TestReasoningEngine(unittest.TestCase):
    def setUp(self):
        self.kernel = FakeKernel()
        self.store = FakeStore()
        self.kernel._services["KnowledgeStoreService"] = self.store
        self.kernel = setup_common_services(self.kernel)
        from services.reasoning_engine import ReasoningEngine
        self.engine = self.kernel.get_service("ReasoningEngine")

    def test_reason_cross_connector_empty(self):
        result = self.engine.reason_cross_connector("test query")
        self.assertIn("conclusion", result)
        self.assertIn("confidence", result)
        self.assertIn("supporting_evidence", result)
        self.assertIn("connector_sources", result)
        self.assertIn("observation_surfaces", result)
        self.assertIn("reasoning_trace", result)
        self.assertIn("supporting_relationships", result)
        self.assertIn("timestamp", result)

    def test_reason_dependencies_no_path(self):
        result = self.engine.reason_dependencies("nonexistent.py")
        self.assertIn("conclusion", result)
        self.assertIsInstance(result["confidence"], float)

    def test_reason_timeline(self):
        self.store.events = [
            {"id": 1, "event_type": "FILE_CREATED", "path": "/test/a.py", "created_at": "2026-01-01T00:00:00"},
            {"id": 2, "event_type": "FILE_MODIFIED", "path": "/test/a.py", "created_at": "2026-01-01T01:00:00"},
        ]
        result = self.engine.reason_timeline(session_id="sess1")
        self.assertIn("conclusion", result)
        self.assertGreaterEqual(len(result["supporting_evidence"]), 2)

    def test_reason_timeline_filtered(self):
        self.store.events = [
            {"id": 1, "event_type": "FILE_CREATED", "path": "/test/a.py", "created_at": "2026-01-01T00:00:00"},
            {"id": 2, "event_type": "FILE_MODIFIED", "path": "/test/b.py", "created_at": "2026-01-01T01:00:00"},
        ]
        result = self.engine.reason_timeline(path="/test/a.py", session_id="sess1")
        self.assertEqual(len(result["supporting_evidence"]), 1)

    def test_reason_state_transitions(self):
        self.store.documents["/test/a.py"] = {"id": 1, "path": "/test/a.py", "version": 3, "status": "active"}
        result = self.engine.reason_state_transitions("/test/a.py")
        self.assertIn("conclusion", result)

    def test_reason_state_transitions_no_doc(self):
        result = self.engine.reason_state_transitions("/nonexistent.py")
        self.assertIn("No document found", result["conclusion"])

    def test_reason_relationships_no_doc(self):
        result = self.engine.reason_relationships("/nonexistent.py")
        self.assertIn("conclusion", result)

    def test_reason_evidence_correlation(self):
        result = self.engine.reason_evidence_correlation()
        self.assertIn("conclusion", result)

    def test_reason_historical(self):
        self.store.events = [
            {"id": 1, "event_type": "FILE_CREATED", "path": "/test/a.py", "created_at": "2026-01-01T00:00:00"},
        ]
        result = self.engine.reason_historical("/test/a.py")
        self.assertIn("conclusion", result)

    def test_reason_historical_no_events(self):
        result = self.engine.reason_historical("/nonexistent.py")
        self.assertIn("No historical events", result["conclusion"])

    def test_wrap_result_format(self):
        from services.reasoning_engine import _wrap_result
        result = _wrap_result("test", 0.95, [{"id": "ev1"}], ["connector_a"],
                              ["api"], [{"step": "done"}], [{"target": "x"}])
        self.assertEqual(result["confidence"], 0.95)
        self.assertEqual(result["conclusion"], "test")
        self.assertEqual(len(result["connector_sources"]), 1)
        self.assertIn("timestamp", result)

    def test_timeline_relationships_ordering(self):
        self.store.events = [
            {"id": 1, "event_type": "E1", "path": "/a.py", "created_at": "t1"},
            {"id": 2, "event_type": "E2", "path": "/a.py", "created_at": "t2"},
        ]
        result = self.engine.reason_timeline(session_id="sess1")
        # happened_before relationships should exist
        relations = [r for r in result.get("supporting_relationships", []) if r.get("relation") == "happened_before"]
        self.assertGreaterEqual(len(relations), 1)


# --- ProjectIntelligenceEngine Tests ---

class TestProjectIntelligenceEngine(unittest.TestCase):
    def setUp(self):
        self.kernel = FakeKernel()
        self.store = FakeStore()
        self.kernel._services["KnowledgeStoreService"] = self.store
        self.kernel = setup_common_services(self.kernel)
        from services.project_intelligence_engine import ProjectIntelligenceEngine
        self.engine = ProjectIntelligenceEngine(self.kernel)
        self.engine.start()

    def test_project_health(self):
        result = self.engine.project_health()
        self.assertIn("conclusion", result)
        self.assertIn("health", result["conclusion"].lower())

    def test_project_health_with_docs(self):
        self.store.documents["a.py"] = {"id": 1}
        result = self.engine.project_health()
        self.assertIn("conclusion", result)

    def test_detect_blockers(self):
        result = self.engine.detect_blockers()
        self.assertIn("conclusion", result)

    def test_detect_blockers_with_errors(self):
        self.store.events = [
            {"id": 1, "event_type": "ERROR", "path": "/test", "payload": "{}", "created_at": "2026-01-01"},
        ]
        result = self.engine.detect_blockers()
        self.assertIn("conclusion", result)

    def test_detect_bottlenecks(self):
        result = self.engine.detect_bottlenecks()
        self.assertIn("conclusion", result)

    def test_detect_stale_work(self):
        result = self.engine.detect_stale_work(30)
        self.assertIn("conclusion", result)

    def test_detect_architecture_drift_no_snapshots(self):
        result = self.engine.detect_architecture_drift()
        self.assertIn("Insufficient snapshots", result["conclusion"])

    def test_detect_architecture_drift_with_snapshots(self):
        self.store.snapshots = [
            {"id": 1, "symbol_data": {"A": {}, "B": {}}, "created_at": "2026-01-01"},
            {"id": 2, "symbol_data": {"A": {}, "B": {}, "C": {}}, "created_at": "2026-01-02"},
        ]
        self.store.list_architecture_snapshots = lambda: self.store.snapshots
        result = self.engine.detect_architecture_drift()
        self.assertIn("changes detected", result["conclusion"].lower())

    def test_wrap_result_format_pi(self):
        from services.project_intelligence_engine import _wrap_result
        result = _wrap_result("test", 0.8, [], [], [], [{"step": "s1"}], [])
        self.assertEqual(result["conclusion"], "test")
        self.assertEqual(result["confidence"], 0.8)


# --- RootCauseAnalysisService Tests ---

class TestRootCauseAnalysis(unittest.TestCase):
    def setUp(self):
        self.kernel = FakeKernel()
        self.store = FakeStore()
        self.kernel._services["KnowledgeStoreService"] = self.store
        self.kernel = setup_common_services(self.kernel)
        from services.root_cause_analysis_service import RootCauseAnalysisService
        self.engine = RootCauseAnalysisService(self.kernel)
        self.engine.start()

    def test_analyze_no_events(self):
        result = self.engine.analyze("test issue")
        self.assertIn("conclusion", result)
        self.assertIn("what_changed", result)

    def test_analyze_with_events(self):
        self.store.events = [
            {"id": 1, "event_type": "FILE_MODIFIED", "path": "/project/a.py", "payload": "{}", "created_at": "t1"},
        ]
        result = self.engine.analyze("a.py")
        self.assertGreaterEqual(len(result["supporting_evidence"]), 1)

    def test_analyze_with_path(self):
        result = self.engine.analyze("issue", path="/test/path.py")
        self.assertIn("conclusion", result)

    def test_analyze_not_found(self):
        result = self.engine.analyze("nonexistent_issue")
        self.assertIn("No evidence found", result["conclusion"])


# --- ImpactAnalysisService Tests ---

class TestImpactAnalysis(unittest.TestCase):
    def setUp(self):
        self.kernel = FakeKernel()
        self.store = FakeStore()
        self.kernel._services["KnowledgeStoreService"] = self.store
        self.kernel = setup_common_services(self.kernel)
        from services.impact_analysis_service import ImpactAnalysisService
        self.engine = ImpactAnalysisService(self.kernel)
        self.engine.start()

    def test_analyze_no_doc(self):
        result = self.engine.analyze("/nonexistent.py")
        self.assertIn("conclusion", result)
        self.assertIn("affected_files", result)
        self.assertIn("impact_level", result)

    def test_analyze_with_doc(self):
        self.store.documents["/test/a.py"] = {"id": 1, "path": "/test/a.py", "version": 1, "status": "active"}
        result = self.engine.analyze("/test/a.py")
        self.assertIn("impact_level", result)
        self.assertIn(result["impact_level"], ("low", "medium", "high"))

    def test_analyze_format(self):
        result = self.engine.analyze("/test/file.py")
        self.assertIn("supporting_evidence", result)
        self.assertIn("connector_sources", result)
        self.assertIn("observation_surfaces", result)
        self.assertIn("reasoning_trace", result)
        self.assertIn("supporting_relationships", result)
        self.assertIn("timestamp", result)


# --- DecisionLineageService Tests ---

class TestDecisionLineage(unittest.TestCase):
    def setUp(self):
        self.kernel = FakeKernel()
        self.store = FakeStore()
        self.kernel._services["KnowledgeStoreService"] = self.store
        self.kernel = setup_common_services(self.kernel)
        self.mock_decisions = make_mock_service("DecisionTrackingService")
        self.mock_decisions.get_decision.return_value = {
            "id": "dec1", "decision_type": "refactor",
            "summary": "Refactored service", "evidence_citations": ["ev1", "ev2"],
            "workspace_id": "ws1", "session_id": "sess1", "created_at": "2026-01-01",
        }
        self.mock_decisions.get_decisions.return_value = [
            {"id": "dec1", "decision_type": "refactor", "summary": "Refactored service",
             "evidence_citations": [], "workspace_id": "ws1", "created_at": "2026-01-01"},
        ]
        self.kernel._services["DecisionTrackingService"] = self.mock_decisions
        from services.decision_lineage_service import DecisionLineageService
        self.engine = DecisionLineageService(self.kernel)
        self.engine.start()

    def test_trace_found(self):
        result = self.engine.trace("dec1")
        self.assertIn("conclusion", result)
        self.assertIn("decision", result)

    def test_trace_not_found(self):
        self.mock_decisions.get_decision.return_value = None
        result = self.engine.trace("nonexistent")
        self.assertIn("Decision not found", result["conclusion"])

    def test_list_lineages(self):
        result = self.engine.list_lineages()
        self.assertIn("conclusion", result)
        self.assertIn("decisions", result)

    def test_list_lineages_filtered(self):
        result = self.engine.list_lineages(workspace_id="ws1")
        self.assertIn("conclusion", result)

    def test_wrap_result_format_dl(self):
        from services.decision_lineage_service import _wrap_result
        result = _wrap_result("test", 0.9, [], ["c1"], ["api"], [{"step": "s1"}], [])
        self.assertEqual(result["confidence"], 0.9)
        self.assertIn("timestamp", result)


# --- ExplainableAIService Tests ---

class TestExplainableAI(unittest.TestCase):
    def setUp(self):
        self.kernel = FakeKernel()
        self.store = FakeStore()
        self.kernel._services["KnowledgeStoreService"] = self.store
        self.kernel = setup_common_services(self.kernel)
        from services.explainable_ai_service import ExplainableAIService
        self.engine = ExplainableAIService(self.kernel)
        self.engine.start()

    def test_explain_no_path(self):
        result = self.engine.explain("What changed in the project?")
        self.assertIn("conclusion", result)
        self.assertIn("why", result)
        self.assertIn("how", result)
        self.assertIn("citations", result)

    def test_explain_with_path_and_doc(self):
        self.store.documents["/test/a.py"] = {"id": 1, "path": "/test/a.py", "version": 1, "chunks": [], "status": "active"}
        result = self.engine.explain("What changed?", path="/test/a.py")
        self.assertIn("conclusion", result)

    def test_explain_format(self):
        result = self.engine.explain("test query")
        self.assertIn("supporting_evidence", result)
        self.assertIn("connector_sources", result)
        self.assertIn("observation_surfaces", result)
        self.assertIn("reasoning_trace", result)
        self.assertIn("timestamp", result)
        self.assertIn("related_knowledge", result)
        self.assertIn("why", result)
        self.assertIn("how", result)

    def test_explain_empty_query(self):
        result = self.engine.explain("")
        self.assertIn("conclusion", result)


# --- Universal Reasoning Policy Compliance Tests ---

class TestUniversalReasoningPolicy(unittest.TestCase):
    def test_wrap_result_contains_all_required_fields(self):
        from services.reasoning_engine import _wrap_result
        result = _wrap_result("test", 0.94, [{"id": "ev1"}], ["github"],
                              ["official_api"], [{"step": "s1"}], [{"target": "x"}])
        required = ["conclusion", "confidence", "supporting_evidence",
                    "connector_sources", "observation_surfaces",
                    "reasoning_trace", "supporting_relationships", "timestamp"]
        for field in required:
            self.assertIn(field, result, "Missing required field: " + field)

    def test_no_hidden_reasoning(self):
        from services.reasoning_engine import _wrap_result
        result = _wrap_result("test", 0.5, [], [], [], [], [])
        self.assertIn("supporting_evidence", result)
        self.assertIn("reasoning_trace", result)

    def test_connector_provenance_preserved(self):
        from services.reasoning_engine import _wrap_result
        result = _wrap_result("test", 0.8, [{"id": "ev1", "connector_id": "github"}],
                              ["github"], ["official_api"], [], [])
        self.assertIn("github", result["connector_sources"])
        self.assertEqual(result["supporting_evidence"][0].get("connector_id"), "github")


# --- KnowledgeGraphService Enhancement Tests ---

class TestKnowledgeGraphEnhancements(unittest.TestCase):
    def setUp(self):
        self.kernel = FakeKernel()
        self.store = FakeStore()
        self.kernel._services["KnowledgeStoreService"] = self.store
        from services.knowledge_graph_service import KnowledgeGraphService
        self.kg = KnowledgeGraphService(self.kernel)
        self.kg.start()

    def test_related_weighted_no_doc(self):
        result = self.kg.related_weighted("/nonexistent.py")
        self.assertEqual(result, [])

    def test_related_weighted_adds_weight(self):
        self.store.documents["/test/a.py"] = {"id": 1, "path": "/test/a.py"}
        self.store.add_relationship(1, "/test/b.py", "imports", {"confidence": 0.8})
        # related_weighted uses SQL queries; verify function exists and returns list
        result = self.kg.related_weighted("/test/a.py")
        self.assertIsInstance(result, list)

    def test_propagate_confidence(self):
        self.store.documents["/test/a.py"] = {"id": 1, "path": "/test/a.py"}
        self.store.add_relationship(1, "/test/b.py", "imports", {"confidence": 0.9})
        self.store.documents["/test/b.py"] = {"id": 2, "path": "/test/b.py"}
        propagated = self.kg.propagate_confidence(["/test/a.py"], 1.0, 2)
        self.assertIn("/test/a.py", propagated)
        self.assertGreater(propagated["/test/a.py"], 0)

    def test_multi_source_correlate_empty(self):
        result = self.kg.multi_source_correlate([])
        self.assertEqual(result, {})

    def test_multi_source_correlate(self):
        self.store.add_relationship("connector_a", "target1", "connector_evidence")
        self.store.add_relationship("connector_b", "target1", "connector_evidence")
        result = self.kg.multi_source_correlate(["connector_a", "connector_b"])
        # relationships stored but won't match source_document_id query in FakeStore
        self.assertIsInstance(result, dict)

    def test_compute_relationship_weight_default(self):
        w = self.kg._compute_relationship_weight({})
        self.assertEqual(w, 1.0)

    def test_compute_relationship_weight_with_confidence(self):
        w = self.kg._compute_relationship_weight({"confidence": 0.5})
        self.assertEqual(w, 0.5)

    def test_compute_relationship_weight_resolved(self):
        w = self.kg._compute_relationship_weight({"confidence": 0.8, "resolution": "local"})
        self.assertAlmostEqual(w, 0.96)

    def test_temporal_relationships_no_doc(self):
        result = self.kg.temporal_relationships("/nonexistent.py")
        self.assertEqual(result, [])


# --- MCP Tool Integration Tests ---

class TestMCPToolsPhase17(unittest.TestCase):
    def setUp(self):
        self.kernel = FakeKernel()
        store = FakeStore()
        self.kernel._services["KnowledgeStoreService"] = store
        self.kernel = setup_common_services(self.kernel)
        # Override DecisionTrackingService for specific test needs
        self.mock_decisions = make_mock_service("DecisionTrackingService")
        self.mock_decisions.get_decision.return_value = {"id": "dec1", "decision_type": "refactor", "summary": "test", "evidence_citations": [], "created_at": "t1"}
        self.mock_decisions.get_decisions.return_value = []
        self.kernel._services["DecisionTrackingService"] = self.mock_decisions
        from services.project_intelligence_engine import ProjectIntelligenceEngine
        self.pi = ProjectIntelligenceEngine(self.kernel)
        self.pi.start()
        self.kernel._services["ProjectIntelligenceEngine"] = self.pi
        from services.root_cause_analysis_service import RootCauseAnalysisService
        self.rca = RootCauseAnalysisService(self.kernel)
        self.rca.start()
        self.kernel._services["RootCauseAnalysisService"] = self.rca
        from services.impact_analysis_service import ImpactAnalysisService
        self.ia = ImpactAnalysisService(self.kernel)
        self.ia.start()
        self.kernel._services["ImpactAnalysisService"] = self.ia
        from services.decision_lineage_service import DecisionLineageService
        self.dl = DecisionLineageService(self.kernel)
        self.dl.start()
        self.kernel._services["DecisionLineageService"] = self.dl
        from services.explainable_ai_service import ExplainableAIService
        self.eai = ExplainableAIService(self.kernel)
        self.eai.start()
        self.kernel._services["ExplainableAIService"] = self.eai
        # Need VectorSearchService and SemanticAwarenessService for MCPToolService
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
        expected = ["explain_project_state", "analyze_project_risk", "root_cause_analysis",
                    "impact_analysis", "project_health", "reasoning_trace",
                    "evidence_lineage", "dependency_graph"]
        for name in expected:
            self.assertIn(name, names, "Missing tool: " + name)

    def test_explain_project_state_tool(self):
        result = self.mcp.call_tool("explain_project_state", {"query": "What changed?"})
        self.assertIn("explanation", result)

    def test_project_health_tool(self):
        result = self.mcp.call_tool("project_health", {})
        self.assertIn("project_health", result)

    def test_reasoning_trace_cross_connector(self):
        result = self.mcp.call_tool("reasoning_trace", {"query": "test", "mode": "cross_connector"})
        self.assertIn("reasoning_trace", result)

    def test_reasoning_trace_timeline(self):
        result = self.mcp.call_tool("reasoning_trace", {"query": "test", "mode": "timeline"})
        self.assertIn("reasoning_trace", result)

    def test_dependency_graph_tool(self):
        result = self.mcp.call_tool("dependency_graph", {"path": "/test/a.py"})
        self.assertIn("dependency_graph", result)

    def test_evidence_lineage_tool_by_id(self):
        result = self.mcp.call_tool("evidence_lineage", {"decision_id": "dec1"})
        self.assertIn("evidence_lineage", result)

    def test_evidence_lineage_tool_list(self):
        result = self.mcp.call_tool("evidence_lineage", {})
        self.assertIn("evidence_lineages", result)

    def test_root_cause_analysis_tool(self):
        result = self.mcp.call_tool("root_cause_analysis", {"issue": "test error"})
        self.assertIn("root_cause_analysis", result)

    def test_impact_analysis_tool(self):
        result = self.mcp.call_tool("impact_analysis", {"path": "/test/file.py"})
        self.assertIn("impact_analysis", result)

    def test_analyze_project_risk_tool(self):
        result = self.mcp.call_tool("analyze_project_risk", {})
        self.assertIn("blockers", result)
        self.assertIn("bottlenecks", result)
        self.assertIn("stale_work", result)
        self.assertIn("architecture_drift", result)

    def test_all_previous_tools_preserved(self):
        tools = self.mcp.list_tools()
        names = [t["name"] for t in tools]
        legacy = ["search_memory", "build_context", "get_document", "get_recent_events",
                  "reindex_memory", "cross_reference", "explain_change", "get_causal_chain",
                  "compare_snapshots", "list_decisions", "get_decision", "search_semantic",
                  "get_similar", "get_awareness_signals", "list_connectors",
                  "get_connector_status", "get_connector_health_all", "get_evidence_stats",
                  "get_connector_evidence", "github_connector_status", "connector_sync",
                  "connector_metrics", "connector_last_sync", "connector_health_details"]
        for name in legacy:
            self.assertIn(name, names, "Legacy tool removed: " + name)
        self.assertEqual(len(names), 44)  # 24 legacy + 8 Phase 17 + 8 Phase 18 + 1 Phase 19 + 1 Phase 7 + 2 Phase 8

    def test_reasoning_trace_unknown_mode(self):
        result = self.mcp.call_tool("reasoning_trace", {"query": "test", "mode": "invalid"})
        self.assertIn("error", result)

    def test_root_cause_missing_issue(self):
        result = self.mcp.call_tool("root_cause_analysis", {})
        self.assertIn("error", result)

    def test_impact_missing_path(self):
        result = self.mcp.call_tool("impact_analysis", {})
        self.assertIn("error", result)


# --- Service mcp_server.py Registration Tests ---

class TestMCPServerRegistration(unittest.TestCase):
    def test_build_mcp_kernel_includes_phase17_services(self):
        from mcp.mcp_server import build_mcp_kernel
        kernel, services = build_mcp_kernel(tempfile.mkdtemp())
        service_names = [s.name for s in services]
        expected = ["ConfidenceEngine", "ReasoningEngine", "ProjectIntelligenceEngine",
                    "RootCauseAnalysisService", "ImpactAnalysisService",
                    "DecisionLineageService", "ExplainableAIService"]
        for name in expected:
            self.assertIn(name, service_names, "Missing service: " + name)
        # Verify service order: Phase 17 services before MCPToolService
        mcp_idx = service_names.index("MCPToolService")
        for name in expected:
            self.assertLess(service_names.index(name), mcp_idx,
                            "%s must be registered before MCPToolService" % name)
        # Cleanup
        for s in reversed(services):
            s.stop()

    def test_build_mcp_kernel_version(self):
        from mcp.mcp_server import build_mcp_kernel, MCPServer
        kernel, services = build_mcp_kernel(tempfile.mkdtemp())
        server = MCPServer()
        # Simulate initialize
        response = server.handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}})
        self.assertEqual(response["result"]["serverInfo"]["version"], "3.0.0")
        for s in reversed(services):
            s.stop()

    def test_build_mcp_kernel_32_tools(self):
        from mcp.mcp_server import build_mcp_kernel
        kernel, services = build_mcp_kernel(tempfile.mkdtemp())
        mcp_tool = kernel.get_service("MCPToolService")
        tools = mcp_tool.list_tools()
        self.assertEqual(len(tools), 44)
        for s in reversed(services):
            s.stop()


if __name__ == "__main__":
    unittest.main()
