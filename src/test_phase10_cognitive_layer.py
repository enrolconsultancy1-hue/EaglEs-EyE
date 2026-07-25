import os
import unittest

from services.causal_graph_service import CausalGraphService
from services.architecture_evolution_service import ArchitectureEvolutionService
from services.decision_tracking_service import DecisionTrackingService
from services.cognitive_layer_service import CognitiveLayerService
from services.execution_timeline_service import ExecutionTimelineService
from services.session_recorder_service import SessionRecorderService
from services.workspace_observer_service import WorkspaceObserverService
from test_phase7_helpers import IntelligenceHarness


class Phase10CognitiveLayerTests(unittest.TestCase):
    def setUp(self):
        self.harness = IntelligenceHarness()
        self.harness.kernel.set_config({
            "memory_path": self.harness.temp.name,
            "twins_path": os.path.join(self.harness.temp.name, "twins"),
        })
        self.workspace = WorkspaceObserverService(self.harness.kernel)
        self.timeline = ExecutionTimelineService(self.harness.kernel)
        self.sessions = SessionRecorderService(self.harness.kernel)
        self.causal = CausalGraphService(self.harness.kernel)
        self.evolution = ArchitectureEvolutionService(self.harness.kernel)
        self.decisions = DecisionTrackingService(self.harness.kernel)
        self.cognitive = CognitiveLayerService(self.harness.kernel)
        self.services = (self.workspace, self.timeline, self.sessions,
                         self.causal, self.evolution, self.decisions, self.cognitive)
        for service in self.services:
            self.harness.kernel.register_service(service)
            service.start()

    def tearDown(self):
        for service in reversed(self.services):
            service.stop()
        self.harness.close()

    def test_causal_edge_creation_and_traversal(self):
        ws_path = os.path.join(self.harness.temp.name, "causal_ws")
        os.makedirs(ws_path)
        ws = self.workspace.register_workspace(ws_path)
        session = self.sessions.start_session(ws["id"], {"agent": "test"})

        self.sessions.record(session["id"], "FILE_MODIFIED", os.path.join(ws_path, "feature.py"), {"lines": 10})
        self.sessions.record(session["id"], "TEST_OBSERVED", ws_path, {"exit_code": 1})
        self.sessions.record(session["id"], "FILE_MODIFIED", os.path.join(ws_path, "feature.py"), {"lines": 15})
        self.sessions.record(session["id"], "TEST_OBSERVED", ws_path, {"exit_code": 0})
        self.sessions.close_session(session["id"])

        events = self.timeline.events(session_id=session["id"])
        self.assertEqual(len(events), 4)

        edge_a = self.causal.link_events(events[0]["event_id"], events[1]["event_id"], "edit_then_test")
        edge_b = self.causal.link_events(events[1]["event_id"], events[2]["event_id"], "fail_then_fix")
        edge_c = self.causal.link_events(events[2]["event_id"], events[3]["event_id"], "edit_then_test")
        self.assertIsNotNone(edge_a)
        self.assertIsNotNone(edge_b)

        downstream = self.causal.get_downstream_events(events[0]["event_id"])
        self.assertEqual(len(downstream), 1)
        self.assertEqual(downstream[0]["event_type"], "TEST_OBSERVED")

        chain = self.causal.get_causal_chain(events[0]["event_id"], direction="forward")
        self.assertEqual(len(chain), 3)

        by_rel = self.causal.get_events_by_relation("edit_then_test")
        self.assertEqual(len(by_rel), 4)

    def test_architecture_snapshot_comparison(self):
        ws_path = os.path.join(self.harness.temp.name, "arch_ws")
        os.makedirs(ws_path)
        test_file = os.path.join(ws_path, "service_a.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("class ServiceA:\\n    pass\\n")
        self.harness.indexer.reindex_path(test_file)
        self.harness.indexer.wait_until_idle()

        ws = self.workspace.register_workspace(ws_path)
        session = self.sessions.start_session(ws["id"])
        snapshot_a = self.evolution.create_snapshot(ws["id"], session["id"], "before")
        self.assertIsNotNone(snapshot_a)
        self.assertEqual(snapshot_a["workspace_id"], ws["id"])

        self.sessions.record(session["id"], "FILE_MODIFIED", test_file, {"action": "add_service_b"})
        test_file_b = os.path.join(ws_path, "service_b.py")
        with open(test_file_b, "w", encoding="utf-8") as f:
            f.write("class ServiceB:\\n    pass\\n")
        self.harness.indexer.reindex_path(test_file_b)
        self.harness.indexer.wait_until_idle()

        snapshot_b = self.evolution.create_snapshot(ws["id"], session["id"], "after")
        self.assertIsNotNone(snapshot_b)

        diff = self.evolution.compare_snapshots(snapshot_a["id"], snapshot_b["id"])
        self.assertIn("added_paths", diff)
        self.assertIn("changed_paths", diff)
        self.assertIn("removed_paths", diff)

        snapshots = self.evolution.list_snapshots(workspace_id=ws["id"])
        self.assertEqual(len(snapshots), 2)

    def test_decision_persistence_and_query(self):
        ws_path = os.path.join(self.harness.temp.name, "decision_ws")
        os.makedirs(ws_path)
        ws = self.workspace.register_workspace(ws_path)
        session = self.sessions.start_session(ws["id"])

        decision_id = self.decisions.record_decision(
            workspace_id=ws["id"],
            session_id=session["id"],
            decision_type="refactor",
            summary="Extracted shared logic into helper method",
            evidence_citations=["event:1", "event:2"],
            payload={"file": "helper.py", "method": "extract_shared"},
        )
        self.assertIsNotNone(decision_id)
        self.assertGreater(decision_id, 0)

        records = self.decisions.get_decisions(workspace_id=ws["id"])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["decision_type"], "refactor")
        self.assertEqual(records[0]["evidence_citations"], ["event:1", "event:2"])

        single = self.decisions.get_decision(decision_id)
        self.assertIsNotNone(single)
        self.assertEqual(single["summary"], "Extracted shared logic into helper method")

    def test_citation_backed_explanation(self):
        ws_path = os.path.join(self.harness.temp.name, "explain_ws")
        os.makedirs(ws_path)
        test_file = os.path.join(ws_path, "retrieval_service.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("class RetrievalService:\\n    def search(self): pass\\n")
        self.harness.indexer.reindex_path(test_file)
        self.harness.indexer.wait_until_idle()

        ws = self.workspace.register_workspace(ws_path)
        session = self.sessions.start_session(ws["id"])

        self.sessions.record(session["id"], "FILE_MODIFIED", test_file, {"lines_added": 5})
        self.sessions.record(session["id"], "TEST_OBSERVED", ws_path, {"exit_code": 1})
        self.sessions.record(session["id"], "FILE_MODIFIED", test_file, {"lines_added": 3})
        self.sessions.record(session["id"], "TEST_OBSERVED", ws_path, {"exit_code": 0})
        self.sessions.close_session(session["id"])

        self.causal.link_events(1, 2, "edit_then_test")
        self.causal.link_events(2, 3, "fail_then_fix")
        self.causal.link_events(3, 4, "edit_then_test")

        self.decisions.record_decision(
            ws["id"], session["id"], "fix",
            "Fixed test failure by adjusting RetrievalService parameters",
            evidence_citations=["event:3"],
        )

        explanation = self.cognitive.explain_change("retrieval_service.py", workspace_id=ws["id"], session_id=session["id"])
        self.assertIn("entity", explanation)
        self.assertEqual(explanation["entity"], "retrieval_service.py")
        self.assertEqual(explanation["scope"], "Observable evidence only. No hidden reasoning is claimed.")
        self.assertIn("explanation", explanation)
        self.assertGreater(len(explanation["citations"]), 0)

        fact_count = explanation["observed_facts"]["event_count"]
        self.assertGreaterEqual(fact_count, 0)

        decision_count = explanation["observed_facts"]["decision_count"]
        self.assertGreaterEqual(decision_count, 0)

    def test_evidence_boundary_enforcement(self):
        explanation = self.cognitive.explain_change("nonexistent.py")
        self.assertIn("entity", explanation)
        self.assertIn("scope", explanation)
        self.assertNotIn("intent", explanation["explanation"].lower())
        self.assertNotIn("motive", explanation["explanation"].lower())
        self.assertNotIn("reasoning", explanation["explanation"].lower())

    def test_cognitive_query(self):
        result = self.cognitive.query("Why did RetrievalService change?")
        self.assertIn("question", result)
        self.assertIn("explanation", result)

    def test_causal_edge_invalid_event_graceful(self):
        result = self.causal.get_downstream_events(99999)
        self.assertEqual(result, [])

        result = self.causal.get_upstream_events(99999)
        self.assertEqual(result, [])
