# EaglEs EyE – AI Twin Observer Constitution

## Permanent engineering constitution

> Read this document completely before making code changes.

This document is the permanent engineering constitution of EaglEs EyE.

Do not rewrite the project, replace working components, or introduce breaking
architectural changes. Observe the existing architecture, understand it, extend
it, preserve it, and strengthen it. Every implementation must respect the
project's long-term mission.

## Project mission

EaglEs EyE reconstructs an evidence-based digital twin of any AI coding session
by continuously observing every artifact the agent produces: files it creates or
modifies, tests it executes, builds it performs, Git actions it records, and
documented plans, design decisions, or reasoning artifacts it leaves within a
local workspace.

The result is a replayable, searchable, auditable, and continuously evolving
engineering history grounded entirely in observable evidence.

## One-line vision

**Watch. Understand. Reconstruct. Twin.**

## The golden rule

Every new feature must strengthen EaglEs EyE's ability to:

- Observe
- Understand
- Reconstruct
- Twin

AI coding sessions through observable evidence. If a feature does not advance
this mission, reconsider it, defer it, or implement it as an optional extension.

## What EaglEs EyE is

EaglEs EyE is not another coding assistant, RAG application, or AI IDE. It is
an **AI Twin Observer**: it watches AI software engineering from beginning to
end and reconstructs what happened using observable evidence.

## Observable evidence

Everything must be based only on observable artifacts, including:

- filesystem events; created, modified, deleted, and renamed files
- source code, documentation, plans, architecture documents, TODO files,
  `NEXT_TASK.md`, `PROJECT_STATUS.md`, and `README.md`
- Git commits, branches, and tags
- build logs, compiler output, runtime logs, test execution, benchmark reports,
  and configuration
- MCP interactions and terminal output, where available

Never claim access to hidden model reasoning. If an AI explicitly writes its
reasoning into the workspace, that file is observable evidence.

## Digital twin

For every watched workspace, EaglEs EyE should gradually build an evidence-based
AI Twin containing:

- execution timeline and event history
- knowledge, symbol, dependency, and project graphs
- architecture evolution, retrieval index, and reflections
- replay history and engineering audit trail

Everything remains local by default.

## Long-term architecture

```text
Observer Layer
      ↓
Knowledge Layer
      ↓
Understanding Layer
      ↓
Reasoning Layer
      ↓
AI Twin Layer
```

### Observer layer

The observer is the heart of the system. It should eventually observe the
filesystem, Git, builds, tests, documentation, project evolution,
configuration, logs, terminal activity, and MCP tools where available.

Observation must remain passive: it must never interfere with the watched
workspace unless explicitly instructed.

### Knowledge layer

Responsible for deterministic, reproducible indexing, versioning, chunking,
storage, retrieval, and citations.

### Understanding layer

Responsible for understanding software: symbols, imports, inheritance, function
calls, dependency and project graphs, documentation links, and architecture
evolution.

### Reasoning layer

Reasoning must reference observable evidence. Do not invent facts or fabricate
explanations. Every conclusion must be traceable to files, events, Git history,
tests, documentation, or graphs.

### AI Twin layer

The long-term objective is a replayable engineering twin for every coding
session, for example:

```text
Twins/
  Workspace_A/
    Session_001/
      timeline.json
      events.json
      symbols.json
      dependency_graph.json
      project_graph.json
      git.json
      tests.json
      summary.md
      replay.md
      metrics.json
```

Everything must be reproducible.

## Current architecture

Respect all existing services; extend them rather than replacing them. Existing
services include, without limitation:

- `WatcherService`, `MirrorService`, and `MemoryService`
- `SemanticMemoryService`, `KnowledgeStoreService`, and
  `KnowledgeIndexerService`
- `RetrievalService`, `ReasoningService`, and `KnowledgeGraphService`
- `ReflectionService`, `ContextBuilderService`, and `MemoryGatewayService`
- `MCPToolService` and all existing tests

## Implementation principles

Always:

- preserve backwards compatibility
- prefer extension over replacement
- maintain service boundaries and modularity
- write regression tests and update documentation
- preserve SQLite and JSON compatibility
- preserve existing APIs whenever practical

## Development order

Prefer this order:

1. Observation
2. Timeline
3. Session reconstruction
4. Knowledge
5. Graph
6. Understanding
7. Replay
8. Comparison
9. AI Twin

Not the reverse.

## Never do these

Do not replace working architecture, remove services without justification,
redesign the kernel unless absolutely required, introduce unnecessary
frameworks, make the project cloud-dependent, claim hidden AI reasoning, or
break replayability.

## Success

The project succeeds when it can answer questions such as:

- “What happened yesterday?”
- “Replay the implementation of `RetrievalService`.”
- “Show every test executed before the last commit.”
- “Compare Claude Code and Codex implementing the same feature.”
- “Why did the architecture change?”
- “What evidence supports this conclusion?”

Every answer must be backed by observable evidence.

## Engineering checkpoint

Before implementing any feature, ask:

> Does this improve EaglEs EyE's ability to Observe, Understand, Reconstruct,
> or Twin AI coding sessions?

If the answer is no, stop and reconsider. Choose a design that supports the
mission. This constitution has higher priority than convenience, shortcuts, or
unnecessary redesigns. Protect the architecture, preserve progress, and build
toward the AI Twin Observer.
