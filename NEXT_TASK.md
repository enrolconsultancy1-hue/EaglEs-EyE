# Next Task

Phase 16 is complete and released as `phase16-release` / `v2.4.0`.

The External Project Integration Layer provides reusable infrastructure for
all future connectors: authentication, webhooks, sync engine, scheduler,
metrics, REST base, ObservationDiscoveryEngine, and the GitHub connector plugin.

The Universal Observation Policy (4 abstract methods on Connector ABC) is now
mandatory for every connector — surfaces are discovered, ranked, and selected
automatically.

Phase 17 candidates (pending authorization):

- Additional connector implementations (GitLab, Bitbucket, Jira, Slack, Notion)
- GUI connector management panel
- Connector testing framework / integration test harness
- Performance optimization for large-scale observation (rate limiting, caching)
- Connector persistence (stateful reconnection, SQLite SyncStore)
- Cross-workspace evidence merging in KnowledgeGraph
- Connector event replay / recovery
- Webhook listener server implementation
- OAuth token refresh flow
- CLI connector management commands (`eagle connector list|sync|status`)
- Multi-connector orchestration (coordinated sync across connectors)
