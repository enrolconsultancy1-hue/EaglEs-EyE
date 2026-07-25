import os
import unittest
from test_phase7_helpers import IntelligenceHarness

class DocumentationLinkTests(unittest.TestCase):
    def test_identifies_documented_and_undocumented_services(self):
        h = IntelligenceHarness()
        try:
            path = os.path.join(h.temp.name, "services.py")
            with open(path, "w", encoding="utf-8") as file: file.write("class MirrorService: pass\nclass HiddenService: pass\n")
            with open(os.path.join(h.temp.name, "README.md"), "w", encoding="utf-8") as file: file.write("MirrorService documentation")
            h.indexer.reindex_path(path); h.indexer.wait_until_idle()
            result = h.documentation.analyze(h.temp.name)
            self.assertIn("MirrorService", [item["service"] for item in result["links"]])
            self.assertIn("HiddenService", [item["service"] for item in result["undocumented"]])
        finally: h.close()
