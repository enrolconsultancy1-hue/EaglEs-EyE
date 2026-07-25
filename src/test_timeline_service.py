import os
import unittest

from services.timeline_service import TimelineService
from test_phase7_helpers import IntelligenceHarness


class TimelineServiceTests(unittest.TestCase):
    def test_reconstructs_ordered_event_evidence_without_inference(self):
        harness = IntelligenceHarness()
        timeline = TimelineService(harness.kernel)
        harness.kernel.register_service(timeline)
        timeline.start()
        try:
            first = os.path.join(harness.temp.name, "first.py")
            second = os.path.join(harness.temp.name, "second.py")
            for path in (first, second):
                with open(path, "w", encoding="utf-8") as file:
                    file.write("VALUE = 1\n")
                harness.indexer.reindex_path(path)
            harness.indexer.wait_until_idle()

            events = timeline.events()
            summary = timeline.session_summary()
            self.assertEqual([event["path"] for event in events], [first, second])
            self.assertEqual([event["citation"] for event in events], ["event:1", "event:2"])
            self.assertEqual(summary["event_types"], {"REINDEX": 2})
            self.assertEqual(summary["affected_paths"], sorted([first, second]))
            self.assertIn("no hidden reasoning", summary["scope"])
        finally:
            timeline.stop()
            harness.close()
