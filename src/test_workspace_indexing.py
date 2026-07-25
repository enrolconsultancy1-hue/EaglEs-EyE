import os
import unittest

from test_phase7_helpers import IntelligenceHarness


class WorkspaceIndexingTests(unittest.TestCase):
    def test_workspace_pass_is_deterministic_and_excludes_runtime_directories(self):
        harness = IntelligenceHarness()
        try:
            source = os.path.join(harness.temp.name, "src")
            ignored = os.path.join(harness.temp.name, ".venv")
            os.makedirs(source)
            os.makedirs(ignored)
            with open(os.path.join(source, "observer.py"), "w", encoding="utf-8") as file:
                file.write("class ObserverService: pass\n")
            with open(os.path.join(harness.temp.name, "README.md"), "w", encoding="utf-8") as file:
                file.write("Evidence-backed workspace.\n")
            with open(os.path.join(ignored, "ignored.py"), "w", encoding="utf-8") as file:
                file.write("class IgnoredService: pass\n")

            result = harness.indexer.reindex_workspace(harness.temp.name)
            harness.indexer.wait_until_idle()

            self.assertEqual(result["queued_files"], 2)
            self.assertEqual(harness.store.statistics()["documents"], 2)
            self.assertEqual([item["name"] for item in harness.store.find_symbols("ObserverService")], ["ObserverService"])
            self.assertEqual(harness.store.find_symbols("IgnoredService"), [])
        finally:
            harness.close()
