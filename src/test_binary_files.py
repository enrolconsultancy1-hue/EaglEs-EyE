import os
import unittest

from test_phase7_helpers import IntelligenceHarness


class BinaryFileTests(unittest.TestCase):
    def setUp(self): self.harness = IntelligenceHarness()
    def tearDown(self): self.harness.close()

    def test_binary_invalid_utf8_and_oversized_files_are_safe(self):
        cases = {"blob.bin": b"\x00\xff\x80", "invalid.txt": b"\xff\xfe", "large.txt": b"x" * (1024 * 1024 + 1)}
        for name, content in cases.items():
            path = os.path.join(self.harness.temp.name, name)
            with open(path, "wb") as file: file.write(content)
            self.harness.indexer.reindex_path(path)
        self.harness.indexer.wait_until_idle()
        self.assertEqual(self.harness.store.statistics()["documents"], 3)
        self.assertEqual(self.harness.retrieval.search("x"), [])
