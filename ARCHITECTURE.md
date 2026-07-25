# EaglEs EyE Architecture

The architecture is governed by the
[AI Twin Observer Constitution](AI_TWIN_CONSTITUTION.md): observation is
passive, conclusions are evidence-backed, and services are extended without
breaking compatibility.

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

## Boundaries

`ReasoningService` only prepares evidence and proposals; it cannot execute
actions.

`CognitiveLayerService` extends this model by organizing evidence into
explanations without inferring hidden reasoning.

`MCPToolService` defines JSON-shaped domain tools, deliberately separate from
any future MCP transport/server.

All autonomous capabilities must remain:

- Evidence-backed.
- Observable.
- Reproducible.
- Non-destructive.
