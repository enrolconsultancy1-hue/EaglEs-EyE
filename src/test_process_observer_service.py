import os
import unittest

from services.engineering_evidence_service import EngineeringEvidenceService
from services.process_observer_service import ProcessObserverService
from services.timeline_service import TimelineService
from test_phase7_helpers import IntelligenceHarness


class ProcessObserverServiceTests(unittest.TestCase):
    def setUp(self):
        self.harness = IntelligenceHarness()
        self.evidence = EngineeringEvidenceService(self.harness.kernel)
        self.timeline = TimelineService(self.harness.kernel)
        self.observer = ProcessObserverService(self.harness.kernel)
        for service in (self.evidence, self.timeline, self.observer):
            self.harness.kernel.register_service(service)
            service.start()

    def tearDown(self):
        self.observer.stop()
        self.timeline.stop()
        self.evidence.stop()
        self.harness.close()

    def test_records_observed_build_test_and_terminal_results(self):
        workspace = os.path.join(self.harness.temp.name, "workspace")
        self.observer.observe_build(workspace, "python -m build", 0, "Built package")
        self.observer.observe_test(workspace, "python -m unittest", 0, "Ran 3 tests")
        self.observer.observe_terminal(workspace, "git status --short", " M README.md", 0)

        events = self.timeline.events()

        self.assertEqual(
            [event["event_type"] for event in events],
            ["BUILD_OBSERVED", "TEST_OBSERVED", "TERMINAL_OBSERVED"],
        )
        self.assertTrue(all(event["payload"]["observer"] == "external_process_observer" for event in events))
        self.assertEqual(events[1]["payload"]["command"], "python -m unittest")
        self.assertEqual(events[2]["payload"]["exit_code"], 0)
