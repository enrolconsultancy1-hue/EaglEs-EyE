import os
import unittest
from test_phase7_helpers import IntelligenceHarness

class DependencyGraphTests(unittest.TestCase):
    def test_import_inheritance_calls_and_registration_are_edges(self):
        h = IntelligenceHarness()
        try:
            path = os.path.join(h.temp.name, "app.py")
            with open(path, "w", encoding="utf-8") as file: file.write("import json\nclass App(Base):\n def go(self, kernel):\n  kernel.register_service(App(kernel))\n  return helper()\ndef helper(): pass\n")
            h.indexer.reindex_path(path); h.indexer.wait_until_idle()
            kinds = {item["relation"] for item in h.graph.related(path)}
            self.assertTrue({"imports", "inherits", "calls", "registers_service"}.issubset(kinds))
        finally: h.close()
