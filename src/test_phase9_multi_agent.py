import os
import unittest

from services.workspace_observer_service import WorkspaceObserverService
from services.execution_timeline_service import ExecutionTimelineService
from services.session_recorder_service import SessionRecorderService
from services.agent_detector_service import AgentDetectorService
from services.multi_agent_observation_service import MultiAgentObservationService
from test_phase7_helpers import IntelligenceHarness


class Phase9MultiAgentTests(unittest.TestCase):
    def setUp(self):
        self.harness = IntelligenceHarness()
        self.harness.kernel.set_config({
            "memory_path": self.harness.temp.name,
            "twins_path": os.path.join(self.harness.temp.name, "twins")
        })
        self.workspace = WorkspaceObserverService(self.harness.kernel)
        self.timeline = ExecutionTimelineService(self.harness.kernel)
        self.sessions = SessionRecorderService(self.harness.kernel)
        self.detector = AgentDetectorService(self.harness.kernel)
        self.multi_agent = MultiAgentObservationService(self.harness.kernel)
        self.services = (self.workspace, self.timeline, self.sessions, self.detector, self.multi_agent)
        for service in self.services:
            self.harness.kernel.register_service(service)
            service.start()

    def tearDown(self):
        for service in reversed(self.services):
            service.stop()
        self.harness.close()

    def test_multi_agent_session_and_agent_comparison(self):
        ws_path = os.path.join(self.harness.temp.name, "multi_agent_ws")
        os.makedirs(ws_path)
        # Create agent markers for Codex and Claude Code
        os.makedirs(os.path.join(ws_path, ".codex"), exist_ok=True)
        os.makedirs(os.path.join(ws_path, ".claude"), exist_ok=True)

        ws = self.workspace.register_workspace(ws_path)
        session_codex = self.sessions.start_session(ws["id"], {"agent": "Codex"})
        session_claude = self.sessions.start_session(ws["id"], {"agent": "Claude Code"})

        self.sessions.record(session_codex["id"], "FILE_MODIFIED", os.path.join(ws_path, "feature.py"), {"lines": 10})
        self.sessions.record(session_codex["id"], "TEST_OBSERVED", ws_path, {"exit_code": 0})

        self.sessions.record(session_claude["id"], "FILE_MODIFIED", os.path.join(ws_path, "feature.py"), {"lines": 12})
        self.sessions.record(session_claude["id"], "TEST_OBSERVED", ws_path, {"exit_code": 0})
        self.sessions.record(session_claude["id"], "BUILD_OBSERVED", ws_path, {"status": "success"})

        self.sessions.close_session(session_codex["id"])
        self.sessions.close_session(session_claude["id"])

        # Run multi-agent comparisons
        session_comp = self.multi_agent.compare_sessions([session_codex["id"], session_claude["id"]])
        self.assertEqual(len(session_comp["sessions"]), 2)
        self.assertEqual(session_comp["sessions"][0]["event_count"], 2)
        self.assertEqual(session_comp["sessions"][1]["event_count"], 3)

        timeline_comp = self.multi_agent.compare_timelines([session_codex["id"], session_claude["id"]])
        self.assertEqual(timeline_comp["max_steps"], 3)

        perf_comp = self.multi_agent.compare_performance([session_codex["id"], session_claude["id"]])
        self.assertEqual(len(perf_comp["performance"]), 2)
        self.assertEqual(perf_comp["performance"][0]["test_success_count"], 1)

        arch_comp = self.multi_agent.compare_architecture([session_codex["id"], session_claude["id"]])
        self.assertEqual(len(arch_comp["architecture_impact"]), 2)
        self.assertIn(os.path.join(ws_path, "feature.py"), arch_comp["architecture_impact"][0]["files_touched"])

        agent_comp = self.multi_agent.compare_agents([ws_path])
        self.assertEqual(len(agent_comp["comparison"][0]["detection"]["agents"]), 2)
