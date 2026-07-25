# Phase 7 Benchmark Summary

Measured on the local Windows development environment using Python 3.14:

| Workload | Result |
| --- | --- |
| Targeted Phase 6–7 suite | 10 tests passed in 7.12 seconds |
| Stress lifecycle workload | 250 creates, 125 modifications, and 50 deletes; SQLite integrity remained `ok` |
| Project indexing | 500 generated Python modules indexed with symbols in under 30 seconds (asserted by test) |

The SQLite store uses WAL mode, `synchronous=NORMAL`, foreign-key enforcement,
and a 5-second busy timeout. This keeps queued indexing practical while each
individual transaction remains atomic.

## Coverage

Coverage instrumentation is not currently installed in the project. The
regression suite covers lifecycle, persistence, rollback, malformed/binary and
oversized files, retrieval result shape, graph extraction, cross references,
and generated-load scenarios. Add `coverage` to the development environment to
publish a line-coverage percentage in CI.
