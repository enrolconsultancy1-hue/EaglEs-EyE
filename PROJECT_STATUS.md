# Project Status

## Current phase

Phase 7 — Reliability, Project Intelligence, and Software Understanding is in
progress.

The software-intelligence extension now includes dedicated symbol indexing,
dependency/project graph facts, project search, architecture observations,
documentation links, evolution-preserving symbol versions, and health snapshots.

Completed foundations:

- Lifecycle-safe configuration for watcher and mirror runtime state.
- SQLite knowledge store with JSON compatibility.
- Versioned queued indexing, lexical retrieval, citations, RAG context, and
  read-only reasoning/MCP domain APIs.
- Static Python symbols and relationships with cross-reference queries.
- Reliability regression suites for stress activity, restart persistence,
  binary/oversized files, rollback integrity, import graphs, retrieval quality,
  large repositories, and cross references.

Latest measured result: the targeted 10-test Phase 6–7 suite completed in
7.12 seconds. See `BENCHMARKS.md`; line coverage awaits installation of the
declared development-only `coverage` dependency.

## Known limitations

- The watcher still maps filesystem renames to delete/create lifecycle events.
- Graph analysis is intentionally Python-only and static; unresolved names are
  recorded as symbolic targets.
- Embeddings, vector search, and a network MCP server are deferred.
