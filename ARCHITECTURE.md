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

`KnowledgeIndexerService` receives filesystem events through a queue and one
worker. It safely skips text extraction for binary, malformed, or oversized
files while preserving metadata. `RetrievalService` supplies a stable lexical
API with scores and citations. `ContextBuilderService` turns ranked chunks into
bounded RAG context.

## Project intelligence

`KnowledgeGraphService` statically analyzes Python files for classes,
dataclasses, enums, functions, methods, variables, constants, decorators,
imports, inheritance, composition hints, calls, service registrations, and
EventBus subscriptions. `CrossReferenceService` combines graph evidence with
lexical retrieval for project-level questions. All graph facts are conservative
and read-only.

`SymbolIndexerService` owns version-aware symbol extraction, including module,
parent symbol, source spans, docstrings, visibility, signatures, and stable
SQLite symbol IDs. Architecture and documentation analyzers persist health and
coverage observations as reflections.

After a controlled workspace pass, `KnowledgeGraphService` conservatively
resolves local Python package imports. The original import target remains the
graph fact; a resolved document path is supplementary evidence in relationship
metadata.

## Boundaries

`ReasoningService` only prepares evidence and proposals; it cannot execute
actions. `MCPToolService` defines JSON-shaped domain tools, deliberately
separate from any future MCP transport/server.
