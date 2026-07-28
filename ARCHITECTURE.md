# EaglEs EyE Architecture

The architecture is governed by the
[AI Twin Observer Constitution](AI_TWIN_CONSTITUTION.md): observation is
passive, conclusions are evidence-backed, and services are extended without
breaking compatibility.

## Architecture Freeze

**v3.0.0 is the permanent architectural baseline.** The AI Twin Core is frozen.
See [ARCHITECTURAL_BASELINE_v3.0.0.md](ARCHITECTURAL_BASELINE_v3.0.0.md) for the
complete freeze policy, architectural principles, Universal Observation Policy,
Universal Reasoning Policy, service topology, evidence flow, and extension rules.

Future releases shall extend the platform — never redesign, replace, or
fundamentally alter the core. All future development follows the capability
roadmap in [ROADMAP.md](ROADMAP.md#product-roadmap--capability-driven).

EaglEs EyE is an event-driven kernel. `EyeKernel` owns service registration and
the synchronous `EventBus`; the watcher publishes filesystem lifecycle events.
Services initialize configuration-dependent runtime state in `start()`, after
`ConfigService` has loaded configuration.

## Memory compatibility

Existing JSON files (`memory.json`, `knowledge.json`, and `vision_memory.json`)
remain supported. Phase 6 introduced `knowledge.db` as the transactional store
and imports legacy `knowledge.json` once without deleting or rewriting it.

## Knowledge model

`KnowledgeStoreService` persists documents, versioned chunks, events,
observations, embeddings, reflections, retrieval logs, relationships, and
symbols. Document and chunk versions are append-preserving: prior chunks become
inactive rather than being erased. SQLite transactions guard each update.

`TimelineService` reconstructs ordered, cited timelines and bounded session
summaries directly from the durable event log. It is read-only: summaries state
only observable event counts, paths, timestamps, and evidence citations.

`SessionReconstructionService` turns a bounded timeline into a replay sequence
with one citation per observed step. It explicitly preserves the limits of the
evidence rather than filling gaps with inferred activity or reasoning.

`EngineeringEvidenceService` is the passive intake boundary for Git, build,
test, and terminal observations. It records caller-supplied evidence into the
same durable event log; it never executes commands or modifies the watched
workspace.

`GitObserverService` is the first observer adapter. It invokes only Git's
read-only status, branch, and revision queries, then records the resulting
facts through `EngineeringEvidenceService`; it never stages, commits, or edits
repository state.

`ProcessObserverService` is the passive adapter for externally observed build,
test, and terminal results. It accepts completed command evidence from an
observer and sends it through `EngineeringEvidenceService`; it never spawns a
process or alters a watched workspace.

## Phase 8.1 workspace identity foundation

`WorkspaceObserverService` is a registration-only foundation for multiple
isolated workspaces. It assigns deterministic IDs from normalized paths and
persists workspace metadata through `KnowledgeStoreService`; it does not alter
or replace the existing single-workspace `WatcherService` API.

SQLite now has additive `workspaces` and reserved `sessions` tables, plus
nullable `workspace_id` and `session_id` columns on events. Existing events
remain unchanged and valid; future phases may attach identity only when there
is explicit observable evidence.

## Phase 8 AI Twin observer foundation

`SessionRecorderService` creates durable workspace-scoped session boundaries
and records only caller-supplied observable events. `ExecutionTimelineService`
orders that evidence by timestamp and event ID within a workspace or session.

`TwinBuilderService` creates local, atomically written `timeline.json`,
`events.json`, and `summary.json` artifacts under the configured Twin directory.
`ReplayService` replays those persisted citations without adding explanations
that the evidence does not support.

`AgentDetectorService` classifies only visible workspace markers (supporting
Codex, Claude Code, Gemini CLI, OpenCode, Aider, Cursor, Cline, Roo Code,
Windsurf, GitHub Copilot, and future MCP agents) and returns the marker paths
as its evidence.

## Phase 9 multi-agent observation

`MultiAgentObservationService` watches and compares multiple coding agents
simultaneously using observable event data, session metadata, and workspace
markers.

It provides comparison APIs across five distinct dimensions:

1. **Session Comparison:** Analyzes session metadata, durations, files touched,
   and event compositions.

2. **Agent Comparison:** Maps agent detections side-by-side with associated
   workspace and session contexts.

3. **Timeline Comparison:** Aligns multi-session timelines side-by-side
   sequentially.

4. **Performance Comparison:** Tallies and compares execution duration, event
   rates, and test success/failure outcomes.

5. **Architecture Comparison:** Examines structural impact through file paths
   and event type touchpoints of each agent's active sessions.

It maintains strict compliance with evidence-only boundaries and does not infer
hidden reasoning.

`KnowledgeIndexerService` receives filesystem events through a queue and one
worker. It safely skips text extraction for binary, malformed, or oversized
files while preserving metadata.

`RetrievalService` supplies a stable lexical API with scores and citations.
`ContextBuilderService` turns ranked chunks into bounded RAG context.

## Phase 7 Cognitive Twin

`CognitiveTwinService` (`services/cognitive_twin_service.py`) transforms a
discovered Project Twin into seven cognitive knowledge dimensions using only
deterministic reasoning over existing evidence:

1. **Purpose** — extracted from architect_summary, purpose_clues, README content.
2. **Domain** — from project classification (mobile, web, backend, enterprise, AI).
3. **Architecture** — patterns detected from documentation and tech_stack analysis.
4. **Maturity** — composite score from documentation completeness, version
   control, technology lifecycle, and codebase size.
5. **Key Components** — infrastructure (CI/CD, Docker, build), documentation
   categories, and technology tiers.
6. **Risks** — version control gaps, sparse documentation, legacy/declining
   technologies, large dependency footprint, low classification confidence.
7. **Recommendations** — improvement suggestions sorted by priority (critical,
   high, medium, low).
8. **Code Summary** (Phase 8 integration) — languages, components, architecture
   layers, complexity, entry points, important files.

The service provides a `ask(question)` interface that routes natural-language
questions to the appropriate cognitive handler. Every answer includes cited
evidence and a confidence level. No external LLM calls are used.

The service is registered in `build_mcp_kernel()` after
`ProjectTwinDiscoveryService` and before `MCPToolService`. A
`cognitive_twin_query` MCP tool exposes the interface, and the GUI twin.html
page provides a Cognitive Twin panel with quick-question buttons.

## Phase 8 Code Intelligence Twin

`CodeIntelligenceService` (`services/code_intelligence_service.py`) analyzes
project source code to enrich the Project Twin with language detection, source
scanning, code knowledge graphs, and architecture understanding. All analysis
is deterministic regex-based scanning — no external LLM calls.

### Capabilities

| Capability | Description |
|---|---|
| **Language Detection** | Detects Python, Dart, JavaScript, TypeScript, Java, C#, Go by file extension; returns file counts and percentages |
| **Source Scanning** | Extracts classes, functions/methods, imports from source files using language-specific regex patterns |
| **Code Knowledge Graph** | Builds nodes (classes, modules) and edges (imports, defined_in relationships) |
| **Architecture Layers** | Detects 30+ layer types from naming patterns: Service, Repository, Controller, Provider, Data, Presentation, Handler, Middleware, Utility, Configuration, etc. |
| **Entry Points** | Finds main.py, main.dart, app.py, index.js, etc. |
| **Important Files** | Scores files by class count, import count, and line count |
| **Complexity Estimation** | Returns low/medium/high based on lines and class count |

### Code query

`code_query(question)` answers natural-language questions about code structure:
classes, functions, languages, imports/dependencies, graph, architecture layers,
entry points, important files, complexity, components/modules, overview, and
free-text keyword search (e.g. "Where is authentication implemented?"). Returns
`{answer, evidence, confidence}`.

### Cognitive Twin integration

`CognitiveTwinService._generate_cognition()` includes an 8th dimension
`code_summary` generated by delegating to `CodeIntelligenceService.analyze_project()`.
Code-related questions in `CognitiveTwinService.ask()` route through
`CodeIntelligenceService.code_query()`.

### Service registration

`CodeIntelligenceService` is registered in `build_mcp_kernel()` after
`CognitiveTwinService` and before `MCPToolService`:

```
...
CognitiveTwinService
  ↓
CodeIntelligenceService
  ↓
MCPToolService  (consumes all above)
```

### MCP tools

| Tool | Purpose |
|---|---|
| `code_intelligence` | Analyze source code and return full code analysis |
| `code_query` | Answer a question about the project's source code |

### GUI

A Code Intelligence Twin section in `twin.html` displays:
- Language detection cards (name, files, percentage)
- Architecture layers with file counts
- Important files with class names and scores
- Code graph info (nodes, edges)
- Query box with 8 quick-question buttons (Overview, Classes, Functions,
  Languages, Architecture, Dependencies, Entry Points, Complexity)

## Project intelligence

`KnowledgeGraphService` statically analyzes Python files for classes,
dataclasses, enums, functions, methods, variables, constants, decorators,
imports, inheritance, composition hints, calls, service registrations, and
EventBus subscriptions.

`CrossReferenceService` combines graph evidence with lexical retrieval for
project-level questions. All graph facts are conservative and read-only.

`SymbolIndexerService` owns version-aware symbol extraction, including module,
parent symbol, source spans, docstrings, visibility, signatures, and stable
SQLite symbol IDs.

Architecture and documentation analyzers persist health and coverage
observations as reflections.

After a controlled workspace pass, `KnowledgeGraphService` conservatively
resolves local Python package imports. The original import target remains the
graph fact; a resolved document path is supplementary evidence in relationship
metadata.

## Phase 10 cognitive layer evidence boundary

The Cognitive Layer extends EaglEs EyE reasoning capabilities while preserving
the evidence-only architecture boundary.

Phase 10 introduces:

- Causal graph relationships between observable events.
- Architecture evolution tracking.
- Explicit engineering decision records.
- Evidence-backed explanation generation.

All cognitive capabilities maintain strict separation:
Observed Facts
↓
Derived Relationships
↓
Evidence-Backed Explanations

### Observed Facts

Observed facts are directly recorded evidence from:

- Filesystem events.
- Git observations.
- Build observations.
- Test observations.
- Terminal observations.
- Workspace sessions.
- Agent-visible markers.
- Explicit engineering records.

Observed facts must contain traceable citations.

### Derived Relationships

Derived relationships are machine-generated connections calculated only from
observable evidence.

Examples:

- Event ordering.
- Candidate causal links.
- Architecture differences.
- Symbol evolution.
- Dependency changes.
- Session correlations.

Derived relationships must never introduce unsupported assumptions.

### Evidence-Backed Explanations

The Cognitive Layer may generate explanations only from:

- Observed facts.
- Derived relationships.
- Stored citations.

Allowed example:

> RetrievalService.py changed before a failing test event and was followed by a
> later commit where the test passed.

Not allowed:

> The developer changed RetrievalService.py because they wanted better
> performance.

unless that motivation exists as an explicit recorded decision.

The system must never claim:

- Hidden AI reasoning.
- Developer intent.
- Unobserved motivations.
- Private decision processes.

`CognitiveLayerService` extends the existing read-only reasoning foundation by
producing structured explanations grounded in evidence graphs and citations. It
coordinates three subordinate services:

- **`CausalGraphService`** — tracks observable event relationship edges
  (`causal_edges` table) with citation-backed relation types, supporting
  upstream/downstream queries and full causal chain reconstruction.
- **`ArchitectureEvolutionService`** — creates point-in-time architecture
  snapshots (symbol sets, dependency graphs, module structure), computes
  structural diffs, and supports evolution timeline queries.
- **`DecisionTrackingService`** — persists explicit engineering decision records
  (`decision_records` table) with workspace/session scoping, rationale, and
  supporting citations; decisions are recorded facts, not inferred intent.

All three services are additive: they extend the Phase 6 SQLite schema without
modifying prior tables or breaking existing Phase 6–9 APIs.

## Phase 11 MCP ecosystem

Phase 11 transforms EaglEs EyE from a local-process library into a
network-accessible MCP-compatible server while preserving all existing
boundaries.

The architecture follows a strict layered hierarchy:

```
External MCP Client
        ↓
   MCP Transport
        ↓
  Tool Registry
        ↓
  MCPToolService
        ↓
 Existing Services
        ↓
  Evidence Store
```

### Transport layer

`src/mcp/` provides three transport modules:

- **`transport_stdio.py`** — line-delimited JSON-RPC 2.0 over stdin/stdout.
  Read-only by default; no network exposure.
- **`transport_tcp.py`** — optional TCP socket server bound to `127.0.0.1`
  only. Disabled by default; requires explicit `mcp.tcp.enabled: true`
  configuration to activate.
- **`mcp_server.py`** — `MCPServer` class handling the `initialize`,
  `tools/list`, and `tools/call` MCP protocol methods with JSON-RPC 2.0
  structured error codes (-32700, -32600, -32601, -32602, -32603, -32000).

### Tool registry

`ToolRegistry` provides a decorator-based registration system with:

- Tool name, description, and JSON Schema input annotations.
- `list_tools()` returning MCP-compliant tool metadata.
- `call_tool()` dispatching to registered functions with argument validation.
- Future plugin extension point (no uncontrolled execution plugins).

### MCPToolService expansion

`MCPToolService` preserves all existing Phase 6–9 tools (`search_memory`,
`build_context`, `get_document`, `get_recent_events`, `reindex_memory`,
`cross_reference`) and adds five Phase 10 evidence tools:

- `explain_change` — evidence-backed explanation for entity changes via
  `CognitiveLayerService`.
- `get_causal_chain` — trace causal chains forward/backward from an event via
  `CausalGraphService`.
- `compare_snapshots` — structural diff between architecture snapshots via
  `ArchitectureEvolutionService`.
- `list_decisions` — engineering decision records filtered by workspace or
  session via `DecisionTrackingService`.
- `get_decision` — single decision record by ID via `DecisionTrackingService`.

All tools return structured data with evidence citations and observable facts
only.

### Security boundaries

- MCP server is **disabled by default** (`mcp.enabled: false`).
- Write tools (`reindex_memory`) require explicit opt-in config flag.
- No MCP tool may spawn processes, execute shell commands, edit workspace
  files, stage commits, or alter repositories.
- TCP transport is **localhost-only** when enabled; authentication required
  before remote access.
- `EyeKernel`, `EventBus`, and all service boundaries remain unchanged. The
  MCP layer is a transport facade, not a kernel replacement.

### Integration test

Run the MCP server via:

    EAGLE_EYE_MEMORY_PATH=/tmp/eye python -m mcp.mcp_server

Then send JSON-RPC 2.0 messages over stdin:

    {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26"}}
    {"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
    {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_memory","arguments":{"query":"RetrievalService"}}}

## Phase 12 Desktop GUI (v2.0.0)

Phase 12 delivers the first complete product release: EaglEs EyE Desktop GUI
("Mission Control"). The GUI is a pure consumer — it communicates exclusively
through the Phase 11 MCP layer.

```
Desktop GUI
        ↓
   MCP Client
        ↓
   MCP Server
        ↓
  Evidence-backed Services
```

### Architecture

```
gui/
  __init__.py
  mcp_client.py     — JSON-RPC 2.0 client connecting to MCP server via stdio
  server.py         — HTTP server (built-in http.server) proxying MCP API
  app.py            — Entry point booting both MCP kernel and web server
  templates/        — HTML views for each Mission Control panel
  static/           — CSS and other static assets
```

### Mission Control views

| View | File | Backend Services Used |
|---|---|---|
| **Dashboard** | `templates/dashboard.html` | GetRecentEvents, session/agent data via MCP |
| **Timeline Viewer** | `templates/timeline.html` | GetRecentEvents, ordered event citations |
| **AI Twin Explorer** | `templates/twin.html` | ListDecisions, Twin artifact descriptions |
| **Search** | `templates/search.html` | SearchMemory, CrossReference |
| **Graph View** | `templates/graph.html` | CrossReference, causal chain, snapshot data |
| **Cognitive Explain Panel** | `templates/explain.html` | ExplainChange, GetCausalChain, GetDecision, ListDecisions |
| **Metrics** | `templates/metrics.html` | GetRecentEvents aggregations |

### Cognitive Explain Panel

The Explain panel visually enforces the Phase 10 evidence boundary:

```
Observed Facts
        ↓
Derived Relationships
        ↓
Evidence-Backed Explanation
        ↓
Citations
```

### Security

- GUI connects to MCP server at `127.0.0.1:9103` (localhost only).
- All operations are read-only through the MCP layer.
- No command execution, file editing, or git mutation is exposed.
- No direct EyeKernel import, no SQLite writes, no service modifications.
- Configuration via environment variables (`GUI_HOST`, `GUI_PORT`, `GUI_OPEN_BROWSER`).

### Running

    python -m gui.app

This starts the MCP server kernel, opens Mission Control in the default
browser, and serves the dashboard at `http://127.0.0.1:9103`.

## Phase 13 Semantic Intelligence & Autonomous Awareness (v2.1.0)

Phase 13 evolves EaglEs EyE from a reactive query-response system into an
evidence-backed semantic awareness platform by adding production embeddings,
vector search, and event-driven awareness signals.

### New services

```
EmbeddingService          — configurable embedding generation (simple hash or
                            sentence-transformers), disabled by default
VectorSearchService       — cosine-similarity search across embedded chunks,
                            symbols, events, and decision records
SemanticAwarenessService  — event-driven pattern detection producing
                            evidence-backed awareness signals
```

### Embedding architecture

`EmbeddingService` supports three provider modes:

| Provider | Description | Dependencies |
|----------|-------------|--------------|
| `disabled` (default) | No embeddings generated | None |
| `simple` | Deterministic hash-based embedding (128-dim) | None |
| `sentence_transformers` | Production semantic embeddings | sentence-transformers |

Embeddings are stored as additive nullable `BLOB` columns on the `chunks`,
`symbols`, `events`, `decision_records`, and `reflections` tables. Existing
records are never modified.

### Vector search

`VectorSearchService` provides:

- `search(query, table, top_k)` — cosine similarity ranked results.
- `find_similar(row_id, table, top_k)` — similarity to a known entity.
- `search_cross_entity(query, top_k)` — simultaneous search across all
  embedded entity types.

Lexical `RetrievalService` is fully preserved. Vector search is additive.

### Awareness signals

`SemanticAwarenessService` subscribes to existing EventBus events
(`FILE_CREATED`, `FILE_MODIFIED`) and detects evidence-backed patterns:

- **Module clustering**: multiple edits detected in the same module within a
  configurable window produces a `module_cluster` signal.

All signals cite the triggering evidence. The service never infers intent,
motivation, hidden reasoning, or future actions.

Results are stored in the new `awareness_signals` table with TTL-based
cleanup.

### New MCP tools

| Tool | Purpose |
|------|---------|
| `search_semantic` | Vector similarity search across embedded entities |
| `get_similar` | Find semantically similar items to a known entity |
| `get_awareness_signals` | List recent evidence-backed awareness signals |

All existing 11 tools remain unchanged. Protocol unchanged (JSON-RPC 2.0).

### New GUI views

| View | File | Description |
|------|------|-------------|
| **Semantic Search** | `search_semantic.html` | Vector similarity search with entity type selection and similar-item finder |
| **Awareness Feed** | `awareness.html` | Recent evidence-backed awareness signals with type filter |

Nav bars on all existing views link to the two new panels. GUI remains a pure
MCP consumer — no direct EyeKernel import, no SQLite writes, no workspace
mutation.

### Service startup order

In `build_mcp_kernel()`, the three Phase 13 services are registered after the
cognitive layer services and before `MCPToolService`:

```
EmbeddingService
    ↓
VectorSearchService
    ↓
SemanticAwarenessService
    ↓
MCPToolService  (consumes all three)
```

## Phase 14 Universal Connector Framework (v2.2.0)

Phase 14 introduces the Connector Framework — the only approved mechanism for
external integrations. Every future platform must plug into this framework;
no connector may bypass it.

### Architecture

```
connectors/
  __init__.py            — Package docstring
  connector.py           — Base Connector abstract class
  connector_manager.py   — Connector lifecycle orchestration
  registry.py            — Thread-safe connector registry
  events.py              — Connector event type constants and data
  models.py              — Canonical evidence model (Observation, Evidence, etc.)
  discovery.py           — Connector discovery from manifests
  sdk.py                 — Connector SDK helper and pipeline runner
  exceptions.py          — Connector-specific exception hierarchy
  health.py              — ConnectorState enum and ConnectorHealth dataclass
  loader.py              — Dynamic connector loading from plugins
  manifest.py            — Connector manifest parser (JSON/YAML)
  validator.py           — Capability, permission, and manifest validation
  plugins/               — Sample reference connectors
    filesystem_connector.py
    git_connector.py
    mock_connector.py
```

### Standard connector interface

Every connector exposes: `connect()`, `disconnect()`, `start()`, `stop()`,
`discover()`, `observe()`, `collect()`, `normalize()`, `emit()`,
`health()`, `heartbeat()`, `status()`.

### Normalization pipeline

```
Observe
  ↓
Collect
  ↓
Normalize
  ↓
Validate
  ↓
Emit
  ↓
Knowledge Graph
  ↓
Reasoning
```

No connector may inject data directly into the knowledge graph or reasoning
systems.

### Connector manifests

Connectors declare metadata in `connector.yaml` or `connector.json`:
connector ID, name, version, vendor, capabilities, permissions, minimum
Eye version, supported OS, entry point, and dependencies. Manifests are
discovered automatically from `connectors/plugins/`.

### Evidence model

The canonical evidence format includes: Observation, Evidence, Artifact,
Source, Identity, Timestamp, Confidence, RawPayload, NormalizedPayload,
TraceInformation, CitationInformation, Relationship, Metadata.

### Connector health

Every connector reports: state (disconnected/connected/starting/running/
paused/error/stopped), last heartbeat, last observation, errors, uptime,
started-at.

### Connector events

The framework publishes events to the kernel EventBus: CONNECTOR_REGISTERED,
CONNECTOR_STARTED, CONNECTOR_STOPPED, CONNECTOR_HEALTH_CHANGED,
CONNECTOR_DISCOVERED, CONNECTOR_FAILED, CONNECTOR_OBSERVATION,
CONNECTOR_EVIDENCE, CONNECTOR_WARNING, CONNECTOR_ERROR.

### MCP tool integration

Three new MCP tools are exposed:

| Tool | Purpose |
|------|---------|
| `list_connectors` | List all registered connectors and their status |
| `get_connector_status` | Get detailed status for a specific connector |
| `get_connector_health_all` | Get health status for all registered connectors |

### ConnectorService

`ConnectorService` bridges the connector framework to the EyeKernel. It owns
a `ConnectorManager`, registers built-in connectors (Filesystem, Git, Mock)
at startup, and publishes connector events to the kernel's EventBus. It is
registered in `build_mcp_kernel()` alongside existing services.

### Sample connectors

| Connector | Capabilities | Description |
|-----------|-------------|-------------|
| FilesystemConnector | filesystem, documents, logs, artifacts | Walks directories, reports file metadata |
| GitConnector | git, commits | Read-only Git status, branch, log queries |
| MockConnector | api, knowledge | Test/development reference with configurable failure modes |

### Service startup order

In `build_mcp_kernel()`, `ConnectorService` is registered after the Phase 13
semantic services and before `MCPToolService`:

```
EmbeddingService
  ↓
VectorSearchService
  ↓
SemanticAwarenessService
  ↓
ConnectorService
  ↓
MCPToolService  (consumes all above)
```

## Phase 15 Unified Evidence & Knowledge Graph (v2.3.0)

Phase 15 connects the Connector Framework evidence pipeline to the Knowledge
Store, creating a single unified evidence architecture. All observation now
flows through the connector framework.

### Complete evidence pipeline

```
Connector
    ↓
Observe
    ↓
Collect
    ↓
Normalize
    ↓
Evidence Bus
    ↓
Evidence Ingestion Service
    ↓
Knowledge Store
    ↓
Knowledge Graph
    ↓
Retrieval
    ↓
Reasoning
    ↓
AI Twin
```

### EvidenceIngestionService

`EvidenceIngestionService` subscribes to the `EvidenceBus` (inside
`ConnectorManager`) and transforms connector `Evidence` objects into
`KnowledgeStoreService` event records. It completes the gap that existed in
Phase 14 where the evidence pipeline terminated at "Emit".

Key methods:
- `ingest(connector_id, evidence_list)` — manually ingest evidence
- `get_stats()` — return ingested count

### EvidenceBus

`EvidenceBus` (`connectors/evidence_bus.py`) bridges the connector emit step
to the ingestion service. It maintains its own subscriber list and also
publishes to the kernel EventBus for backward compatibility.

### Single observation architecture

Phase 15 eliminates duplicate observation paths by deprecating three pre-
connector services and routing their behavior through the connector framework:

| Deprecated Service | Replacement | Migration |
|---|---|---|
| `GitObserverService` | `GitConnector` | Routes through `GitConnector` when available; prints deprecation warning |
| `EngineeringEvidenceService` | Evidence pipeline | Writes directly to store AND emits through `EvidenceBus`; prints deprecation warning |
| `ProcessObserverService` | Evidence pipeline | Delegates to `EngineeringEvidenceService`; prints deprecation warning |

All three services remain importable and callable — existing code continues to
work — but emit deprecation warnings on first use.

### EventBus hardening

The `EventBus` now supports:
- **Error isolation** — each subscriber callback is wrapped in try/except;
  a failing subscriber no longer prevents remaining subscribers from receiving
  the event.
- **Unsubscribe** — `subscribe()` returns a token; `unsubscribe(token)` removes
  the listener. This enables clean service lifecycle management.

### KnowledgeGraphService extension

`KnowledgeGraphService.ingest_connector_evidence(connector_id, evidence_list)`
accepts connector evidence and creates `connector_evidence` relationship entries
in the Knowledge Store. This provides a unified graph view that spans Python
AST analysis and connector evidence.

### New MCP tools

| Tool | Purpose |
|------|---------|
| `get_evidence_stats` | Evidence ingestion pipeline statistics |
| `get_connector_evidence` | Trigger evidence collection from a connector and ingest into the knowledge store |

### Service startup order

In `build_mcp_kernel()`, `EvidenceIngestionService` is registered after
`ConnectorService` and before `MCPToolService`:

```
EmbeddingService
  ↓
VectorSearchService
  ↓
SemanticAwarenessService
  ↓
ConnectorService
  ↓
EvidenceIngestionService
  ↓
MCPToolService  (consumes all above)
```

## Phase 17 Autonomous Project Intelligence (v2.5.0)

Phase 17 transforms EaglEs EyE from an evidence collection platform into an
evidence reasoning platform. It builds entirely on existing architecture
without introducing new foundational layers.

### Universal Reasoning Policy

**Every reasoning result SHALL preserve complete evidence provenance.**

A reasoning result SHALL NEVER exist without:

- Source Connector(s)
- Observation Surface(s)
- Evidence IDs
- Confidence Score
- Reasoning Trace
- Supporting Relationships
- Timestamp(s)

Every conclusion shall remain reproducible. No hidden reasoning. No unsupported
conclusions. No connector provenance may be discarded.

### ReasoningEngine (single entry point)

`ReasoningEngine` (`services/reasoning_engine.py`) is the single entry point for
all Phase 17 reasoning. MCP tools delegate to ReasoningEngine, which routes to
the appropriate sub-engine:

```
MCP Tool
    │
    ▼
ReasoningEngine
    │
    ├── Course: cross-connector, dependency, timeline,
    │          state transition, relationship inference,
    │          evidence correlation, historical reconstruction
    ├── ProjectIntelligenceEngine  (health, blockers, bottlenecks, stale, drift)
    ├── RootCauseAnalysisService   (what/why/evidence/confidence)
    ├── ImpactAnalysisService      (files, components, docs, connectors)
    ├── DecisionLineageService     (decision → evidence → observation → source)
    ├── ConfidenceEngine           (score, quality, missing, trace)
    └── ExplainableAIService       (why, how, evidence, knowledge, sources)
```

Reasoning methods:

| Method | Purpose |
|--------|---------|
| `reason_cross_connector(query)` | Search across all connectors for evidence |
| `reason_dependencies(path, depth)` | Dependency graph with confidence propagation |
| `reason_timeline(path, session_id)` | Ordered event timeline with causal relationships |
| `reason_state_transitions(path)` | Document version transition analysis |
| `reason_relationships(path)` | Relationship inference with weighting |
| `reason_evidence_correlation(connector_ids)` | Cross-connector evidence correlation |
| `reason_historical(path, session_id)` | Historical reconstruction with evolution |

### ConfidenceEngine

`ConfidenceEngine` (`services/confidence_engine.py`) provides:

- `score_evidence(evidence_list)` — composite score from quality, coverage, trace
- `score_relationships(relationships)` — weight-based relationship confidence
- `aggregate(*scores_and_details)` — combine multiple confidence scores

Every evidence item is assessed for citation presence, source connector, and
timestamp. Missing evidence is explicitly reported (never fabricated).

### KnowledgeGraph Enhancements

Added to `KnowledgeGraphService` (`services/knowledge_graph_service.py`):

| Method | Purpose |
|--------|---------|
| `related_weighted(path)` | Relationships annotated with computed confidence weights |
| `propagate_confidence(paths, confidence, depth)` | Confidence propagation along graph edges with decay (0.85x per hop) |
| `temporal_relationships(path, window_days)` | Relationships bounded by recency window |
| `multi_source_correlate(connector_ids)` | Cross-connector evidence correlation |
| `_compute_relationship_weight(metadata)` | Weight from confidence, resolution, type |

Relationship weight formula:
```
base = 1.0 × confidence × (1.2 if resolved_local else 0.5 if unresolved)
                                  × (1.1 if typed_relation)
                                  → clamped to [0, 2.0]
```

### ProjectIntelligenceEngine

`ProjectIntelligenceEngine` (`services/project_intelligence_engine.py`)
automatically determines:

| Method | Detection |
|--------|-----------|
| `project_health(workspace_id)` | Composite health from doc count, relationships, connector health |
| `detect_blockers(workspace_id)` | Error events, connector failures, causal blockers |
| `detect_bottlenecks()` | High-failure connectors, high-frequency event types |
| `detect_stale_work(days)` | Stale (>N days) and orphaned (no relationships) documents |
| `detect_architecture_drift()` | Symbol changes between architecture snapshots |

### RootCauseAnalysisService

`RootCauseAnalysisService` (`services/root_cause_analysis_service.py`):

- `analyze(issue, path, session_id)` — determines what changed, why, which
  connector observed it, which evidence supports it, confidence score, related
  artifacts. Includes causal chain analysis and symbol evolution tracking.

### ImpactAnalysisService

`ImpactAnalysisService` (`services/impact_analysis_service.py`):

- `analyze(path)` — determines files affected, components affected,
  documentation affected, connectors involved, estimated impact level
  (low/medium/high). Uses knowledge graph relationships, causal downstream
  chains, and where-used analysis.

### DecisionLineageService

`DecisionLineageService` (`services/decision_lineage_service.py`):

- `trace(decision_id)` — full lineage: decision → supporting evidence → related
  observations → timeline → confidence → source connectors
- `list_lineages(workspace_id, session_id)` — list all decision lineages

### ExplainableAIService

`ExplainableAIService` (`services/explainable_ai_service.py`):

- `explain(query, path, workspace_id, session_id)` — three-phase explanation:
  1. Gather facts (events, documents, symbols, cognitive explanations)
  2. Derive relationships (evidence ordering, causal chains)
  3. Build explanation (why, how, supporting evidence, related knowledge)

### New MCP tools (32 total)

| Tool | Backend Service |
|------|----------------|
| `explain_project_state` | ExplainableAIService via ReasoningEngine |
| `analyze_project_risk` | ProjectIntelligenceEngine (blockers + bottlenecks + stale + drift) |
| `root_cause_analysis` | RootCauseAnalysisService |
| `impact_analysis` | ImpactAnalysisService |
| `project_health` | ProjectIntelligenceEngine |
| `reasoning_trace` | ReasoningEngine (cross_connector/dependencies/timeline/evidence_correlation/historical) |
| `evidence_lineage` | DecisionLineageService |
| `dependency_graph` | ReasoningEngine (dependencies with depth) |

All 24 existing tools preserved unchanged.

### Service startup order

In `build_mcp_kernel()`, the seven Phase 17 services are registered after
`ConnectorSchedulerService` and before `MCPToolService`:

```
EmbeddingService
  ↓
VectorSearchService
  ↓
SemanticAwarenessService
  ↓
ConnectorService
  ↓
EvidenceIngestionService
  ↓
ConnectorSchedulerService
  ↓
ConfidenceEngine
  ↓
ReasoningEngine
  ↓
ProjectIntelligenceEngine
  ↓
RootCauseAnalysisService
  ↓
ImpactAnalysisService
  ↓
DecisionLineageService
  ↓
ExplainableAIService
  ↓
MCPToolService  (consumes all above)
```

## Phase 16 External Project Integration Layer (v2.4.0)

Phase 16 proves the Connector Framework against a real external ecosystem
(GitHub) while building reusable infrastructure for all future integrations:
authentication, webhooks, synchronization, scheduling, and metrics.

Phase 16 also establishes the **Universal Observation Policy** as a permanent
architectural contract — every connector discovers, ranks, and selects the
richest available observation pipeline automatically.

### Universal Observation Policy

Every connector SHALL implement:

| Method | Purpose |
|--------|---------|
| `discover_observation_surfaces()` | List every available authorized observation surface |
| `rank_observation_surfaces()` | Rank surfaces by evidence quality, latency, completeness, reliability |
| `select_observation_pipeline()` | Build the optimal observation pipeline automatically |
| `get_active_surfaces()` | Return currently active observation surfaces |

Observation surfaces ordered by preference:
1. Native AI Twin Connector
2. MCP Server
3. Official Plugin / Extension SDK
4. Official API
5. Webhooks / Event Streams
6. Local Workspace
7. Git Repository
8. Project Files
9. Build Artifacts / Config Files / Logs / Local Databases

### ObservationDiscoveryEngine

`ObservationDiscoveryEngine` (`connectors/observation_discovery.py`) provides
reusable surface discovery, ranking, and pipeline selection. It computes a
`SurfaceQuality` score from quality, latency, completeness, reliability, and
incremental sync capability, then selects the top-ranked surfaces.

### Connector Authentication Layer

`connectors/auth/__init__.py` provides secure credential providers:

| Provider | Class | Auth Mechanism |
|----------|-------|----------------|
| Personal Access Token | `PATAuth` | Bearer token in Authorization header |
| OAuth | `OAuthAuth` | Access/refresh token flow |
| API Key | `APIKeyAuth` | Custom header with key value |
| Bearer Token | `BearerTokenAuth` | Bearer token in Authorization header |

Credentials are never logged. All providers implement `authenticate()`,
`get_headers()`, `sanitize()`, and `validate()`.

### Generic REST Connector

`RESTConnector` (`connectors/rest_connector.py`) is the reusable base class for
REST-based project systems. Inherits from `Connector`. Provides:

- GET/POST request methods with retry and exponential backoff
- Pagination via Link header or page-based iteration
- MetricsCollector integration for API request/retry/failure tracking
- SyncEngine integration for checkpoint-based incremental sync
- Extensible auth via `_setup_auth()` (PAT, Bearer, API Key)

### GitHub Connector

`GitHubConnector` (`connectors/plugins/github_connector.py`) implements:

| Capability | REST API Endpoint | Evidence Type |
|---|---|---|
| Repository metadata | `GET /repos/{owner}/{repo}` | repository |
| Branches | `GET /repos/{owner}/{repo}/branches` | branches |
| Commits | `GET /repos/{owner}/{repo}/commits` | commits |
| Pull Requests | `GET /repos/{owner}/{repo}/pulls` | pull_requests |
| Issues | `GET /repos/{owner}/{repo}/issues` | issues |
| Releases | `GET /repos/{owner}/{repo}/releases` | releases |
| Tags | `GET /repos/{owner}/{repo}/tags` | tags |
| Contributors | `GET /repos/{owner}/{repo}/contributors` | contributors |
| Events | `GET /repos/{owner}/{repo}/events` | events |

All evidence flows through the established pipeline:
```
Connector → Observe → Collect → Normalize → EvidenceBus → EvidenceIngestionService → KnowledgeStore
```

No write operations. No issue creation. No PR modification. Observation only.

### Webhook Listener Framework

`connectors/webhooks/__init__.py` provides:

| Component | Purpose |
|-----------|---------|
| `WebhookRegistry` | Connector registration with secrets and event types |
| `SignatureVerifier` | HMAC-SHA256/SHA1 signature verification |
| `WebhookQueue` | FIFO queue with configurable retry |
| `ReplayGuard` | Idempotency via event ID deduplication |
| `WebhookHandler` | Top-level orchestration: receive, verify, queue, dispatch |

No platform-specific webhook handlers in Phase 16 — framework only.

### Synchronization Engine

`SyncEngine` (`connectors/sync.py`) supports:

| Operation | Purpose |
|-----------|---------|
| `initial_sync()` | Full fetch with cursor-based pagination |
| `delta_sync()` | Incremental sync from stored checkpoint |
| `resume()` | Resume incomplete sync from checkpoint |
| `detect_conflict()` | Compare local vs remote cursors |

Checkpoints stored in `SyncStore` (in-memory by default; extensible to SQLite).

### ConnectorSchedulerService

`ConnectorSchedulerService` (`services/connector_scheduler_service.py`)
provides background periodic synchronization:

- Register connectors with configurable interval
- Exponential backoff on consecutive failures
- Manual sync via `trigger_sync()`
- Daemon thread with 5-second check loop
- Disabled by default; enable via `config["connector_scheduler"]["enabled"]`

### Connector Metrics

`MetricsCollector` (`connectors/metrics.py`) tracks per-connector:

| Metric | Tracking |
|--------|----------|
| Sync count / duration | Incremented on each sync |
| API requests | Incremented per HTTP request |
| Failures / retries | Incremented on error/retry |
| Evidence created | Items synced per sync call |
| Throughput | Items/sec computed from total / elapsed |
| Uptime | Elapsed since connector metrics registration |

Thread-safe via `threading.Lock`.

### Service startup order

In `build_mcp_kernel()`, `ConnectorSchedulerService` is registered after
`EvidenceIngestionService` and before `MCPToolService`:

```
EmbeddingService
  ↓
VectorSearchService
  ↓
SemanticAwarenessService
  ↓
ConnectorService
  ↓
EvidenceIngestionService
  ↓
ConnectorSchedulerService
  ↓
MCPToolService  (consumes all above)
```

### New MCP tools (24 total)

| Tool | Purpose |
|------|---------|
| `github_connector_status` | Get detailed status of the GitHub connector |
| `connector_sync` | Trigger manual synchronization for a connector |
| `connector_metrics` | Get performance metrics for a connector |
| `connector_last_sync` | Get the last synchronization time for a connector |
| `connector_health_details` | Get detailed health information for connectors |

All 19 existing tools preserved unchanged.

### Platform independence

The AI Twin core contains no platform-specific logic. Only connectors contain
platform-specific code. Every future integration (ClickUp, Codex, Cursor,
Claude Desktop, Windsurf, VS Code, JetBrains, or any new platform) plugs into
the same framework, follows the Universal Observation Policy, and routes
through the established evidence pipeline.

## Boundaries

`ReasoningService` only prepares evidence and proposals; it cannot execute
actions.

`CognitiveLayerService` extends this model by organizing evidence into
explanations without inferring hidden reasoning.

`MCPToolService` defines JSON-shaped domain tools, deliberately separate from
any future MCP transport/server.

---

## Phase 18 — Universal AI Project Twin (v3.0.0, 2026-07-26)

Phase 18 delivers the first stable **Universal AI Project Twin**. It is
feature-frozen: no new foundational layers, no redesign of Connector Framework,
Knowledge Graph, Evidence Pipeline, or Reasoning Engine. All components are
`Service` subclasses consuming existing services.

### New architecture (all services)

```
[Phase 1–17 services unchanged]
  │
  ├── AITwinOrchestrator (services/ai_twin_orchestrator.py)
  │     Coordinates all services into single lifecycle. Exposes 8 Dashboard
  │     APIs: twin_status, twin_health, connector_status_summary,
  │     observation_status, reasoning_status, sync_status, project_health,
  │     evidence_metrics. Every result preserves URP provenance.
  │
  ├── TwinIntegrityValidator (services/twin_integrity_validator.py)
  │     6 consistency checks: KG, evidence, relationships, connectors, sync,
  │     provenance. All-in-one check_all() method.
  │
  ├── UnifiedProjectTwin (services/unified_project_twin.py)
  │     One coherent representation integrating files, git, docs, evidence,
  │     tasks, decisions, relationships, architecture, history, risks, health,
  │     and connectors — regardless of origin.
  │
  ├── UniversalTwinReport (services/universal_twin_report.py)
  │     Complete AI Twin Report: overview, health, integrity, status, blockers,
  │     bottlenecks, stale work, architecture drift. Entirely evidence-backed.
  │     Summary mode for quick access.
  │
  └── MCPToolService (services/mcp_tool_service.py)
        40 tools total (32 existing + 8 new):
        ai_twin_status, ai_twin_health, ai_twin_integrity,
        ai_twin_overview, ai_twin_summary, ai_twin_connectors,
        ai_twin_reasoning, ai_twin_report
```

### Service registration order

Phase 18 services are registered in `build_mcp_kernel()` after
`ExplainableAIService` and before `MCPToolService`:

```
... ExplainableAIService →
  AITwinOrchestrator → TwinIntegrityValidator →
  UnifiedProjectTwin → UniversalTwinReport →
  MCPToolService
```

### MCP protocol version

Updated to `3.0.0` in `mcp_server.py` initialize response.

### Production hardening

- Removed `services/watcher_service.py` (0-line empty stub, never functional).

### Universal AI Project Twin acceptance test

Given any supported project ecosystem and appropriate authorization,
EaglEs EyE can:
1. Discover the richest authorized observation surfaces (UOP — every connctor)
2. Continuously synchronize evidence (SyncEngine + ConnectorSchedulerService)
3. Maintain a unified project knowledge graph (KnowledgeGraphService)
4. Reason across all collected evidence (ReasoningEngine, 7 methods)
5. Explain every conclusion with complete provenance (URP — every result)
6. Present a single coherent AI Twin (AITwinOrchestrator + Unified +
   Report)
7. All without requiring changes to core architecture (platform independence)

### 403 tests passing, zero regressions

### Architecture Freeze

The foundational roadmap is complete. **No additional numbered phases will be
created.** The v3.0.0 architecture is permanently frozen per the Architecture
Freeze Policy in [ARCHITECTURAL_BASELINE_v3.0.0.md](ARCHITECTURAL_BASELINE_v3.0.0.md).

Future development follows the capability-driven product roadmap in
[ROADMAP.md](ROADMAP.md#product-roadmap--capability-driven). All future
extensions shall: extend the architecture, preserve backward compatibility,
comply with the Universal Observation Policy and Universal Reasoning Policy,
and never modify frozen components.

All autonomous capabilities must remain:

- Evidence-backed.
- Observable.
- Reproducible.
- Non-destructive.
