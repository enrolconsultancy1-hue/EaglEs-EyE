# Changelog

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

