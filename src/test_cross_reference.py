import os
import unittest

from test_phase7_helpers import IntelligenceHarness


class CrossReferenceTests(unittest.TestCase):
    def test_service_usage_question_returns_graph_and_document_evidence(self):
        harness = IntelligenceHarness()
        try:
            path = os.path.join(harness.temp.name, "app.py")
            with open(path, "w", encoding="utf-8") as file:
                file.write("class MirrorService: pass\ndef setup(kernel): kernel.register_service(MirrorService(kernel))\n")
            harness.indexer.reindex_path(path); harness.indexer.wait_until_idle()
            result = harness.cross_reference.find("MirrorService")
            self.assertTrue(result["definitions"])
            self.assertTrue(result["documents"])
        finally:
            harness.close()
