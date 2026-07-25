"""MCP-shaped domain tools without binding the kernel to an MCP server package."""

from services.service import Service


class MCPToolService(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.retrieval = None
        self.context = None
        self.indexer = None
        self.store = None
        self.cross_reference = None
        self.causal = None
        self.evolution = None
        self.decisions = None
        self.cognitive = None

    def start(self):
        super().start()
        self.retrieval = self.kernel.get_service("RetrievalService")
        self.context = self.kernel.get_service("ContextBuilderService")
        self.indexer = self.kernel.get_service("KnowledgeIndexerService")
        self.store = self.kernel.get_service("KnowledgeStoreService")
        self.cross_reference = self.kernel.get_service("CrossReferenceService")
        self.causal = self.kernel.get_service("CausalGraphService")
        self.evolution = self.kernel.get_service("ArchitectureEvolutionService")
        self.decisions = self.kernel.get_service("DecisionTrackingService")
        self.cognitive = self.kernel.get_service("CognitiveLayerService")
        print("[MCP TOOLS] Ready.")

    def list_tools(self):
        return [
            {"name": "search_memory", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "category": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["query"]},
             "description": "Search indexed memory chunks by query text."},
            {"name": "build_context", "inputSchema": {"type": "object", "properties": {"question": {"type": "string"}, "max_chars": {"type": "integer"}}, "required": ["question"]},
             "description": "Build RAG context for a question."},
            {"name": "get_document", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
             "description": "Retrieve a stored document by path."},
            {"name": "get_recent_events", "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer"}}},
             "description": "List recent filesystem events."},
            {"name": "reindex_memory", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
             "description": "Re-index a file path into memory."},
            {"name": "cross_reference", "inputSchema": {"type": "object", "properties": {"subject": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["subject"]},
             "description": "Cross-reference a symbol or subject across the knowledge graph."},
            {"name": "explain_change", "inputSchema": {"type": "object", "properties": {"entity_path": {"type": "string"}, "workspace_id": {"type": "string"}, "session_id": {"type": "string"}}, "required": ["entity_path"]},
             "description": "Produce an evidence-backed explanation for why a file or entity changed."},
            {"name": "get_causal_chain", "inputSchema": {"type": "object", "properties": {"event_id": {"type": "string"}, "direction": {"type": "string", "enum": ["forward", "backward"]}}, "required": ["event_id"]},
             "description": "Trace causal chains forward or backward from an event."},
            {"name": "compare_snapshots", "inputSchema": {"type": "object", "properties": {"snapshot_id_a": {"type": "string"}, "snapshot_id_b": {"type": "string"}}, "required": ["snapshot_id_a", "snapshot_id_b"]},
             "description": "Compare two architecture snapshots and report structural differences."},
            {"name": "list_decisions", "inputSchema": {"type": "object", "properties": {"workspace_id": {"type": "string"}, "session_id": {"type": "string"}}},
             "description": "List engineering decision records, optionally filtered by workspace or session."},
            {"name": "get_decision", "inputSchema": {"type": "object", "properties": {"decision_id": {"type": "string"}}, "required": ["decision_id"]},
             "description": "Retrieve a single engineering decision record by ID."},
        ]

    def call_tool(self, name, arguments):
        arguments = arguments or {}
        if name == "search_memory":
            return {"results": self.retrieval.search(arguments.get("query", ""), arguments.get("category"), arguments.get("limit", 10))}
        if name == "build_context":
            return {"context": self.context.build_rag_context(arguments.get("question", ""), arguments.get("max_chars", 6000))}
        if name == "get_document":
            return {"document": self.store.get_document(arguments.get("path", ""))}
        if name == "get_recent_events":
            return {"events": self.store.recent_events(arguments.get("limit", 10))}
        if name == "reindex_memory":
            path = arguments.get("path")
            if not path:
                return {"error": "path is required"}
            self.indexer.reindex_path(path)
            return {"accepted": True, "path": path}
        if name == "cross_reference":
            if not self.cross_reference:
                return {"error": "cross-reference service is unavailable"}
            return self.cross_reference.find(arguments.get("subject", ""), arguments.get("limit", 20))
        if name == "explain_change":
            if not self.cognitive:
                return {"error": "CognitiveLayerService is unavailable"}
            entity_path = arguments.get("entity_path")
            if not entity_path:
                return {"error": "entity_path is required for explain_change"}
            result = self.cognitive.explain_change(
                entity_path,
                arguments.get("workspace_id"),
                arguments.get("session_id"),
            )
            return {"explanation": result}
        if name == "get_causal_chain":
            if not self.causal:
                return {"error": "CausalGraphService is unavailable"}
            event_id = arguments.get("event_id")
            if not event_id:
                return {"error": "event_id is required for get_causal_chain"}
            chain = self.causal.get_causal_chain(event_id, arguments.get("direction", "forward"))
            return {"causal_chain": [{"id": e.get("id"), "event_type": e.get("event_type"), "path": e.get("path"), "timestamp": e.get("timestamp")} for e in chain]}
        if name == "compare_snapshots":
            if not self.evolution:
                return {"error": "ArchitectureEvolutionService is unavailable"}
            sid_a = arguments.get("snapshot_id_a")
            sid_b = arguments.get("snapshot_id_b")
            if not sid_a or not sid_b:
                return {"error": "snapshot_id_a and snapshot_id_b are required for compare_snapshots"}
            try:
                diff = self.evolution.compare_snapshots(sid_a, sid_b)
            except ValueError as e:
                return {"error": str(e)}
            return {"diff": diff}
        if name == "list_decisions":
            if not self.decisions:
                return {"error": "DecisionTrackingService is unavailable"}
            records = self.decisions.get_decisions(arguments.get("workspace_id"), arguments.get("session_id"))
            return {"decisions": records}
        if name == "get_decision":
            if not self.decisions:
                return {"error": "DecisionTrackingService is unavailable"}
            decision_id = arguments.get("decision_id")
            if not decision_id:
                return {"error": "decision_id is required for get_decision"}
            record = self.decisions.get_decision(decision_id)
            if not record:
                return {"error": "Decision not found: " + str(decision_id)}
            return {"decision": record}
        return {"error": "Unknown tool: " + str(name)}
