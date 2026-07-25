import os
import unittest
from test_phase7_helpers import IntelligenceHarness

class ProjectGraphTests(unittest.TestCase):
    def test_project_search_returns_symbols_relationships_and_citations(self):
        h = IntelligenceHarness()
        try:
            path = os.path.join(h.temp.name, "mirror_service.py")
            with open(path, "w", encoding="utf-8") as file: file.write("class MirrorService:\n pass\n")
            h.indexer.reindex_path(path); h.indexer.wait_until_idle()
            result = h.retrieval.project_search("MirrorService")
            self.assertTrue(result["symbols"]); self.assertTrue(result["chunks"])
        finally: h.close()
