# Next Task

The foundational roadmap (Phases 8–18) is complete. **v3.0.0 is the permanent
architectural baseline.** The AI Twin Core is frozen.

## Current State

- **Version:** v3.1-dev (Project Twin Discovery Connector)
- **Tests:** 431 passing (403 existing + 28 new), zero regressions
- **MCP Tools:** 41 (40 existing + discover_project_twin)
- **Architecture:** Frozen per [ARCHITECTURAL_BASELINE_v3.0.0.md](ARCHITECTURAL_BASELINE_v3.0.0.md)

## What's Next

Future development follows the **capability-driven product roadmap** in
[ROADMAP.md](ROADMAP.md#product-roadmap--capability-driven).

### Next candidate: v3.1 — Connector Expansion

Extend the Connector Framework to additional ecosystems:

- ClickUp, Jira, Notion, Slack
- Codex, Cursor, Claude Desktop, Windsurf
- VS Code, JetBrains

Every new connector MUST comply with:

- Universal Connector Framework
- Universal Observation Policy
- Universal Reasoning Policy

**No core architecture changes.**

### Engineering rules

- Architecture Validation Gate remains mandatory
- Universal Observation Policy remains mandatory
- Universal Reasoning Policy remains mandatory
- Release Gate remains mandatory
- Backward compatibility is required
- New capabilities extend the architecture
- The AI Twin Core shall not be redesigned without an approved architectural
  exception

Await explicit authorization before beginning any implementation work.
