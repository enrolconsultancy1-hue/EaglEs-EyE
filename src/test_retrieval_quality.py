import os
import unittest

from test_phase7_helpers import IntelligenceHarness


class RetrievalQualityTests(unittest.TestCase):
    def setUp(self):
        self.harness = IntelligenceHarness()
        for name, content in {"mirror.md": "MirrorService copies changed source files.", "watcher.md": "WatcherService emits filesystem events."}.items():
            path = os.path.join(self.harness.temp.name, name)
            with open(path, "w", encoding="utf-8") as file: file.write(content)
            self.harness.indexer.reindex_path(path)
        self.harness.indexer.wait_until_idle()
    def tearDown(self): self.harness.close()

    def test_ranked_results_have_complete_citations(self):
        results = self.harness.retrieval.search("MirrorService")
        self.assertEqual(results[0]["filename"], "mirror.md")
        for result in results:
            self.assertTrue(result["citation"])
            self.assertIn("score", result)
            self.assertIn("chunk_id", result)
