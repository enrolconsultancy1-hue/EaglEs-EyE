"""Configurable embedding generation — disabled by default for backward compatibility.

Supports a built-in hash-based embedding (zero external dependencies) for
development/testing, and sentence-transformers for production semantic search.
"""

import hashlib
import json
import math
import struct

from services.service import Service


try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False


HASH_DIMENSION = 128


class EmbeddingService(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self._store = None
        self.provider = "disabled"
        self.model = None
        self.dimension = HASH_DIMENSION
        self._enabled = False

    def start(self):
        super().start()
        config = self.kernel.get_config()
        self.provider = config.get("embeddings", {}).get("provider", "disabled")
        self._enabled = self.provider != "disabled"
        if not self._enabled:
            print("[EMBEDDING] Disabled by configuration.")
            return
        self._store = self.kernel.get_service("KnowledgeStoreService")
        if not self._store:
            raise RuntimeError("EmbeddingService requires KnowledgeStoreService.")
        model_cfg = config.get("embeddings", {}).get("model", "")
        if self.provider == "sentence_transformers":
            self._load_sentence_transformer(model_cfg or "all-MiniLM-L6-v2")
        elif self.provider == "simple":
            self.dimension = HASH_DIMENSION
            print("[EMBEDDING] Simple hash provider ready (dim=%d)." % self.dimension)
        else:
            print("[EMBEDDING] Unknown provider '%s', disabling." % self.provider)
            self._enabled = False

    def _load_sentence_transformer(self, model_name):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            print("[EMBEDDING] sentence-transformers model '%s' ready (dim=%d)." % (model_name, self.dimension))
        except ImportError:
            print("[EMBEDDING] sentence-transformers not installed, falling back to simple.")
            self.provider = "simple"
            self.dimension = HASH_DIMENSION

    @property
    def enabled(self):
        return self._enabled

    def generate(self, text):
        if not self._enabled:
            return None
        if not text or not text.strip():
            return [0.0] * self.dimension
        if self.provider == "sentence_transformers" and self.model:
            vec = self.model.encode(text, normalize_embeddings=True)
            return vec.tolist() if HAS_NUMPY else list(vec)
        return self._hash_embed(text)

    def persist(self, table, row_id, embedding_vector):
        if not self._enabled:
            return
        if not embedding_vector:
            return
        blob = self._vector_to_blob(embedding_vector)
        with self._store.transaction() as connection:
            self._store._ensure_column(connection, table, "embedding", "BLOB")
            connection.execute(
                "UPDATE %s SET embedding = ? WHERE id = ?" % table,
                (blob, row_id),
            )

    def load(self, table, row_id):
        if not self._enabled:
            return None
        with self._store.transaction() as connection:
            self._store._ensure_column(connection, table, "embedding", "BLOB")
            row = connection.execute(
                "SELECT embedding FROM %s WHERE id = ?" % table, (row_id,)
            ).fetchone()
        if row and row["embedding"]:
            return self._blob_to_vector(row["embedding"])
        return None

    def load_all(self, table, where_clause="1=1", params=None):
        if not self._enabled:
            return []
        params = params or []
        with self._store.transaction() as connection:
            self._store._ensure_column(connection, table, "embedding", "BLOB")
            rows = connection.execute(
                "SELECT id, embedding FROM %s WHERE %s AND embedding IS NOT NULL" % (table, where_clause),
                params,
            ).fetchall()
        results = []
        for row in rows:
            vec = self._blob_to_vector(row["embedding"])
            if vec:
                results.append({"id": row["id"], "vector": vec})
        return results

    @staticmethod
    def _hash_embed(text):
        vec = [0.0] * HASH_DIMENSION
        for i, token in enumerate(_tokenize(text)):
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % HASH_DIMENSION
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    @staticmethod
    def _vector_to_blob(vec):
        return struct.pack("!%sf" % len(vec), *vec)

    @staticmethod
    def _blob_to_vector(blob):
        count = len(blob) // 4
        return list(struct.unpack("!%sf" % count, blob))


def _tokenize(text):
    result = []
    current = ""
    for ch in text.lower():
        if ch.isalnum() or ch in {"_", "."}:
            current += ch
        else:
            if current:
                result.append(current)
                if len(current) > 1:
                    for j in range(1, len(current)):
                        result.append(current[j:])
            current = ""
    if current:
        result.append(current)
    return result
