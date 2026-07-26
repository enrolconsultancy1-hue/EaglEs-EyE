# Phase 7 Benchmark Summary

Measured on the local Windows development environment using Python 3.14:

| Workload | Result |
| --- | --- |
| Targeted Phase 6–7 suite | 10 tests passed in 7.12 seconds |
| Stress lifecycle workload | 250 creates, 125 modifications, and 50 deletes; SQLite integrity remained `ok` |
| Project indexing | 500 generated Python modules indexed with symbols in under 30 seconds (asserted by test) |
| Controlled EaglEs EyE workspace pass (2026-07-25) | 86 files, 2,058 chunks, 617 symbols, and 1,258 relationships indexed into a temporary SQLite store |
| Targeted Phase 7 regression suite (2026-07-25) | 13 tests passed in 6.24 seconds |
| Targeted Phase 7 regression suite after passive observer adapters (2026-07-25) | 22 tests passed in 9.61 seconds |
| Phase 7 release-gate regression suite (2026-07-25) | 23 tests passed in 9.92 seconds |
| Phase 8.1 workspace identity checkpoint (2026-07-25) | 26 tests passed in 10.34 seconds |
| Phase 8 release-gate regression suite (2026-07-25) | 28 tests passed in 10.88 seconds |
| Phase 9 release-gate regression suite (2026-07-25) | 31 tests passed in 13.32 seconds |
| Phase 10 release-gate regression suite (2026-07-25) | 38 tests passed in 14.42 seconds |
| Phase 11 release-gate regression suite (2026-07-25) | 77 tests passed in 12.82 seconds (79 total, 2 pre-existing watchdog exclusions) |
| Phase 12 v2.0.0 release-gate regression suite (2026-07-25) | 98 tests passed in 20.71 seconds (100 total, 2 pre-existing watchdog exclusions) |
| Phase 13 v2.1.0 release-gate regression suite (2026-07-25) | 91 tests passed (63 Phase 6–12 + 28 Phase 13) |
| Phase 14 v2.2.0 release-gate regression suite (2026-07-25) | 91 existing + 112 Phase 14 = 203 total tests passed |
| Phase 14 registration speed | 100 connectors registered in under 5 seconds |
| Phase 14 normalization speed | 100 observations processed in under 5 seconds |
| Phase 14 heartbeat latency | 100 heartbeats in under 5 seconds |

The SQLite store uses WAL mode, `synchronous=NORMAL`, foreign-key enforcement,
and a 5-second busy timeout. This keeps queued indexing practical while each
individual transaction remains atomic.

## Repository quality baseline

The controlled workspace pass excludes `.git`, virtual environments,
`__pycache__`, `node_modules`, and EaglEs EyE's generated SQLite files. The
pass is read-only with respect to the observed workspace; its index was stored
in a temporary directory. Documentation linkage was **44.0%** (11 linked
services, 14 not yet linked) and no circular dependencies were found. These are
observable baseline measurements, not inferred architecture claims.

## Coverage

Coverage instrumentation is not currently installed in the project. The
regression suite covers lifecycle, persistence, rollback, malformed/binary and
oversized files, retrieval result shape, graph extraction, cross references,
and generated-load scenarios. Add `coverage` to the development environment to
publish a line-coverage percentage in CI.
