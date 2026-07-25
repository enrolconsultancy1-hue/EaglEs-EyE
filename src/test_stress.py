import os
import unittest

from test_phase7_helpers import IntelligenceHarness


class StressTests(unittest.TestCase):
    def test_hundreds_of_create_modify_delete_operations_remain_consistent(self):
        harness = IntelligenceHarness()
        try:
            paths = []
            for number in range(250):
                path = os.path.join(harness.temp.name, "item_%03d.txt" % number)
                with open(path, "w", encoding="utf-8") as file: file.write("initial %d" % number)
                paths.append(path)
                harness.indexer.reindex_path(path)
            harness.indexer.wait_until_idle()
            for path in paths[::2]:
                with open(path, "w", encoding="utf-8") as file: file.write("updated reliability content")
                harness.indexer.reindex_path(path)
            for path in paths[::5]:
                os.remove(path)
                harness.indexer.enqueue({"path": path, "event_type": "FILE_DELETED"})
            harness.indexer.wait_until_idle()
            self.assertEqual(harness.store.statistics()["documents"], 200)
            self.assertEqual(len(harness.retrieval.search("reliability")), 10)
            self.assertEqual(harness.store.integrity_check(), "ok")
        finally:
            harness.close()
