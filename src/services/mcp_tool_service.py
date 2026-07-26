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
        self.vector_search = None
        self.awareness = None
        self.connector = None

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
        self.vector_search = self.kernel.get_service("VectorSearchService")
        self.awareness = self.kernel.get_service("SemanticAwarenessService")
        self.connector = self.kernel.get_service("ConnectorService")
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
            {"name": "search_semantic", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "table": {"type": "string", "enum": ["chunks", "symbols", "events", "decision_records"]}, "top_k": {"type": "integer"}}, "required": ["query"]},
             "description": "Semantic vector search across embedded entities."},
            {"name": "get_similar", "inputSchema": {"type": "object", "properties": {"row_id": {"type": "integer"}, "table": {"type": "string", "enum": ["chunks", "symbols", "events", "decision_records"]}, "top_k": {"type": "integer"}}, "required": ["row_id", "table"]},
             "description": "Find semantically similar items to a given entity by ID."},
            {"name": "get_awareness_signals", "inputSchema": {"type": "object", "properties": {"signal_type": {"type": "string"}, "limit": {"type": "integer"}}},
             "description": "List recent semantic awareness signals."},
            {"name": "list_connectors", "inputSchema": {"type": "object", "properties": {}},
             "description": "List all registered connectors and their status."},
            {"name": "get_connector_status", "inputSchema": {"type": "object", "properties": {"connector_id": {"type": "string"}}, "required": ["connector_id"]},
             "description": "Get detailed status for a specific connector."},
            {"name": "get_connector_health_all", "inputSchema": {"type": "object", "properties": {}},
             "description": "Get health status for all registered connectors."},
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
        if name == "search_semantic":
            if not self.vector_search or not self.vector_search.enabled:
                return {"error": "Vector search is unavailable (embeddings disabled)"}
            query = arguments.get("query", "")
            if not query:
                return {"error": "query is required for search_semantic"}
            table = arguments.get("table", "chunks")
            top_k = int(arguments.get("top_k", 10))
            if table == "all":
                results = self.vector_search.search_cross_entity(query, top_k)
            else:
                results = self.vector_search.search(query, table, top_k)
            return {"results": results}
        if name == "get_similar":
            if not self.vector_search or not self.vector_search.enabled:
                return {"error": "Vector search is unavailable (embeddings disabled)"}
            row_id = arguments.get("row_id")
            table = arguments.get("table", "chunks")
            top_k = int(arguments.get("top_k", 5))
            results = self.vector_search.find_similar(row_id, table, top_k)
            return {"results": results}
        if name == "get_awareness_signals":
            if not self.awareness:
                return {"error": "SemanticAwarenessService is unavailable"}
            signal_type = arguments.get("signal_type")
            limit = int(arguments.get("limit", 20))
            signals = self.awareness.get_signals(signal_type, limit)
            return {"signals": signals}
        if name == "list_connectors":
            if not self.connector or not self.connector.get_manager():
                return {"error": "ConnectorService is unavailable"}
            manager = self.connector.get_manager()
            connectors = []
            for cid in manager.list_ids():
                try:
                    status = manager.connector_status(cid)
                    connectors.append(status)
                except Exception:
                    connectors.append({"id": cid, "state": "error"})
            return {"connectors": connectors}
        if name == "get_connector_status":
            if not self.connector or not self.connector.get_manager():
                return {"error": "ConnectorService is unavailable"}
            connector_id = arguments.get("connector_id", "")
            if not connector_id:
                return {"error": "connector_id is required"}
            try:
                status = self.connector.get_manager().connector_status(connector_id)
                return {"status": status}
            except Exception as e:
                return {"error": str(e)}
        if name == "get_connector_health_all":
            if not self.connector or not self.connector.get_manager():
                return {"error": "ConnectorService is unavailable"}
            health = self.connector.get_manager().check_health_all()
            return {"health": health}
        return {"error": "Unknown tool: " + str(name)}
