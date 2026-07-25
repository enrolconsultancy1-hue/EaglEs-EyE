import os
import unittest

from services.engineering_evidence_service import EngineeringEvidenceService
from services.timeline_service import TimelineService
from test_phase7_helpers import IntelligenceHarness


class EngineeringEvidenceServiceTests(unittest.TestCase):
    def test_records_explicit_evidence_for_timeline_replay(self):
        harness = IntelligenceHarness()
        evidence = EngineeringEvidenceService(harness.kernel)
        timeline = TimelineService(harness.kernel)
        for service in (evidence, timeline):
            harness.kernel.register_service(service)
            service.start()
        try:
            workspace = os.path.join(harness.temp.name, "workspace")
            result = evidence.record_test(workspace, "python -m unittest", 0, "Ran 1 test")
            events = timeline.events()

            self.assertEqual(result["event_type"], "TEST_OBSERVED")
            self.assertEqual(events[0]["event_type"], "TEST_OBSERVED")
            self.assertEqual(events[0]["payload"]["command"], "python -m unittest")
            self.assertEqual(events[0]["payload"]["exit_code"], 0)
            self.assertEqual(events[0]["payload"]["evidence_kind"], "test")
        finally:
            timeline.stop()
            evidence.stop()
            harness.close()
