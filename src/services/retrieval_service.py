import json
import os
from datetime import datetime, timezone

from services.service import Service


class RetrievalService(Service):
    """Stable lexical retrieval API; vector providers can augment score later."""

    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        if not self.store:
            raise RuntimeError("RetrievalService requires KnowledgeStoreService.")
        print("[RETRIEVAL] Ready.")

    def search(self, query, category=None, limit=10):
        terms = [term for term in query.lower().split() if term]
        if not terms:
            return []
        results = []
        for chunk in self.store.active_chunks():
            metadata = json.loads(chunk["metadata"] or "{}")
            if category and metadata.get("category") != category:
                continue
            score = self._score(terms, chunk, metadata)
            if score <= 0:
                continue
            results.append({
                "score": round(score, 4), "document_id": chunk["document_id"],
                "chunk_id": chunk["id"], "path": chunk["path"],
                "filename": os.path.basename(chunk["path"]), "offset": chunk["offset"],
                "content": chunk["text"], "citation": "%s:%s" % (os.path.basename(chunk["path"]), chunk["offset"]),
                "metadata": metadata,
            })
        results.sort(key=lambda item: (-item["score"], item["path"], item["offset"]))
        results = results[:max(1, int(limit))]
        with self.store.transaction() as connection:
            connection.execute(
                "INSERT INTO retrieval_logs(query, filters, result_count, created_at) VALUES (?, ?, ?, ?)",
                (query, json.dumps({"category": category}), len(results), datetime.now(timezone.utc).isoformat()),
            )
        return results

    def project_search(self, query, limit=10):
        """Augment lexical evidence with known project symbols and graph facts."""
        symbols = self.store.find_symbols(query, limit=limit)
        with self.store.transaction() as connection:
            relationships = [dict(row) for row in connection.execute(
                "SELECT documents.path, relationships.target_path, relationships.relation FROM relationships JOIN documents ON documents.id = relationships.source_document_id WHERE relationships.target_path LIKE ? LIMIT ?",
                ("%" + query + "%", limit),
            )]
        return {"query": query, "chunks": self.search(query, limit=limit), "symbols": symbols, "relationships": relationships, "recent_events": self.store.recent_events(limit)}

    @staticmethod
    def _score(terms, chunk, metadata):
        text = chunk["text"].lower()
        filename = os.path.basename(chunk["path"]).lower()
        directory = os.path.dirname(chunk["path"]).lower()
        metadata_text = json.dumps(metadata, ensure_ascii=False).lower()
        score = 0.0
        for term in terms:
            score += text.count(term) * 1.0
            score += filename.count(term) * 4.0
            score += directory.count(term) * 1.5
            score += metadata_text.count(term) * 0.5
        # Recency refines a matching result; it must never create one.
        if score <= 0:
            return 0.0
        try:
            age_days = (datetime.now(timezone.utc) - datetime.fromisoformat(chunk["updated_at"])).days
            score += max(0, 1 - age_days / 365) * 0.25
        except ValueError:
            pass
        return score
