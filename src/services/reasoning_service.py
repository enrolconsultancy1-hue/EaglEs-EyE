from services.service import Service


class ReasoningService(Service):
    """Read-only reasoning foundation; it proposes but never executes actions."""

    def __init__(self, kernel):
        super().__init__(kernel)
        self.retrieval = None
        self.context_builder = None
        self.store = None

    def start(self):
        super().start()
        self.retrieval = self.kernel.get_service("RetrievalService")
        self.context_builder = self.kernel.get_service("ContextBuilderService")
        self.store = self.kernel.get_service("KnowledgeStoreService")
        if not all((self.retrieval, self.context_builder, self.store)):
            raise RuntimeError("ReasoningService requires retrieval, context, and store services.")
        print("[REASONING] Ready (read-only).")

    def reason(self, goal, limit=8, max_chars=5000):
        results = self.retrieval.search(goal, limit=limit)
        context = self.context_builder.build_rag_context(goal, max_chars=max_chars, limit=limit)
        proposal = {
            "goal": goal,
            "evidence_count": len(results),
            "citations": [item["citation"] for item in results],
            "context": context,
            "proposed_action": "Review the cited context and choose an explicit action.",
            "execution_allowed": False,
        }
        self.store.record_reflection("Reasoning context prepared for: " + goal, proposal)
        return proposal
