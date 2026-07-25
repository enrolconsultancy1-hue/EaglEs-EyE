"""Phase 13 Semantic Intelligence tests — embeddings, vector search, awareness, MCP tools, GUI."""

import json
import math
import os
import sqlite3
import sys
import tempfile
import threading
import unittest

from services.embedding_service import EmbeddingService, _tokenize, HASH_DIMENSION
from services.vector_search_service import VectorSearchService, _cosine_similarity
from services.semantic_awareness_service import SemanticAwarenessService


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

class Phase13EmbeddingTests(unittest.TestCase):
    def test_hash_embedding_dimension(self):
        vec = EmbeddingService._hash_embed("hello world")
        self.assertEqual(len(vec), HASH_DIMENSION)

    def test_hash_embedding_normalized(self):
        vec = EmbeddingService._hash_embed("test string for normalization")
        norm = math.sqrt(sum(v * v for v in vec))
        self.assertAlmostEqual(norm, 1.0, places=5)

    def test_hash_embedding_deterministic(self):
        a = EmbeddingService._hash_embed("the same text")
        b = EmbeddingService._hash_embed("the same text")
        self.assertEqual(a, b)

    def test_hash_embedding_different_inputs(self):
        a = EmbeddingService._hash_embed("totally different content")
        b = EmbeddingService._hash_embed("something else entirely")
        self.assertNotEqual(a, b)

    def test_empty_text_returns_zero(self):
        vec = EmbeddingService._hash_embed("")
        self.assertEqual(len(vec), HASH_DIMENSION)
        self.assertTrue(all(v == 0.0 for v in vec))

    def test_whitespace_text_returns_zero(self):
        vec = EmbeddingService._hash_embed("   \n  \t  ")
        self.assertEqual(len(vec), HASH_DIMENSION)
        self.assertTrue(all(v == 0.0 for v in vec))

    def test_tokenize_basic(self):
        tokens = _tokenize("hello world foo")
        self.assertIn("hello", tokens)
        self.assertIn("world", tokens)
        self.assertIn("foo", tokens)

    def test_tokenize_with_punctuation(self):
        tokens = _tokenize("hello.world foo_bar")
        self.assertIn("hello.world", tokens)
        self.assertIn("foo_bar", tokens)

    def test_vector_blob_roundtrip(self):
        original = [0.1, 0.2, 0.3, 0.4, 0.5]
        blob = EmbeddingService._vector_to_blob(original)
        restored = EmbeddingService._blob_to_vector(blob)
        for a, b in zip(original, restored):
            self.assertAlmostEqual(a, b, places=5)

    def test_embedding_disabled_by_default(self):
        kernel = DummyKernel({})
        svc = EmbeddingService(kernel)
        svc.start()
        self.assertFalse(svc.enabled)
        svc.stop()

    def test_embedding_enabled_with_simple_provider(self):
        from services.knowledge_store_service import KnowledgeStoreService
        kernel = DummyKernel({"embeddings": {"provider": "simple"}})
        store = KnowledgeStoreService(kernel)
        kernel.register_service(store)
        store.start = lambda: None
        svc = EmbeddingService(kernel)
        svc.start()
        self.assertTrue(svc.enabled)
        gen = svc.generate("test")
        self.assertIsNotNone(gen)
        self.assertEqual(len(gen), HASH_DIMENSION)
        svc.stop()


# ---------------------------------------------------------------------------
# Vector search
# ---------------------------------------------------------------------------

class Phase13VectorSearchTests(unittest.TestCase):
    def test_cosine_similarity_identical(self):
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        self.assertAlmostEqual(_cosine_similarity(a, b), 1.0)

    def test_cosine_similarity_orthogonal(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        self.assertAlmostEqual(_cosine_similarity(a, b), 0.0)

    def test_cosine_similarity_empty(self):
        self.assertEqual(_cosine_similarity([], []), 0.0)

    def test_cosine_similarity_different_lengths(self):
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0]
        self.assertGreater(_cosine_similarity(a, b), 0.0)

    def test_search_disabled_when_embedding_off(self):
        kernel = DummyKernel({})
        vs = VectorSearchService(kernel)
        vs.start()
        self.assertFalse(vs.enabled)
        results = vs.search("test query")
        self.assertEqual(results, [])
        vs.stop()


# ---------------------------------------------------------------------------
# Semantic awareness
# ---------------------------------------------------------------------------

class Phase13AwarenessTests(unittest.TestCase):
    def test_module_from_path_src(self):
        module = SemanticAwarenessService._module_from_path("/project/src/services/foo.py")
        self.assertEqual(module, "src/services/foo.py")

    def test_module_from_path_no_src(self):
        module = SemanticAwarenessService._module_from_path("/project/tests/test_foo.py")
        self.assertIsNone(module)

    def test_module_from_path_windows(self):
        module = SemanticAwarenessService._module_from_path("C:\\project\\src\\services\\foo.py")
        self.assertEqual(module, "src/services/foo.py")


# ---------------------------------------------------------------------------
# MCP semantic tools
# ---------------------------------------------------------------------------

class Phase13MCPToolTests(unittest.TestCase):
    def test_search_semantic_tool_in_list(self):
        from services.mcp_tool_service import MCPToolService
        kernel = DummyKernel({})
        svc = MCPToolService(kernel)
        svc.start()
        tools = svc.list_tools()
        names = [t["name"] for t in tools]
        self.assertIn("search_semantic", names)
        self.assertIn("get_similar", names)
        self.assertIn("get_awareness_signals", names)
        svc.stop()

    def test_search_semantic_returns_error_when_disabled(self):
        from services.mcp_tool_service import MCPToolService
        kernel = DummyKernel({})
        svc = MCPToolService(kernel)
        svc.start()
        result = svc.call_tool("search_semantic", {"query": "test"})
        self.assertIn("error", result)
        svc.stop()

    def test_get_similar_returns_error_when_disabled(self):
        from services.mcp_tool_service import MCPToolService
        kernel = DummyKernel({})
        svc = MCPToolService(kernel)
        svc.start()
        result = svc.call_tool("get_similar", {"row_id": 1, "table": "chunks"})
        self.assertIn("error", result)
        svc.stop()

    def test_get_awareness_signals_list(self):
        from services.mcp_tool_service import MCPToolService
        from services.knowledge_store_service import KnowledgeStoreService
        from services.semantic_awareness_service import SemanticAwarenessService
        kernel = DummyKernel({})
        store = KnowledgeStoreService(kernel)
        kernel.register_service(store)
        tmp = tempfile.mkdtemp()
        store.database_path = os.path.join(tmp, "test.db")
        store.connection = sqlite3.connect(store.database_path)
        store.connection.row_factory = sqlite3.Row
        store.connection.execute("PRAGMA journal_mode=WAL")
        store.connection.execute("PRAGMA synchronous=NORMAL")
        store.connection.execute("PRAGMA foreign_keys=ON")
        store.connection.execute("PRAGMA busy_timeout=5000")
        store._create_schema()
        awareness = SemanticAwarenessService(kernel)
        kernel.register_service(awareness)
        awareness.store = store
        awareness._enabled = True
        svc = MCPToolService(kernel)
        svc.start()
        result = svc.call_tool("get_awareness_signals", {})
        self.assertIn("signals", result)
        svc.stop()
        store.connection.close()

    def test_existing_tools_preserved(self):
        from services.mcp_tool_service import MCPToolService
        kernel = DummyKernel({})
        svc = MCPToolService(kernel)
        svc.start()
        tools = svc.list_tools()
        names = [t["name"] for t in tools]
        for tool in ("search_memory", "build_context", "get_document", "get_recent_events",
                     "reindex_memory", "cross_reference", "explain_change", "get_causal_chain",
                     "compare_snapshots", "list_decisions", "get_decision"):
            self.assertIn(tool, names, "Existing tool %s should be preserved" % tool)
        svc.stop()


# ---------------------------------------------------------------------------
# GUI template presence
# ---------------------------------------------------------------------------

class Phase13GUITemplateTests(unittest.TestCase):
    def test_search_semantic_template_exists(self):
        template_dir = os.path.join(os.path.dirname(__file__), "..", "gui", "templates")
        self.assertTrue(os.path.isfile(os.path.join(template_dir, "search_semantic.html")))

    def test_awareness_template_exists(self):
        template_dir = os.path.join(os.path.dirname(__file__), "..", "gui", "templates")
        self.assertTrue(os.path.isfile(os.path.join(template_dir, "awareness.html")))

    def test_search_semantic_template_has_api_call(self):
        template_path = os.path.join(os.path.dirname(__file__), "..", "gui", "templates", "search_semantic.html")
        with open(template_path) as f:
            content = f.read()
        self.assertIn("search_semantic", content)
        self.assertIn("get_similar", content)
        self.assertIn("/api/call", content)

    def test_awareness_template_has_api_call(self):
        template_path = os.path.join(os.path.dirname(__file__), "..", "gui", "templates", "awareness.html")
        with open(template_path) as f:
            content = f.read()
        self.assertIn("get_awareness_signals", content)
        self.assertIn("/api/call", content)


# ---------------------------------------------------------------------------
# DummyKernel helper for service-level tests
# ---------------------------------------------------------------------------

class DummyEventBus:
    def __init__(self):
        self.subscriptions = []

    def subscribe(self, event_name, callback):
        self.subscriptions.append((event_name, callback))


class DummyKernel:
    def __init__(self, config=None):
        self.config = config or {}
        self.services = {}
        self.event_bus = DummyEventBus()

    def register_service(self, service):
        self.services[service.name] = service

    def get_service(self, name):
        return self.services.get(name)

    def get_config(self):
        return self.config

    def set_config(self, config):
        self.config = config


if __name__ == "__main__":
    unittest.main()
