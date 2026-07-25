import os
import tempfile
import unittest

from core.kernel import EyeKernel
from services.context_builder_service import ContextBuilderService
from services.knowledge_indexer_service import KnowledgeIndexerService
from services.knowledge_store_service import KnowledgeStoreService
from services.mcp_tool_service import MCPToolService
from services.reasoning_service import ReasoningService
from services.retrieval_service import RetrievalService


class SemanticIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.kernel = EyeKernel()
        self.kernel.set_config({"memory_path": self.directory.name, "chunk_size": 80, "chunk_overlap": 10})
        self.store = KnowledgeStoreService(self.kernel)
        self.indexer = KnowledgeIndexerService(self.kernel)
        self.retrieval = RetrievalService(self.kernel)
        self.context = ContextBuilderService(self.kernel)
        self.reasoning = ReasoningService(self.kernel)
        self.tools = MCPToolService(self.kernel)
        for service in (self.store, self.indexer, self.retrieval, self.context, self.reasoning, self.tools):
            self.kernel.register_service(service)
        for service in (self.store, self.indexer, self.retrieval, self.context, self.reasoning, self.tools):
            service.start()

    def tearDown(self):
        for service in (self.tools, self.reasoning, self.context, self.retrieval, self.indexer, self.store):
            service.stop()
        self.directory.cleanup()

    def test_versioned_index_search_context_and_tools(self):
        path = os.path.join(self.directory.name, "architecture.md")
        with open(path, "w", encoding="utf-8") as destination:
            destination.write("MirrorService uses ConfigService. Semantic memory supports retrieval.\n")
        self.indexer.reindex_path(path)
        self.indexer.wait_until_idle()

        first = self.store.get_document(os.path.abspath(path))
        self.assertEqual(first["version"], 1)
        self.assertEqual(len(self.retrieval.search("semantic retrieval")), 1)
        context = self.context.build_rag_context("MirrorService")
        self.assertIn("Citation: architecture.md:0", context)

        with open(path, "w", encoding="utf-8") as destination:
            destination.write("MirrorService uses lifecycle-safe configuration.\n")
        self.indexer.reindex_path(path)
        self.indexer.wait_until_idle()
        second = self.store.get_document(os.path.abspath(path))
        self.assertEqual(second["version"], 2)
        self.assertEqual(len(self.retrieval.search("semantic retrieval")), 0)

        tool_result = self.tools.call_tool("search_memory", {"query": "lifecycle"})
        self.assertEqual(tool_result["results"][0]["filename"], "architecture.md")
        proposal = self.reasoning.reason("MirrorService lifecycle")
        self.assertFalse(proposal["execution_allowed"])

    def test_deleted_file_is_retained_as_history_not_retrieval(self):
        path = os.path.join(self.directory.name, "remove.txt")
        with open(path, "w", encoding="utf-8") as destination:
            destination.write("temporary semantic knowledge")
        self.indexer.reindex_path(path)
        self.indexer.wait_until_idle()
        os.remove(path)
        self.indexer.enqueue({"path": path, "event_type": "FILE_DELETED"})
        self.indexer.wait_until_idle()
        document = self.store.get_document(os.path.abspath(path))
        self.assertEqual(document["status"], "deleted")
        self.assertEqual(self.retrieval.search("temporary"), [])


if __name__ == "__main__":
    unittest.main()
