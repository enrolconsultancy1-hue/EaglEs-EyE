import os
import unittest

from services.session_reconstruction_service import SessionReconstructionService
from services.timeline_service import TimelineService
from test_phase7_helpers import IntelligenceHarness


class SessionReconstructionServiceTests(unittest.TestCase):
    def test_reconstructs_a_cited_replay_from_observed_events(self):
        harness = IntelligenceHarness()
        timeline = TimelineService(harness.kernel)
        reconstruction = SessionReconstructionService(harness.kernel)
        for service in (timeline, reconstruction):
            harness.kernel.register_service(service)
            service.start()
        try:
            path = os.path.join(harness.temp.name, "observer.py")
            with open(path, "w", encoding="utf-8") as file:
                file.write("VALUE = 1\n")
            harness.indexer.reindex_path(path)
            harness.indexer.wait_until_idle()

            result = reconstruction.reconstruct("session-001")

            self.assertEqual(result["session_id"], "session-001")
            self.assertEqual(result["replay"][0]["path"], path)
            self.assertEqual(result["evidence"], ["event:1"])
            self.assertIn("does not claim hidden reasoning", result["limitations"])
        finally:
            reconstruction.stop()
            timeline.stop()
            harness.close()
