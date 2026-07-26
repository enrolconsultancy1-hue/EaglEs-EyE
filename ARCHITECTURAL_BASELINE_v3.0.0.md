# EaglEs EyE Architectural Baseline v3.0.0

**Status:** FROZEN  
**Version:** 3.0.0  
**Commit:** 66c292e  
**Date:** 2026-07-26  
**Supersedes:** All prior architectural documents for the AI Twin Core

---

## Executive Summary

EaglEs EyE completed Phases 8–18, transforming from a file-watching memory
system into a **Universal AI Project Twin** — an autonomous platform that
observes, mirrors, remembers, and reasons across any software project
ecosystem through standardized connectors.

### What was accomplished

| Phase | Version | Capability |
|-------|---------|------------|
| 8 | — | AI Twin Observer Foundation — workspace identity, session recording, execution timelines, agent detection, local twin artifacts |
| 9 | — | Multi-Agent Observation — compare coding agents across 5 dimensions |
| 10 | — | Evidence-Based Cognitive Layer — causal graphs, architecture evolution, decision tracking, evidence-backed explanations |
| 11 | — | MCP Ecosystem — JSON-RPC 2.0 stdio/TCP server, tool registry, 11 domain tools |
| 12 | v2.0.0 | EaglEs EyE Desktop GUI — Mission Control with 7 views |
| 13 | v2.1.0 | Semantic Intelligence & Autonomous Awareness — embeddings, vector search, awareness signals |
| 14 | v2.2.0 | Universal Connector Framework — connector ABC, registry, SDK, manifests, plugins, validation |
| 15 | v2.3.0 | Unified Evidence & Knowledge Graph — EvidenceBus, EvidenceIngestionService, single observation pipeline |
| 16 | v2.4.0 | External Project Integration Layer — authentication, webhooks, sync engine, scheduling, metrics, GitHub connector |
| 17 | v2.5.0 | Autonomous Project Intelligence — ReasoningEngine, ConfidenceEngine, project intelligence, root cause, impact, lineage, explainable AI |
| 18 | v3.0.0 | Universal AI Project Twin — AITwinOrchestrator, TwinIntegrityValidator, UnifiedProjectTwin, UniversalTwinReport, 40 MCP tools |

**403 tests passing, zero regressions. Constitution unchanged.**

---

## Architectural Principles

### 1. Observation is passive

EaglEs EyE observes without modifying. Every connector reads without writing.
Every service records without executing. The system never stages commits,
edits files, spawns processes, or alters the watched workspace.

### 2. Conclusions are evidence-backed

Every conclusion must cite observable evidence. No hidden reasoning. No
unsupported claims. No inferred intent or undocumented motivation.

### 3. Services extend without replacement

New capabilities are added as new `Service` subclasses, never by modifying or
replacing existing services. SQLite schema changes are additive only (new
tables, nullable columns). Backward compatibility is required.

### 4. The platform is connector-driven

All external integrations plug into the Universal Connector Framework. No
connector may bypass the framework, inject data directly into the knowledge
graph, or route around the evidence pipeline.

### 5. Architecture is layered

```
MCP Clients / GUI
     ↓
MCP Transport Layer
     ↓
MCPToolService
     ↓
Domain Services (Reasoning, Intelligence, Twin)
     ↓
Knowledge Store + Knowledge Graph
     ↓
Evidence Pipeline (Connector → EvidenceBus → Ingestion)
     ↓
Connector Framework
     ↓
External Ecosystems
```

Each layer communicates only with the layer immediately below. No layer
bypasses another.

### 6. Governance is constitutional

AI_TWIN_CONSTITUTION.md is the supreme governance document. No feature,
experiment, or optimization may violate the constitution. The chain of
command is: Constitution → Roadmap → Architecture → Status → Next Task.

---

## Universal Observation Policy

**Status:** PERMANENT AND MANDATORY

Every connector SHALL implement the following methods:

| Method | Purpose |
|--------|---------|
| `discover_observation_surfaces()` | List every available authorized observation surface |
| `rank_observation_surfaces()` | Rank surfaces by evidence quality, latency, completeness, reliability |
| `select_observation_pipeline()` | Build the optimal observation pipeline automatically |
| `get_active_surfaces()` | Return currently active observation surfaces |

### Observation surface preference order

1. Native AI Twin Connector
2. MCP Server
3. Official Plugin / Extension SDK
4. Official API
5. Webhooks / Event Streams
6. Local Workspace
7. Git Repository
8. Project Files
9. Build Artifacts / Config Files / Logs / Local Databases

### Surface quality scoring

`ObservationDiscoveryEngine` computes a `SurfaceQuality` score from:

- **Quality** — data richness and structure
- **Latency** — time from event to observation
- **Completeness** — fraction of available data captured
- **Reliability** — historical success rate
- **Incremental sync capability** — ability to fetch only new/changed data

### Enforcement

Every connector MUST pass through the complete normalization pipeline:

```
Connector → Observe → Collect → Normalize → Validate → Emit → EvidenceBus → Ingestion → Knowledge Store
```

No connector may inject data directly into the Knowledge Store or bypass the
EvidenceBus. This is enforced by the base `Connector` abstract class.

---

## Universal Reasoning Policy

**Status:** PERMANENT AND MANDATORY

Every reasoning result SHALL preserve complete evidence provenance.

### Required fields

A reasoning result SHALL NEVER exist without:

| Field | Description |
|-------|-------------|
| `conclusion` | Natural language conclusion |
| `confidence` | Numeric confidence score [0.0, 1.0] |
| `supporting_evidence` | List of evidence items with citations |
| `connector_sources` | Source connector identifiers |
| `observation_surfaces` | Observation surface identifiers |
| `reasoning_trace` | Ordered steps of the reasoning process |
| `supporting_relationships` | Relationships that support the conclusion |
| `timestamp` | ISO 8601 timestamp of the result |

### Rules

1. **No hidden reasoning** — every reasoning step must appear in the
   `reasoning_trace`.
2. **No unsupported conclusions** — every conclusion must cite at least one
   evidence item or explicitly state that no evidence was found.
3. **No connector provenance discarded** — every evidence item must preserve
   its `connector_id` and `observation_surface`.
4. **Reproducibility** — given the same evidence set, the same result must be
   reproducible.

### Evidence quality assessment

Every evidence item is assessed by `ConfidenceEngine` for:

- **Citation presence** — does the item have an ID or citation?
- **Source connector** — is the originating connector identified?
- **Timestamp** — is the observation time recorded?

Missing attributes are explicitly reported (never fabricated).

---

## Permanent Service Topology

### Complete production service graph

```
EyeKernel
└── EventBus
│
├── Core Services
│   ├── ConfigService
│   ├── LoggerService
│   ├── MirrorService
│   ├── MemoryService
│   └── VisionService
│
├── Knowledge & Retrieval
│   ├── KnowledgeStoreService        — SQLite persistence (15 tables)
│   ├── KnowledgeIndexerService      — File indexing, chunking
│   ├── KnowledgeGraphService        — AST analysis + connector evidence + enhancements
│   ├── SymbolIndexerService         — Version-aware symbol extraction
│   ├── RetrievalService             — Lexical search with citations
│   ├── ContextBuilderService        — RAG context construction
│   ├── VectorSearchService          — Cosine-similarity semantic search
│   └── EmbeddingService             — Configurable embedding (disabled by default)
│
├── Intelligence & Analysis
│   ├── CrossReferenceService        — Combined graph + lexical lookup
│   ├── ArchitectureAnalyzerService  — Health/coverage observations
│   ├── DocumentationLinkService     — Documentation coverage tracking
│   ├── ArchitectureEvolutionService — Snapshot creation, structural diff
│   └── CausalGraphService           — Event relationship tracking
│
├── Observation & Recording
│   ├── WorkspaceObserverService     — Workspace identity registration
│   ├── ExecutionTimelineService     — Ordered event timelines
│   ├── SessionRecorderService       — Workspace-scoped session boundaries
│   ├── TwinBuilderService           — Local twin artifact generation
│   ├── ReplayService                — Evidence-based replay
│   ├── AgentDetectorService         — Visible-marker agent classification
│   ├── MultiAgentObservationService — Cross-agent comparison
│   ├── SemanticAwarenessService     — Event-driven pattern detection
│   ├── DecisionTrackingService      — Engineering decision records
│   └── CognitiveLayerService        — Evidence-backed explanation engine
│
├── Connector Framework
│   ├── ConnectorService             — Framework-to-kernel bridge
│   ├── ConnectorManager             — Lifecycle orchestration
│   ├── ConnectorRegistry            — Thread-safe connector registry
│   ├── EvidenceIngestionService     — EvidenceBus → KnowledgeStore
│   ├── ConnectorSchedulerService    — Background periodic sync
│   └── connector plugins:
│       ├── FilesystemConnector      — Walk-based file observation
│       ├── GitConnector             — Read-only Git queries
│       ├── GitHubConnector          — REST API project system integration
│       └── MockConnector            — Test/development reference
│
├── Reasoning & Intelligence (Phase 17)
│   ├── ConfidenceEngine             — Evidence quality scoring
│   ├── ReasoningEngine              — Single entry point for all reasoning
│   ├── ProjectIntelligenceEngine    — Health, blockers, bottlenecks, stale, drift
│   ├── RootCauseAnalysisService     — What/why/evidence/confidence
│   ├── ImpactAnalysisService        — Files, components, docs, connectors
│   ├── DecisionLineageService       — Decision → evidence → observation → source
│   └── ExplainableAIService         — Why/how/evidence/knowledge/sources
│
├── AI Twin Services (Phase 18)
│   ├── AITwinOrchestrator           — Service coordination, 8 Dashboard APIs
│   ├── TwinIntegrityValidator       — 6 consistency checks
│   ├── UnifiedProjectTwin           — Single coherent project representation
│   └── UniversalTwinReport          — Complete evidence-backed AI Twin Report
│
└── MCP Layer
    ├── MCPServer                    — JSON-RPC 2.0 protocol handler
    ├── ToolRegistry                 — Decorator-based tool registration
    ├── MCPToolService               — 40 domain tools
    └── Transports
        ├── transport_stdio          — Line-delimited JSON-RPC over stdio
        └── transport_tcp            — Localhost-only TCP socket (disabled by default)
```

### Service registration order

Services are registered in `build_mcp_kernel()` in dependency order:

```
KnowledgeStoreService → SymbolIndexerService → KnowledgeGraphService →
KnowledgeIndexerService → RetrievalService → ContextBuilderService →
CrossReferenceService → ArchitectureAnalyzerService → DocumentationLinkService →
WorkspaceObserverService → ExecutionTimelineService → SessionRecorderService →
CausalGraphService → ArchitectureEvolutionService → DecisionTrackingService →
CognitiveLayerService → EmbeddingService → VectorSearchService →
SemanticAwarenessService → ConnectorService → EvidenceIngestionService →
ConnectorSchedulerService → ConfidenceEngine → ReasoningEngine →
ProjectIntelligenceEngine → RootCauseAnalysisService → ImpactAnalysisService →
DecisionLineageService → ExplainableAIService → AITwinOrchestrator →
TwinIntegrityValidator → UnifiedProjectTwin → UniversalTwinReport →
MCPToolService
```

---

## Evidence Flow

### Complete pipeline

```
External Ecosystem
     ↓
Connector.observe() / .collect()
     ↓
Connector.normalize() —→ canonical Evidence model
     ↓
Connector.validate() —→ CapabilityValidator, PermissionValidator
     ↓
Connector.emit() —→ EvidenceBus
     ↓
EvidenceBus.publish() —→ subscribers
     ↓
EvidenceIngestionService.ingest()
     ↓
KnowledgeStoreService —→ events, observations, relationships tables
     ↓
KnowledgeGraphService —→ AST analysis + connector evidence relationships
     ↓
RetrievalService / VectorSearchService —→ lexical / semantic retrieval
     ↓
ReasoningEngine —→ reasoning, confidence, explanation
     ↓
MCPToolService —→ tool responses
     ↓
MCP Transport —→ JSON-RPC 2.0 response
```

### Data flow characteristics

- **Append-only**: events, chunks, and observations are never deleted or
  overwritten. Prior versions become inactive rather than erased.
- **Immutable evidence**: once recorded, evidence is never modified.
- **Read-only queries**: all retrieval, reasoning, and explanation methods are
  read-only. No side effects.
- **Deprecation-safe**: pre-connector observer services (GitObserverService,
  EngineeringEvidenceService, ProcessObserverService) remain importable and
  callable with deprecation warnings, routing through the connector framework.

---

## AI Twin Lifecycle

### From observation to reasoning

```
1. CONNECTOR DISCOVERY
   └── connector.discover_observation_surfaces()
       └── rank by quality → select optimal pipeline

2. OBSERVATION
   └── connector.observe() / .collect()
       └── normalize → validate → emit

3. EVIDENCE BUS
   └── EvidenceBus.publish(evidence)
       └── EvidenceIngestionService receives
           └── KnowledgeStoreService persists

4. KNOWLEDGE GRAPH
   └── KnowledgeGraphService.ingest_connector_evidence()
       └── creates relationships, propagates confidence

5. STORAGE & INDEXING
   └── KnowledgeStoreService (SQLite)
       └── events, observations, documents, chunks, symbols, relationships

6. RETRIEVAL
   └── RetrievalService (lexical)
   └── VectorSearchService (semantic, if enabled)

7. REASONING
   └── ReasoningEngine (single entry point)
       ├── reason_cross_connector
       ├── reason_dependencies
       ├── reason_timeline
       ├── reason_state_transitions
       ├── reason_relationships
       ├── reason_evidence_correlation
       └── reason_historical

8. INTELLIGENCE
   └── ProjectIntelligenceEngine
       ├── project_health
       ├── detect_blockers
       ├── detect_bottlenecks
       ├── detect_stale_work
       └── detect_architecture_drift

9. ANALYSIS
   ├── RootCauseAnalysisService.analyze()
   ├── ImpactAnalysisService.analyze()
   └── DecisionLineageService.trace()

10. EXPLANATION
    └── ExplainableAIService.explain()
        ├── Gather facts
        ├── Derive relationships
        └── Build explanation (why + how + evidence)

11. CONFIDENCE
    └── ConfidenceEngine
        ├── score_evidence()
        ├── score_relationships()
        └── aggregate()

12. AI TWIN ORCHESTRATION
    └── AITwinOrchestrator
        ├── twin_status / twin_health
        ├── connector_status_summary
        ├── observation_status / reasoning_status
        ├── sync_status / evidence_metrics
        └── project_health

13. INTEGRITY VALIDATION
    └── TwinIntegrityValidator.check_all()
        ├── KG consistency
        ├── Evidence consistency
        ├── Relationship consistency
        ├── Connector consistency
        ├── Sync consistency
        └── Provenance integrity

14. UNIFIED REPRESENTATION
    └── UnifiedProjectTwin
        ├── overview
        ├── project_summary
        ├── connector_twin
        └── reasoning_twin

15. REPORT
    └── UniversalTwinReport.generate()
        ├── Overview, health, integrity, status
        ├── Blockers, bottlenecks, stale work, drift
        └── Complete evidence-backed report

16. TOOL RESPONSE
    └── MCPToolService.call_tool()
        └── JSON-RPC 2.0 response via MCP transport
```

---

## Acceptance Criteria

### v3.0.0 official acceptance statement

> Given any supported project ecosystem and appropriate authorization, I can
> discover the richest authorized observation surfaces, continuously
> synchronize evidence, maintain a unified project knowledge graph, reason
> across all collected evidence, explain every conclusion with complete
> provenance, and present a single coherent AI Twin of the project without
> requiring changes to the core architecture.

### Verification

| Criterion | Status |
|-----------|--------|
| Discover observation surfaces | ✅ Universal Observation Policy (4 methods on every connector) |
| Continuously synchronize evidence | ✅ SyncEngine + ConnectorSchedulerService |
| Unified project knowledge graph | ✅ KnowledgeGraphService with AST + connector evidence |
| Reason across all evidence | ✅ ReasoningEngine (7 methods, cross-connector) |
| Explain with complete provenance | ✅ Universal Reasoning Policy (8 required fields) |
| Single coherent AI Twin | ✅ AITwinOrchestrator + UnifiedProjectTwin + UniversalTwinReport |
| No core architecture changes | ✅ Platform independence proven (GitHub connector) |
| **403 tests passing** | ✅ Zero regressions |

---

## Architecture Freeze Policy

### Declaration

The **AI Twin Core** — comprising all services, frameworks, policies, and
infrastructure listed below — is **frozen as of v3.0.0** and shall not be
redesigned, replaced, or fundamentally altered unless a critical architectural
defect is discovered and approved through an architectural exception process.

### Frozen components

| Component | File / Module |
|-----------|---------------|
| Kernel | `core/kernel.py` |
| EventBus | `core/event_bus.py` |
| Universal Connector Framework | `connectors/` (all modules) |
| Universal Observation Policy | `connectors/observation_discovery.py` |
| Evidence Pipeline | `connectors/evidence_bus.py` |
| EvidenceBus | `connectors/evidence_bus.py` |
| EvidenceIngestionService | `services/evidence_ingestion_service.py` |
| Knowledge Store | `services/knowledge_store_service.py` |
| Knowledge Graph | `services/knowledge_graph_service.py` |
| Synchronization Engine | `connectors/sync.py` |
| Reasoning Engine | `services/reasoning_engine.py` |
| Project Intelligence Engine | `services/project_intelligence_engine.py` |
| Root Cause Analysis | `services/root_cause_analysis_service.py` |
| Impact Analysis | `services/impact_analysis_service.py` |
| Decision Lineage | `services/decision_lineage_service.py` |
| Confidence Engine | `services/confidence_engine.py` |
| Explainable AI | `services/explainable_ai_service.py` |
| AI Twin Orchestrator | `services/ai_twin_orchestrator.py` |
| Twin Integrity Validator | `services/twin_integrity_validator.py` |
| Universal Twin Report | `services/universal_twin_report.py` |
| MCP Core | `mcp/` (server, registry, transports) |
| AI Twin Core Architecture | `ARCHITECTURAL_BASELINE_v3.0.0.md` |
| Universal Observation Policy | (this document) |
| Universal Reasoning Policy | (this document) |

### Exception process

A frozen component may only be modified if:

1. A critical architectural defect is discovered that cannot be solved by
   adding a new extension.
2. An Architectural Exception Request is submitted documenting the defect, the
   proposed change, and why extension is insufficient.
3. The exception is approved by architectural review.
4. Backward compatibility is maintained (existing tests continue to pass).

### What freezing means

- **No redesign**: do not rewrite frozen components.
- **No replacement**: do not supersede frozen components with alternatives.
- **No fundamental alteration**: do not change the core contract, interface,
  or behavior of frozen components.
- **Extension is the only path**: add new `Service` subclasses, new connector
  plugins, new MCP tools, and new capabilities on top of the frozen core.

---

## Extension Rules

### How to extend without redesigning

#### 1. New connectors

Create a new connector plugin in `connectors/plugins/` that extends the base
`Connector` class. Follow the Universal Observation Policy. Route through the
evidence pipeline. No core changes required.

#### 2. New reasoning capabilities

Add new methods to existing reasoning services or create new sub-services that
consume ReasoningEngine output. Register in `build_mcp_kernel()` before
`MCPToolService`.

#### 3. New MCP tools

Add tool definitions and handlers to `MCPToolService.list_tools()` and
`MCPToolService.call_tool()`. Preserve all existing tools.

#### 4. New integrations

Integrate through the Connector Framework only. No direct kernel access.
No bypassing the Evidence Pipeline.

#### 5. New GUI views

Add new templates to `gui/templates/` that communicate exclusively through the
MCP layer. No direct EyeKernel import, no SQLite writes, no workspace mutation.

#### 6. New persistence

Add new SQLite tables (never modify existing ones) or extend with nullable
columns (never make existing columns non-nullable). Data migration must be
backward compatible.

### Forbidden patterns

| Pattern | Why |
|---------|-----|
| Modifying a frozen service | Violates freeze policy |
| Bypassing the connector framework | Circumvents evidence pipeline |
| Writing directly to Knowledge Store from a connector | Circumvents validation |
| Replacing an existing service | Breaks backward compatibility |
| Adding platform-specific logic to core | Violates separation of concerns |
| Modifying the Constitution | Constitution is frozen |
| Removing or renaming existing MCP tools | Breaks client compatibility |

---

## Contributor Guidance

### Getting started

1. Read `AI_TWIN_CONSTITUTION.md` — the supreme governance document.
2. Read `ARCHITECTURAL_BASELINE_v3.0.0.md` — the permanent architecture.
3. Read `ARCHITECTURE.md` — detailed implementation documentation.
4. Read `ROADMAP.md` — the capability-driven product roadmap.

### Core rules

1. **Never modify a frozen component.** Add new services instead.
2. **Never bypass the connector framework.** Every external integration flows
   through `Connector` → `EvidenceBus` → `EvidenceIngestionService` →
   `KnowledgeStore`.
3. **Never hide reasoning.** Every conclusion must cite evidence and preserve
   provenance per the Universal Reasoning Policy.
4. **Never break backward compatibility.** Existing tests must continue to
   pass. Existing tools must continue to work.
5. **Never modify the Constitution.** It is frozen permanently.

### Development workflow

1. Architecture Validation Gate — document and approve the architecture before
   implementation.
2. Implementation — extend existing services, never modify frozen ones.
3. Tests — add tests for new capabilities. Run full regression suite.
4. Documentation — update `ARCHITECTURE.md`, `PROJECT_STATUS.md`,
   `NEXT_TASK.md`, `CHANGELOG.md`.
5. Release Gate — verify tests, docs, architecture, and constitution.
6. Commit and tag — `v3.x.y` with descriptive message.

### Testing requirements

- All new capabilities must have tests.
- The full regression suite must pass before release.
- Pre-existing test failures (e.g., 5 MCP stdio exclusions) must be documented.
- Universal Observation Policy compliance must be tested.
- Universal Reasoning Policy compliance must be tested.

### Documentation requirements

Every release must update:

- `ARCHITECTURE.md` — add new architecture section
- `PROJECT_STATUS.md` — update current phase/version
- `NEXT_TASK.md` — link to product roadmap
- `CHANGELOG.md` — document all changes
- `ROADMAP.md` — update capability roadmap

The Constitution (`AI_TWIN_CONSTITUTION.md`) and the Architectural Baseline
(`ARCHITECTURAL_BASELINE_v3.0.0.md`) shall never be modified.

### Governance chain

```
AI_TWIN_CONSTITUTION.md (frozen)
         ↓
ARCHITECTURAL_BASELINE_v3.0.0.md (frozen)
         ↓
ROADMAP.md (capability-driven)
         ↓
ARCHITECTURE.md (detailed implementation docs)
         ↓
PROJECT_STATUS.md (current state)
         ↓
NEXT_TASK.md (immediate next step)
```

No implementation decision shall override a higher-level governance document.

---

*This document is the permanent architectural reference for EaglEs EyE.
It shall never be modified. Future releases shall extend the platform
according to the Extension Rules in this document.*
