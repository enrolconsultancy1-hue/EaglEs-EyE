import os
import unittest
from test_phase7_helpers import IntelligenceHarness

class ArchitectureAnalysisTests(unittest.TestCase):
    def test_detects_circular_module_dependencies(self):
        h = IntelligenceHarness()
        try:
            for name, content in {"one.py": "import two\n", "two.py": "import one\n"}.items():
                path = os.path.join(h.temp.name, name)
                with open(path, "w", encoding="utf-8") as file: file.write(content)
                h.indexer.reindex_path(path)
            h.indexer.wait_until_idle()
            self.assertTrue(h.architecture.analyze()["circular_dependencies"])
        finally: h.close()

    def test_handles_import_target_with_no_local_dependencies(self):
        h = IntelligenceHarness()
        try:
            for name, content in {"one.py": "import two\n", "two.py": "import os\n"}.items():
                path = os.path.join(h.temp.name, name)
                with open(path, "w", encoding="utf-8") as file: file.write(content)
                h.indexer.reindex_path(path)
            h.indexer.wait_until_idle()
            self.assertEqual(h.architecture.analyze()["circular_dependencies"], [])
        finally: h.close()
