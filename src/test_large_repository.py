import os
import time
import unittest

from test_phase7_helpers import IntelligenceHarness


class LargeRepositoryTests(unittest.TestCase):
    def test_generated_repository_indexes_with_measurable_throughput(self):
        harness = IntelligenceHarness()
        try:
            started = time.perf_counter()
            for number in range(500):
                path = os.path.join(harness.temp.name, "module_%04d.py" % number)
                with open(path, "w", encoding="utf-8") as file: file.write("def function_%d(): return 'repository benchmark'\n" % number)
                harness.indexer.reindex_path(path)
            harness.indexer.wait_until_idle()
            elapsed = time.perf_counter() - started
            statistics = harness.store.statistics()
            self.assertEqual(statistics["documents"], 500)
            self.assertGreater(statistics["symbols"], 499)
            self.assertLess(elapsed, 30, "500-file indexing should remain practical in CI")
        finally:
            harness.close()
