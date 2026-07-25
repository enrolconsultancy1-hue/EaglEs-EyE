# EaglEs EyE

> A modular cognitive AI kernel that observes, remembers, reflects, reasons,
> and is evolving into a safe software-understanding engine.

## AI contributor first read

Before making changes, AI contributors must read the
[AI Twin Observer Constitution](AI_TWIN_CONSTITUTION.md). The root
[AGENTS.md](AGENTS.md) provides the required document-reading order.

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
- Deterministic, passive workspace indexing that reuses the versioned evidence
  pipeline while excluding common VCS and runtime directories.
- Evidence-only timelines and session summaries reconstructed from durable event
  records, with stable event citations.
- Replayable session reconstructions built from those cited timeline events.
- Passive recording of supplied Git, build, test, and terminal evidence for
  timeline and replay use.
- Read-only Git snapshots of branch, revision, and working-tree status.
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

The [AI Twin Observer Constitution](AI_TWIN_CONSTITUTION.md) is the project's
permanent engineering guide. See [ARCHITECTURE.md](ARCHITECTURE.md),
[PROJECT_STATUS.md](PROJECT_STATUS.md), [NEXT_TASK.md](NEXT_TASK.md), and
[BENCHMARKS.md](BENCHMARKS.md) for the current design and measured Phase 7
results.
