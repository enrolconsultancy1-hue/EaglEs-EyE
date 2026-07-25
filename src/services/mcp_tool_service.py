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

    def start(self):
        super().start()
        self.retrieval = self.kernel.get_service("RetrievalService")
        self.context = self.kernel.get_service("ContextBuilderService")
        self.indexer = self.kernel.get_service("KnowledgeIndexerService")
        self.store = self.kernel.get_service("KnowledgeStoreService")
        self.cross_reference = self.kernel.get_service("CrossReferenceService")
        print("[MCP TOOLS] Ready.")

    def list_tools(self):
        return [
            {"name": "search_memory", "inputSchema": {"type": "object", "required": ["query"]}},
            {"name": "build_context", "inputSchema": {"type": "object", "required": ["question"]}},
            {"name": "get_document", "inputSchema": {"type": "object", "required": ["path"]}},
            {"name": "get_recent_events", "inputSchema": {"type": "object"}},
            {"name": "reindex_memory", "inputSchema": {"type": "object", "required": ["path"]}},
            {"name": "cross_reference", "inputSchema": {"type": "object", "required": ["subject"]}},
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
        return {"error": "Unknown tool: " + str(name)}
