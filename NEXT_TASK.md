# Next Task

Phase 15 is complete and released as `phase15-release` / `v2.3.0`.

The evidence pipeline now runs from connector observe/collect/normalize/emit
through EvidenceBus → EvidenceIngestionService → KnowledgeStore → KnowledgeGraph.

All observation flows through the connector framework. The three pre-connector
observer services are deprecated but still functional.

Phase 16 candidates (pending authorization):

- Connector authentication support (OAuth, API keys, tokens)
- Network connector implementations (GitHub API, MCP client, HTTP API)
- GUI connector management panel
- Connector testing framework
- Performance optimization for large-scale observation
- Connector persistence (stateful reconnection)
- Cross-workspace evidence merging in KnowledgeGraph
- Connector event replay / recovery
