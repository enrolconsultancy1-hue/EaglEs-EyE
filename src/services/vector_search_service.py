"""Vector similarity search across embedded entities.

Performs cosine-similarity search on embeddings stored by EmbeddingService.
Preserves lexical RetrievalService — this is an additive capability.
"""

import math

from services.service import Service


class VectorSearchService(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.embedding = None
        self.store = None

    def start(self):
        super().start()
        self.embedding = self.kernel.get_service("EmbeddingService")
        self.store = self.kernel.get_service("KnowledgeStoreService")
        if not self.embedding or not self.embedding.enabled:
            print("[VECTOR SEARCH] EmbeddingService disabled, vector search unavailable.")
            return
        if not self.store:
            raise RuntimeError("VectorSearchService requires KnowledgeStoreService.")
        print("[VECTOR SEARCH] Ready.")

    @property
    def enabled(self):
        return self.embedding is not None and self.embedding.enabled

    def search(self, query, table="chunks", top_k=10):
        if not self.enabled:
            return []
        query_vec = self.embedding.generate(query)
        if not query_vec:
            return []
        candidates = self.embedding.load_all(table)
        scored = []
        for c in candidates:
            sim = _cosine_similarity(query_vec, c["vector"])
            scored.append((sim, c["id"]))
        scored.sort(key=lambda x: -x[0])
        scored = scored[:max(1, top_k)]
        results = []
        with self.store.transaction() as connection:
            for sim, row_id in scored:
                row = connection.execute(
                    "SELECT * FROM %s WHERE id = ?" % table, (row_id,)
                ).fetchone()
                if row:
                    r = dict(row)
                    r["similarity"] = round(sim, 4)
                    r["table"] = table
                    results.append(r)
        return results

    def find_similar(self, row_id, table="chunks", top_k=5):
        if not self.enabled:
            return []
        query_vec = self.embedding.load(table, row_id)
        if not query_vec:
            return []
        candidates = self.embedding.load_all(
            table, where_clause="id != ?", params=[row_id]
        )
        scored = []
        for c in candidates:
            sim = _cosine_similarity(query_vec, c["vector"])
            scored.append((sim, c["id"]))
        scored.sort(key=lambda x: -x[0])
        scored = scored[:max(1, top_k)]
        results = []
        with self.store.transaction() as connection:
            for sim, cid in scored:
                row = connection.execute(
                    "SELECT * FROM %s WHERE id = ?" % table, (cid,)
                ).fetchone()
                if row:
                    r = dict(row)
                    r["similarity"] = round(sim, 4)
                    r["table"] = table
                    results.append(r)
        return results

    def search_cross_entity(self, query, top_k=5):
        if not self.enabled:
            return {}
        return {
            "chunks": self.search(query, "chunks", top_k),
            "symbols": self.search(query, "symbols", top_k),
            "events": self.search(query, "events", top_k),
            "decisions": self.search(query, "decision_records", top_k),
        }


def _cosine_similarity(a, b):
    dot = 0.0
    na = 0.0
    nb = 0.0
    for i in range(min(len(a), len(b))):
        dot += a[i] * b[i]
        na += a[i] * a[i]
        nb += b[i] * b[i]
    denom = math.sqrt(na) * math.sqrt(nb)
    return dot / denom if denom > 0 else 0.0
