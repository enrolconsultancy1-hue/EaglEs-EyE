# EaglEs EyE Architecture

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

## Boundaries

`ReasoningService` only prepares evidence and proposals; it cannot execute
actions. `MCPToolService` defines JSON-shaped domain tools, deliberately
separate from any future MCP transport/server.
