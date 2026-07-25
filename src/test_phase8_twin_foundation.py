import os
import unittest

from services.agent_detector_service import AgentDetectorService
from services.execution_timeline_service import ExecutionTimelineService
from services.replay_service import ReplayService
from services.session_recorder_service import SessionRecorderService
from services.twin_builder_service import TwinBuilderService
from services.workspace_observer_service import WorkspaceObserverService
from test_phase7_helpers import IntelligenceHarness


class Phase8TwinFoundationTests(unittest.TestCase):
    def setUp(self):
        self.harness = IntelligenceHarness()
        self.harness.kernel.set_config({"memory_path": self.harness.temp.name, "twins_path": os.path.join(self.harness.temp.name, "twins")})
        self.workspace = WorkspaceObserverService(self.harness.kernel)
        self.timeline = ExecutionTimelineService(self.harness.kernel)
        self.sessions = SessionRecorderService(self.harness.kernel)
        self.builder = TwinBuilderService(self.harness.kernel)
        self.replay = ReplayService(self.harness.kernel)
        self.detector = AgentDetectorService(self.harness.kernel)
        self.services = (self.workspace, self.timeline, self.sessions, self.builder, self.replay, self.detector)
        for service in self.services:
            self.harness.kernel.register_service(service)
            service.start()

    def tearDown(self):
        for service in reversed(self.services): service.stop()
        self.harness.close()

    def test_multi_workspace_sessions_are_isolated_and_replayable(self):
        first_path, second_path = (os.path.join(self.harness.temp.name, name) for name in ("first", "second"))
        os.makedirs(first_path); os.makedirs(second_path)
        first = self.workspace.register_workspace(first_path)
        second = self.workspace.register_workspace(second_path)
        first_session = self.sessions.start_session(first["id"], {"source": "test"})
        second_session = self.sessions.start_session(second["id"])
        self.sessions.record(first_session["id"], "FILE_MODIFIED", os.path.join(first_path, "app.py"), {"observable": True})
        self.sessions.record(second_session["id"], "TEST_OBSERVED", second_path, {"exit_code": 0})
        self.sessions.close_session(first_session["id"])

        first_events = self.timeline.events(session_id=first_session["id"])
        second_events = self.timeline.events(session_id=second_session["id"])
        twin = self.builder.build(first_session["id"])
        replay = self.replay.replay(twin["path"])

        self.assertEqual([event["path"] for event in first_events], [os.path.join(first_path, "app.py")])
        self.assertEqual([event["event_type"] for event in second_events], ["TEST_OBSERVED"])
        self.assertEqual(replay["evidence"], ["event:1"])
        self.assertEqual(replay["summary"]["session"]["id"], first_session["id"])
        self.assertTrue(os.path.exists(os.path.join(twin["path"], "events.json")))

    def test_active_sessions_are_recoverable_and_agent_detection_uses_markers(self):
        path = os.path.join(self.harness.temp.name, "agent")
        os.makedirs(path)
        with open(os.path.join(path, "AGENTS.md"), "w", encoding="utf-8") as target: target.write("observable marker\n")
        workspace = self.workspace.register_workspace(path)
        session = self.sessions.start_session(workspace["id"])

        recovered = self.sessions.recover_active_sessions(workspace["id"])
        detection = self.detector.detect(path)

        self.assertEqual([item["id"] for item in recovered], [session["id"]])
        self.assertEqual(detection["agents"][0]["agent"], "Codex")
        self.assertIn("no hidden reasoning", detection["scope"])
