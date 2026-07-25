from services.service import Service


class CrossReferenceService(Service):
    """Project-level question API built on static graph facts and retrieval."""

    def __init__(self, kernel):
        super().__init__(kernel)
        self.graph = None
        self.retrieval = None
        self.store = None

    def start(self):
        super().start()
        self.graph = self.kernel.get_service("KnowledgeGraphService")
        self.retrieval = self.kernel.get_service("RetrievalService")
        self.store = self.kernel.get_service("KnowledgeStoreService")
        if not all((self.graph, self.retrieval, self.store)):
            raise RuntimeError("CrossReferenceService requires graph, retrieval, and store services.")
        print("[CROSS REFERENCE] Ready.")

    def find(self, subject, limit=20):
        graph = self.graph.where_used(subject)
        lexical = self.retrieval.search(subject, limit=limit)
        return {"subject": subject, "definitions": graph["symbols"], "relationships": graph["relationships"], "documents": lexical}

    def event_subscribers(self, event_name):
        with self.store.transaction() as connection:
            return [dict(row) for row in connection.execute(
                """SELECT documents.path, relationships.metadata FROM relationships
                JOIN documents ON documents.id = relationships.source_document_id
                WHERE relationships.relation = 'subscribes_to' AND relationships.target_path = ?""",
                ("event:" + event_name,),
            )]
