import os
import unittest

from services.engineering_evidence_service import EngineeringEvidenceService
from services.git_observer_service import GitObserverService
from services.timeline_service import TimelineService
from test_phase7_helpers import IntelligenceHarness


class GitObserverServiceTests(unittest.TestCase):
    def setUp(self):
        self.harness = IntelligenceHarness()
        self.evidence = EngineeringEvidenceService(self.harness.kernel)
        self.timeline = TimelineService(self.harness.kernel)
        for service in (self.evidence, self.timeline):
            self.harness.kernel.register_service(service)
            service.start()

    def tearDown(self):
        self.timeline.stop()
        self.evidence.stop()
        self.harness.close()

    def test_records_a_read_only_git_snapshot(self):
        responses = {
            ("status", "--porcelain=v1", "--branch"): {"exit_code": 0, "output": "## main\n M src/app.py\n"},
            ("rev-parse", "HEAD"): {"exit_code": 0, "output": "abc123\n"},
            ("branch", "--show-current"): {"exit_code": 0, "output": "main\n"},
        }
        observer = GitObserverService(
            self.harness.kernel, lambda workspace, *args: responses[args]
        )
        self.harness.kernel.register_service(observer)
        observer.start()
        try:
            result = observer.observe(os.path.join(self.harness.temp.name, "workspace"))
            event = self.timeline.events()[0]
            self.assertTrue(result["observed"])
            self.assertEqual(event["event_type"], "GIT_OBSERVED")
            self.assertEqual(event["payload"]["branch"], "main")
            self.assertEqual(event["payload"]["head"], "abc123")
            self.assertIn("src/app.py", event["payload"]["status_porcelain"])
        finally:
            observer.stop()

    def test_reports_non_repository_without_recording_an_event(self):
        observer = GitObserverService(
            self.harness.kernel, lambda workspace, *args: {"exit_code": 128, "output": "not a repository"}
        )
        self.harness.kernel.register_service(observer)
        observer.start()
        try:
            result = observer.observe(self.harness.temp.name)
            self.assertFalse(result["observed"])
            self.assertEqual(self.timeline.events(), [])
        finally:
            observer.stop()
