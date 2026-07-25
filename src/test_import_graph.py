import os
import unittest

from test_phase7_helpers import IntelligenceHarness


class ImportGraphTests(unittest.TestCase):
    def setUp(self): self.harness = IntelligenceHarness()
    def tearDown(self): self.harness.close()

    def test_symbols_dependencies_and_event_subscriptions_are_discovered(self):
        path = os.path.join(self.harness.temp.name, "service.py")
        with open(path, "w", encoding="utf-8") as file:
            file.write("from dataclasses import dataclass\nfrom enum import Enum\n@dataclass\nclass Worker(Base):\n    VALUE = 1\n    def run(self, bus):\n        bus.subscribe('FILE_MODIFIED', self.run)\n        return helper()\ndef helper(): return 1\n")
        self.harness.indexer.reindex_path(path)
        self.harness.indexer.wait_until_idle()
        symbols = self.harness.store.find_symbols("Worker")
        self.assertEqual(symbols[0]["kind"], "dataclass")
        related = self.harness.graph.related(os.path.abspath(path))
        self.assertIn("imports", [item["relation"] for item in related])
        self.assertEqual(len(self.harness.cross_reference.event_subscribers("FILE_MODIFIED")), 1)
