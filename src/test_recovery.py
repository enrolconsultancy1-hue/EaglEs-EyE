import os
import unittest

from test_phase7_helpers import IntelligenceHarness


class RestartPersistenceTests(unittest.TestCase):
    def test_restart_preserves_document_and_chunk_identity(self):
        harness = IntelligenceHarness()
        try:
            path = os.path.join(harness.temp.name, "stable.md")
            with open(path, "w", encoding="utf-8") as file: file.write("stable retrieval fact")
            harness.indexer.reindex_path(path); harness.indexer.wait_until_idle()
            before = harness.store.get_document(path)
            database = harness.store.database_path
            harness.store.stop()
            # Reopen the same database with a fresh service lifecycle.
            from core.kernel import EyeKernel
            from services.knowledge_store_service import KnowledgeStoreService
            kernel = EyeKernel(); kernel.set_config({"memory_path": os.path.dirname(database)})
            store = KnowledgeStoreService(kernel); kernel.register_service(store); store.start()
            after = store.get_document(path)
            self.assertEqual(before["id"], after["id"])
            self.assertEqual(before["chunks"][0]["id"], after["chunks"][0]["id"])
            store.stop()
        finally:
            harness.close()
