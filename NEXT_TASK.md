# Next Task

Phase 14 is complete and released as `phase14-release` / `v2.2.0`.

The Connector Framework is now the only approved mechanism for external
integrations. Every future platform (GitHub, ClickUp, Codex, IDE plugins,
MCP servers, etc.) must plug into this framework.

Phase 15 candidates (pending authorization):

- Authentication support for connectors (OAuth, API keys, tokens)
- Network connector implementations (GitHub API, MCP client, HTTP API)
- GUI connector management panel
- Connector testing framework
- Performance optimization for large-scale observation
- Connector persistence (stateful reconnection)
