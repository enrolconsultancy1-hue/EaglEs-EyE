# EaglEs EyE

> A modular cognitive AI kernel that observes, remembers, reflects, reasons,
> and is evolving into a safe software-understanding engine.

## Vision

EaglEs EyE is an event-driven AI operating kernel. Its services communicate
through an EventBus to observe filesystem activity, mirror files, preserve
legacy memory, build durable knowledge, and provide evidence for future agents.

## Current capabilities

- Kernel, EventBus, configuration, logging, watcher, and mirror services.
- Legacy JSON event, semantic, and vision memory compatibility.
- SQLite-backed versioned documents, chunks, events, reflections, and graph
  facts via `knowledge.db`.
- Queued incremental indexing, lexical retrieval, citations, and bounded RAG
  context building.
- Static Python symbols, import/dependency relationships, event subscriptions,
  architecture observations, documentation coverage, and cross-reference queries.
- Read-only reasoning foundations and MCP-shaped domain tools.

## Roadmap

- Phases 1–5 — kernel, eventing, core services, and semantic memory complete.
- Phase 6 — vision, unified memory gateway, and brain foundations complete.
- Phase 7 — reliability and software understanding in progress.
- Phase 8 — planned cognitive intelligence: hybrid retrieval, working memory,
  approval-gated planning, and provider abstractions.

## Development

Run the targeted semantic and reliability suite from the repository root:

```powershell
$env:PYTHONPATH='src'
python -m unittest -q test_semantic_intelligence test_import_graph test_binary_files test_sqlite_recovery test_stress test_recovery test_retrieval_quality test_cross_reference test_large_repository
```

See [ARCHITECTURE.md](ARCHITECTURE.md), [PROJECT_STATUS.md](PROJECT_STATUS.md),
[NEXT_TASK.md](NEXT_TASK.md), and [BENCHMARKS.md](BENCHMARKS.md) for the
current design and measured Phase 7 results.
