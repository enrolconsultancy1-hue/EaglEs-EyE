# Changelog

## Project Twin Discovery Connector — 2026-07-26

First v3.1 connector expansion: extends the frozen v3.0.0 platform with
real external project observation and Twin creation.

- **LocalProjectConnector** (`connectors/plugins/local_project_connector.py`):
  Implements Connector ABC, discovers project identity/type/stack/git/deps
  from a local folder. Detects 10 project types, 14 languages, 8 frameworks.
  Complies with Universal Observation Policy (discover/rank/select surfaces).
- **ProjectTwinDiscoveryService** (`services/project_twin_discovery_service.py`):
  Orchestrates discovery via LocalProjectConnector, publishes 7 EventBus
  notification events (CONNECTED → SCAN → IDENTIFIED → STACK → GIT →
  DEPENDENCIES → TWIN CREATED), stores twin JSON in `memory/twins/`,
  indexes knowledge via KnowledgeStoreService.
- **MCP tool `discover_project_twin`**: discovers a local project folder and
  returns a complete Project Twin with notifications, twin path, and
  discovery data.
- **Service registration**: ProjectTwinDiscoveryService registered in
  mcp_server.py after UniversalTwinReport, before MCPToolService.
- **Zero regressions**: all 403 existing tests continue to pass.
- **28 new Phase 19 tests**: 431 total passing tests.
- **41 MCP tools total** (40 existing + 1 new).
- No frozen files modified.

## Architecture Freeze — 2026-07-26

The AI Twin Core is permanently frozen as of v3.0.0.

- Created `ARCHITECTURAL_BASELINE_v3.0.0.md` — permanent architectural reference
- Established Architecture Freeze Policy — 22 frozen components
- Closed the foundational phase roadmap (Phases 8–18 complete, no more phases)
- Established capability-driven product roadmap (v3.1–v4.0) in ROADMAP.md
- All future development defined as capability expansion, not architectural redesign
- Governance rules documented: Architecture Validation Gate, UOP, URP, Release Gate
- No source code modified, no services changed, no APIs changed, no tests modified

## phase18-release / v3.0.0 — 2026-07-26

Phase 18 complete — Universal AI Project Twin. v3.0.0 is the final roadmap
milestone and permanent architectural baseline. Feature-frozen: no new
foundational layers, no redesigns. All work was integration, stabilization,
validation, and polish.

- **AITwinOrchestrator** (`services/ai_twin_orchestrator.py`): Coordinates all
  services into a single coherent AI Twin lifecycle. Exposes 8 stable Dashboard
  APIs: twin_status, twin_health, connector_status_summary, observation_status,
  reasoning_status, sync_status, project_health, evidence_metrics.
- **TwinIntegrityValidator** (`services/twin_integrity_validator.py`): 6
  consistency checks — Knowledge Graph, evidence, relationships, connectors,
  sync, provenance integrity. All-in-one `check_all()` method.
- **UnifiedProjectTwin** (`services/unified_project_twin.py`): One coherent
  representation integrating files, git, docs, evidence, tasks, decisions,
  relationships, architecture, history, risks, health, and connectors. Methods:
  overview, project_summary, connector_twin, reasoning_twin.
- **UniversalTwinReport** (`services/universal_twin_report.py`): Complete,
  evidence-backed AI Twin Report covering overview, health, integrity, status,
  blockers, bottlenecks, stale work, architecture drift. Summary mode for quick
  access.
- **8 new MCP tools**: ai_twin_status, ai_twin_health, ai_twin_integrity,
  ai_twin_overview, ai_twin_summary, ai_twin_connectors, ai_twin_reasoning,
  ai_twin_report. All 32 existing tools preserved. **40 tools total**.
- **Service registration**: 4 Phase 18 services registered in build_mcp_kernel()
  after ExplainableAIService, before MCPToolService. MCP protocol version 3.0.0.
- **Production hardening**: Removed empty `services/watcher_service.py` (0 lines).
- **Zero regressions**: 356 existing Phase 1–17 tests continue to pass.
- **47 new Phase 18 tests**: 403 total passing tests with zero regressions.

## phase17-release / v2.5.0 — 2026-07-26

Phase 17 complete — Autonomous Project Intelligence. v2.5.0 transforms EaglEs
EyE from an evidence collection platform into an evidence reasoning platform.
No new foundational layers.

- **Universal Reasoning Policy**: Every reasoning result preserves source connectors, observation surfaces, evidence IDs, confidence score, reasoning trace, supporting relationships, and timestamps. No hidden reasoning.
- **ReasoningEngine** (`services/reasoning_engine.py`): Single entry point for all reasoning. 7 methods covering cross-connector, dependencies, timeline, state transitions, relationship inference, evidence correlation, historical reconstruction.
- **ConfidenceEngine** (`services/confidence_engine.py`): Evidence quality scoring (citation/source/timestamp), relationship weighting, aggregate scoring. Missing evidence explicitly reported.
- **KnowledgeGraph enhancements** (`services/knowledge_graph_service.py`): 5 new methods — related_weighted, propagate_confidence (0.85x decay), temporal_relationships, multi_source_correlate, _compute_relationship_weight.
- **ProjectIntelligenceEngine** (`services/project_intelligence_engine.py`): Composite health score, blocker detection (errors, connector failures), bottleneck detection (high-failure rates), stale/orphan detection, architecture drift (snapshot comparison).
- **RootCauseAnalysisService** (`services/root_cause_analysis_service.py`): What changed, why, which connector, evidence citations, confidence, causal chain.
- **ImpactAnalysisService** (`services/impact_analysis_service.py`): Affected files, components, documentation, connectors, impact level.
- **DecisionLineageService** (`services/decision_lineage_service.py`): Full lineage trace from decision ID; list all lineages by workspace/session.
- **ExplainableAIService** (`services/explainable_ai_service.py`): Three-phase explanation — gather facts, derive relationships, build explanation with why/how/evidence/knowledge/sources.
- **8 new MCP tools**: explain_project_state, analyze_project_risk, root_cause_analysis, impact_analysis, project_health, reasoning_trace, evidence_lineage, dependency_graph. All 24 existing tools preserved. 32 tools total.
- **Service registration**: 7 Phase 17 services registered in build_mcp_kernel() after ConnectorSchedulerService, before MCPToolService. MCP protocol version 2.5.0.
- **Zero regressions**: 278 existing Phase 6–16 tests continue to pass.
- **Phase 17 release gate**: 78 Phase 17 tests passed; 356 total (361 including 5 pre-existing stdio exclusions).
- AI_TWIN_CONSTITUTION.md unchanged.
- ARCHITECTURE.md, PROJECT_STATUS.md, NEXT_TASK.md, BENCHMARKS.md, CHANGELOG.md updated.

## phase16-release / v2.4.0 — 2026-07-26

Phase 16 complete — External Project Integration Layer. v2.4.0 proves the
connector framework against a real external ecosystem (GitHub) while building
reusable infrastructure for all future integrations.

- **Universal Observation Policy**: 4 new abstract methods on Connector ABC — `discover_observation_surfaces()`, `rank_observation_surfaces()`, `select_observation_pipeline()`, `get_active_surfaces()`. All existing connectors implement them.
- **ObservationDiscoveryEngine**: reusable surface quality scoring, preference ordering, and automatic pipeline selection.
- **Connector Authentication** (`connectors/auth/`): PATAuth, OAuthAuth, APIKeyAuth, BearerTokenAuth with credential sanitization, validation, and secure header injection.
- **Webhook Framework** (`connectors/webhooks/`): WebhookRegistry, SignatureVerifier (HMAC-SHA256/SHA1), WebhookQueue, ReplayGuard, WebhookHandler. No platform-specific webhook handlers.
- **SyncEngine** (`connectors/sync.py`): initial_sync, delta_sync, resume, conflict detection with checkpoint persistence via SyncStore.
- **ConnectorSchedulerService** (`services/connector_scheduler_service.py`): background periodic sync with exponential backoff, daemon thread, 5-second check loop. Disabled by default.
- **MetricsCollector** (`connectors/metrics.py`): thread-safe per-connector counters for sync count, API requests, failures, retries, evidence, observations, throughput, uptime.
- **RESTConnector** (`connectors/rest_connector.py`): reusable base class for REST-based project systems with pagination (Link header / page-based), RetryPolicy (exponential backoff), health check, auth setup.
- **GitHubConnector** (`connectors/plugins/github_connector.py`): 9 capabilities — repository metadata, branches, commits, pull requests, issues, releases, tags, contributors, events. Two observation surfaces: `official_api`, `git_repository`.
- **Manifest extension**: 5 new fields (observation_surfaces, preferred_surface, supports_multi_surface, supports_incremental_sync, supports_realtime).
- **SDK extension**: `run_observation_discovery()` static method.
- **Validator extension**: `VALID_OBSERVATION_SURFACES`, `"network"` and `"webhook"` capabilities.
- **5 new MCP tools**: `github_connector_status`, `connector_sync`, `connector_metrics`, `connector_last_sync`, `connector_health_details`. All 19 existing tools preserved. 24 tools total.
- **Sample configs**: `github_connector.yaml.example`, `webhook_listener.yaml.example`.
- **Zero regressions**: 231 existing Phase 6–15 tests continue to pass.
- **Phase 16 release gate**: 42 Phase 16 tests passed; 273 total.
- **Service order**: ConnectorSchedulerService registered after EvidenceIngestionService, before MCPToolService in build_mcp_kernel().
- AI_TWIN_CONSTITUTION.md unchanged.
- ARCHITECTURE.md, PROJECT_STATUS.md, NEXT_TASK.md, BENCHMARKS.md, CHANGELOG.md updated.

## phase15-release / v2.3.0 — 2026-07-26

Phase 15 complete — Unified Evidence & Knowledge Graph. v2.3.0 connects the
connector evidence pipeline to the Knowledge Store, creating a single unified
evidence architecture.

- EventBus hardened: error isolation around subscriber callbacks, unsubscribe token support with `subscribe()` returning a token and `unsubscribe(token)` removing the listener.
- Created `EvidenceBus` (`connectors/evidence_bus.py`) bridging connector emit to the ingestion pipeline with publish/subscribe semantics.
- Created `EvidenceIngestionService` (`services/evidence_ingestion_service.py`) subscribing to EvidenceBus, transforming connector Evidence objects into KnowledgeStoreService event records. Exposes `ingest()` and `get_stats()`.
- Extended `ConnectorManager` to own an EvidenceBus instance and route observe/collect through it.
- Deprecated three pre-connector observer services with full backward compatibility:
  - `GitObserverService` — delegates to `GitConnector`, issues DeprecationWarning.
  - `EngineeringEvidenceService` — also publishes through EvidenceBus, issues DeprecationWarning.
  - `ProcessObserverService` — delegates to `EngineeringEvidenceService`, issues DeprecationWarning.
- Extended `KnowledgeGraphService` with `ingest_connector_evidence(connector_id, evidence_list)` creating `connector_evidence` relationship entries.
- Registered `EvidenceIngestionService` in `build_mcp_kernel()` after `ConnectorService`.
- 2 new MCP tools: `get_evidence_stats`, `get_connector_evidence`. All 17 existing tools preserved.
- Zero regressions: 203 existing Phase 6–14 tests continue to pass.
- Phase 15 release gate: 28 Phase 15 tests passed; 231 total.
- AI_TWIN_CONSTITUTION.md unchanged.
- ARCHITECTURE.md, PROJECT_STATUS.md, NEXT_TASK.md, BENCHMARKS.md, CHANGELOG.md updated.

## phase14-release / v2.2.0 — 2026-07-26

Phase 14 complete — Universal Connector Framework. v2.2.0 introduces the
only approved mechanism for external integrations.

- Created `connectors/` package with 12 modules: connector, connector_manager, registry, events, models, discovery, sdk, exceptions, health, loader, manifest, validator.
- Standard connector interface with 13 lifecycle and data methods.
- Connector manifests (JSON/YAML) with metadata, capabilities, permissions, and dependencies.
- Thread-safe `ConnectorRegistry` with automatic discovery and dependency resolution.
- `ConnectorHealth` state machine with 7 states and heartbeat monitoring.
- Canonical evidence model with Observation, Evidence, Artifact, Source, Identity, Timestamp, Confidence, RawPayload, NormalizedPayload, TraceInformation, CitationInformation.
- Normalization pipeline: Observe → Collect → Normalize → Validate → Emit → Knowledge Graph → Reasoning.
- 10 connector event types published to the kernel EventBus.
- `ConnectorSDK` for minimal-boilerplate connector development.
- `CapabilityValidator` and `PermissionValidator` with strict capability/permission sets.
- `ConnectorService` bridging the framework to the EyeKernel.
- Three reference connectors: FilesystemConnector, GitConnector (read-only), MockConnector.
- 3 new MCP tools: `list_connectors`, `get_connector_status`, `get_connector_health_all`. All 14 existing tools preserved.
- Dynamic plugin loading from `connectors/plugins/` — no kernel code changes required.
- Connector Developer Guide (`src/connectors/README.md`) with quick start, manifest spec, and lifecycle documentation.
- Zero regressions: 91 existing Phase 6–13 tests continue to pass.
- Phase 14 release gate: 112 Phase 14 tests passed; 203 total.
- AI_TWIN_CONSTITUTION.md unchanged.

## phase13-release / v2.1.0 — 2026-07-25

Phase 13 complete — Semantic Intelligence & Autonomous Awareness. v2.1.0 first post-roadmap delivery.

- Added `EmbeddingService` with three provider modes: `disabled` (default), `simple` (zero-dependency hash-based), `sentence_transformers` (production semantic search).
- Added `VectorSearchService` for cosine-similarity search across chunks, symbols, events, and decision records.
- Added `SemanticAwarenessService` for event-driven evidence-backed pattern detection (module clustering).
- Additive nullable `embedding BLOB` columns on `chunks`, `symbols`, `events`, `decision_records`, `reflections` tables.
- New `awareness_signals` table with TTL-based cleanup.
- Integrated embedding generation into `KnowledgeIndexerService` (config-gated, default off).
- 3 new MCP tools: `search_semantic`, `get_similar`, `get_awareness_signals`. All 11 existing tools preserved.
- Two new Mission Control views: Semantic Search panel and Awareness Signal feed.
- All existing 9 GUI nav bars updated to link to the two new panels.
- Strict boundaries preserved: no command execution, no workspace mutation, no hidden reasoning inference.
- Phase 13 release gate: 28 Phase 13 tests passed; 91 total.

## phase12-release / v2.0.0 — 2026-07-25

Phase 12 complete — EaglEs EyE Desktop GUI. v2.0.0 first complete product release.

- Added `gui/` package with MCP client, web server, and Mission Control UI.
- Seven Mission Control views: Dashboard, Timeline Viewer, AI Twin Explorer, Search, Graph View, Cognitive Explain Panel, Metrics.
- Cognitive Explain Panel enforcing Phase 10 evidence boundary: Observed Facts → Derived Relationships → Evidence-Backed Explanation.
- Strict consumer boundary: GUI communicates via MCP only — never imports EyeKernel, writes SQLite, mutates workspaces, or executes commands.
- Phase 12 release gate: 21 Phase 12 tests passed; 98 total (100 total with 2 pre-existing watchdog exclusions).

## phase11-release — 2026-07-25

Phase 11 complete — MCP Ecosystem.

- Added `src/mcp/` package with stdio JSON-RPC 2.0 transport (`transport_stdio.py`), localhost-only TCP transport (`transport_tcp.py`, disabled by default), tool registry (`tool_registry.py`), and MCP protocol server (`mcp_server.py`).
- Full MCP protocol support: initialize handshake, tools/list, tools/call with structured JSON-RPC 2.0 error codes.
- Expanded `MCPToolService` with 5 Phase 10 evidence tools: `explain_change`, `get_causal_chain`, `compare_snapshots`, `list_decisions`, `get_decision`.
- Preserved all 6 legacy Phase 6–9 tools with full backward compatibility.
- Security boundary: MCP disabled by default, TCP localhost-only, no process/workspace mutation.
- Phase 11 release gate: 37 Phase 11 tests passed; 77 total (79 total with 2 pre-existing watchdog exclusions).

## phase10-release — 2026-07-25

Phase 10 complete — Evidence-Based Cognitive Layer.

- Added `CausalGraphService` for observable event relationship tracking and evidence-backed causal chains.
- Added `ArchitectureEvolutionService` for snapshot creation, structural diff, and evolution queries.
- Added `DecisionTrackingService` for recording explicit engineering decisions linked to workspace, session, and citations.
- Added `CognitiveLayerService` evidence-backed explanation engine separating observed facts → derived relationships → explanations.
- Extended SQLite schema additively with `causal_edges`, `decision_records`, `architecture_snapshots` tables, preserving all prior Phase 6–9 data.
- Strict evidence-boundary enforcement: no hidden reasoning, intent, or undocumented motivation claimed.
- Phase 10 release gate: 38 tests passed.

## phase9-release — 2026-07-25

Phase 9 complete — Multi-Agent Observation.

- Added `MultiAgentObservationService` to watch and compare multiple coding agents simultaneously.
- Added comprehensive comparison APIs across 5 distinct dimensions: Session, Agent, Timeline, Performance, and Architecture.
- Aligned multi-session timelines side-by-side to compare sequential agent actions sequentially.
- Expanded visible-marker-only agent detection within `AgentDetectorService` to support Codex, Claude Code, Gemini CLI, OpenCode, Aider, Cursor, Cline, Roo Code, Windsurf, GitHub Copilot, and future MCP agents.
- Fully preserved backward compatibility, SQLite data, and evidence-only boundaries.
- Phase 9 release gate: 31 tests passed.

## phase8-release — 2026-07-25

Phase 8 complete — AI Twin Observer Foundation.

- Added isolated workspace identity and durable session boundaries.
- Added workspace/session-scoped execution timelines and recovery queries.
- Added atomically written local Twin artifacts and evidence-based replay.
- Added visible-marker-only agent detection with explicit evidence.
- Phase 8 release gate: 28 targeted tests passed.

## phase7-release — 2026-07-25

Phase 7 complete — Reliability, Project Intelligence, Software Understanding,
and Passive Evidence Adapters.

- Added deterministic workspace indexing and local package-import resolution.
- Added evidence-only timelines and replayable session reconstruction.
- Added passive Git, build, test, and terminal evidence adapters.
- Preserved SQLite/JSON compatibility and read-only observer boundaries.
- Phase 7 release gate: 23 targeted tests passed.



\## v0.1.0



Initial public architecture.



Features:



\- Cognitive Kernel

\- Event Bus

\- File Watcher

\- Logger

\- Mirror

\- Memory

\- Reflection

