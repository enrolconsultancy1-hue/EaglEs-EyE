"""MCP-shaped domain tools without binding the kernel to an MCP server package."""

from services.service import Service


class MCPToolService(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.retrieval = None
        self.context = None
        self.indexer = None
        self.store = None
        self.cross_reference = None
        self.causal = None
        self.evolution = None
        self.decisions = None
        self.cognitive = None
        self.vector_search = None
        self.awareness = None
        self.connector = None
        self.evidence_ingestion = None
        self.scheduler = None
        self.reasoning = None
        self.project_intelligence = None
        self.root_cause = None
        self.impact = None
        self.decision_lineage = None
        self.confidence = None
        self.explainable = None
        self.ai_twin = None
        self.twin_validator = None
        self.unified_twin = None
        self.twin_report = None
        self.project_twin = None

    def start(self):
        super().start()
        self.retrieval = self.kernel.get_service("RetrievalService")
        self.context = self.kernel.get_service("ContextBuilderService")
        self.indexer = self.kernel.get_service("KnowledgeIndexerService")
        self.store = self.kernel.get_service("KnowledgeStoreService")
        self.cross_reference = self.kernel.get_service("CrossReferenceService")
        self.causal = self.kernel.get_service("CausalGraphService")
        self.evolution = self.kernel.get_service("ArchitectureEvolutionService")
        self.decisions = self.kernel.get_service("DecisionTrackingService")
        self.cognitive = self.kernel.get_service("CognitiveLayerService")
        self.vector_search = self.kernel.get_service("VectorSearchService")
        self.awareness = self.kernel.get_service("SemanticAwarenessService")
        self.connector = self.kernel.get_service("ConnectorService")
        self.evidence_ingestion = self.kernel.get_service("EvidenceIngestionService")
        self.scheduler = self.kernel.get_service("ConnectorSchedulerService")
        self.reasoning = self.kernel.get_service("ReasoningEngine")
        self.project_intelligence = self.kernel.get_service("ProjectIntelligenceEngine")
        self.root_cause = self.kernel.get_service("RootCauseAnalysisService")
        self.impact = self.kernel.get_service("ImpactAnalysisService")
        self.decision_lineage = self.kernel.get_service("DecisionLineageService")
        self.confidence = self.kernel.get_service("ConfidenceEngine")
        self.explainable = self.kernel.get_service("ExplainableAIService")
        self.ai_twin = self.kernel.get_service("AITwinOrchestrator")
        self.twin_validator = self.kernel.get_service("TwinIntegrityValidator")
        self.unified_twin = self.kernel.get_service("UnifiedProjectTwin")
        self.twin_report = self.kernel.get_service("UniversalTwinReport")
        self.project_twin = self.kernel.get_service("ProjectTwinDiscoveryService")
        print("[MCP TOOLS] Ready.")

    def list_tools(self):
        return [
            {"name": "search_memory", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "category": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["query"]},
             "description": "Search indexed memory chunks by query text."},
            {"name": "build_context", "inputSchema": {"type": "object", "properties": {"question": {"type": "string"}, "max_chars": {"type": "integer"}}, "required": ["question"]},
             "description": "Build RAG context for a question."},
            {"name": "get_document", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
             "description": "Retrieve a stored document by path."},
            {"name": "get_recent_events", "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer"}}},
             "description": "List recent filesystem events."},
            {"name": "reindex_memory", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
             "description": "Re-index a file path into memory."},
            {"name": "cross_reference", "inputSchema": {"type": "object", "properties": {"subject": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["subject"]},
             "description": "Cross-reference a symbol or subject across the knowledge graph."},
            {"name": "explain_change", "inputSchema": {"type": "object", "properties": {"entity_path": {"type": "string"}, "workspace_id": {"type": "string"}, "session_id": {"type": "string"}}, "required": ["entity_path"]},
             "description": "Produce an evidence-backed explanation for why a file or entity changed."},
            {"name": "get_causal_chain", "inputSchema": {"type": "object", "properties": {"event_id": {"type": "string"}, "direction": {"type": "string", "enum": ["forward", "backward"]}}, "required": ["event_id"]},
             "description": "Trace causal chains forward or backward from an event."},
            {"name": "compare_snapshots", "inputSchema": {"type": "object", "properties": {"snapshot_id_a": {"type": "string"}, "snapshot_id_b": {"type": "string"}}, "required": ["snapshot_id_a", "snapshot_id_b"]},
             "description": "Compare two architecture snapshots and report structural differences."},
            {"name": "list_decisions", "inputSchema": {"type": "object", "properties": {"workspace_id": {"type": "string"}, "session_id": {"type": "string"}}},
             "description": "List engineering decision records, optionally filtered by workspace or session."},
            {"name": "get_decision", "inputSchema": {"type": "object", "properties": {"decision_id": {"type": "string"}}, "required": ["decision_id"]},
             "description": "Retrieve a single engineering decision record by ID."},
            {"name": "search_semantic", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "table": {"type": "string", "enum": ["chunks", "symbols", "events", "decision_records"]}, "top_k": {"type": "integer"}}, "required": ["query"]},
             "description": "Semantic vector search across embedded entities."},
            {"name": "get_similar", "inputSchema": {"type": "object", "properties": {"row_id": {"type": "integer"}, "table": {"type": "string", "enum": ["chunks", "symbols", "events", "decision_records"]}, "top_k": {"type": "integer"}}, "required": ["row_id", "table"]},
             "description": "Find semantically similar items to a given entity by ID."},
            {"name": "get_awareness_signals", "inputSchema": {"type": "object", "properties": {"signal_type": {"type": "string"}, "limit": {"type": "integer"}}},
             "description": "List recent semantic awareness signals."},
            {"name": "list_connectors", "inputSchema": {"type": "object", "properties": {}},
             "description": "List all registered connectors and their status."},
            {"name": "get_connector_status", "inputSchema": {"type": "object", "properties": {"connector_id": {"type": "string"}}, "required": ["connector_id"]},
             "description": "Get detailed status for a specific connector."},
            {"name": "get_connector_health_all", "inputSchema": {"type": "object", "properties": {}},
             "description": "Get health status for all registered connectors."},
            {"name": "get_evidence_stats", "inputSchema": {"type": "object", "properties": {}},
             "description": "Get evidence ingestion pipeline statistics."},
            {"name": "get_connector_evidence", "inputSchema": {"type": "object", "properties": {"connector_id": {"type": "string"}, "count": {"type": "integer"}}, "required": ["connector_id"]},
             "description": "Trigger evidence collection from a connector and ingest into the knowledge store."},
            {"name": "github_connector_status", "inputSchema": {"type": "object", "properties": {"connector_id": {"type": "string", "default": "github"}}, "required": []},
             "description": "Get detailed status of the GitHub connector."},
            {"name": "connector_sync", "inputSchema": {"type": "object", "properties": {"connector_id": {"type": "string"}}, "required": ["connector_id"]},
             "description": "Trigger manual synchronization for a connector."},
            {"name": "connector_metrics", "inputSchema": {"type": "object", "properties": {"connector_id": {"type": "string"}}, "required": []},
             "description": "Get performance metrics for a connector."},
            {"name": "connector_last_sync", "inputSchema": {"type": "object", "properties": {"connector_id": {"type": "string"}}, "required": ["connector_id"]},
             "description": "Get the last synchronization time for a connector."},
            {"name": "connector_health_details", "inputSchema": {"type": "object", "properties": {"connector_id": {"type": "string"}}, "required": []},
             "description": "Get detailed health information for all or a specific connector."},
            {"name": "explain_project_state", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "path": {"type": "string"}, "workspace_id": {"type": "string"}, "session_id": {"type": "string"}}, "required": ["query"]},
             "description": "Explain project state with why, how, supporting evidence, and connector sources."},
            {"name": "analyze_project_risk", "inputSchema": {"type": "object", "properties": {"workspace_id": {"type": "string"}}},
             "description": "Analyze project risks including blockers, bottlenecks, stale work, and architecture drift."},
            {"name": "root_cause_analysis", "inputSchema": {"type": "object", "properties": {"issue": {"type": "string"}, "path": {"type": "string"}, "session_id": {"type": "string"}}, "required": ["issue"]},
             "description": "Determine root cause for an issue with evidence citations and confidence score."},
            {"name": "impact_analysis", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
             "description": "Determine files, components, documentation, and connectors affected by a change."},
            {"name": "project_health", "inputSchema": {"type": "object", "properties": {"workspace_id": {"type": "string"}}},
             "description": "Get project health assessment with confidence score and evidence."},
            {"name": "reasoning_trace", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "mode": {"type": "string", "enum": ["cross_connector", "dependencies", "timeline", "evidence_correlation", "historical"]}}, "required": ["query", "mode"]},
             "description": "Execute a reasoning trace across connectors, dependencies, timeline, or evidence correlation."},
            {"name": "evidence_lineage", "inputSchema": {"type": "object", "properties": {"decision_id": {"type": "string"}, "workspace_id": {"type": "string"}, "session_id": {"type": "string"}}, "required": []},
             "description": "Trace decision lineage from decision ID or list all lineages filtered by workspace/session."},
            {"name": "dependency_graph", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "depth": {"type": "integer", "default": 2}}, "required": ["path"]},
             "description": "Analyze dependencies for a given path with confidence propagation."},
            {"name": "ai_twin_status", "inputSchema": {"type": "object", "properties": {}},
             "description": "Get overall AI Twin status with state, confidence, and evidence counts."},
            {"name": "ai_twin_health", "inputSchema": {"type": "object", "properties": {}},
             "description": "Get AI Twin health assessment with health status and confidence."},
            {"name": "ai_twin_integrity", "inputSchema": {"type": "object", "properties": {"all": {"type": "boolean"}}},
             "description": "Run integrity checks on KG, evidence, relationships, connectors, sync, and provenance."},
            {"name": "ai_twin_overview", "inputSchema": {"type": "object", "properties": {}},
             "description": "Get a unified overview of the AI Twin covering all integrated data sources."},
            {"name": "ai_twin_summary", "inputSchema": {"type": "object", "properties": {}},
             "description": "Get a quick summary of AI Twin health, status, and integrity."},
            {"name": "ai_twin_connectors", "inputSchema": {"type": "object", "properties": {}},
             "description": "Get connector twin status across all registered connectors."},
            {"name": "ai_twin_reasoning", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "mode": {"type": "string", "enum": ["cross_connector", "dependencies", "timeline", "historical", "evidence_correlation"]}}},
             "description": "Execute reasoning through the unified AI Twin interface."},
            {"name": "ai_twin_report", "inputSchema": {"type": "object", "properties": {"workspace_id": {"type": "string"}}},
             "description": "Generate a complete, evidence-backed Universal AI Twin Report."},
            {"name": "discover_project_twin", "inputSchema": {"type": "object", "properties": {"project_path": {"type": "string"}}, "required": ["project_path"]},
             "description": "Discover a local project folder and create a Project Twin with identity, stack, dependencies, and repository detection."},
        ]

    def call_tool(self, name, arguments):
        arguments = arguments or {}
        if name == "search_memory":
            return {"results": self.retrieval.search(arguments.get("query", ""), arguments.get("category"), arguments.get("limit", 10))}
        if name == "build_context":
            return {"context": self.context.build_rag_context(arguments.get("question", ""), arguments.get("max_chars", 6000))}
        if name == "get_document":
            return {"document": self.store.get_document(arguments.get("path", ""))}
        if name == "get_recent_events":
            return {"events": self.store.recent_events(arguments.get("limit", 10))}
        if name == "reindex_memory":
            path = arguments.get("path")
            if not path:
                return {"error": "path is required"}
            self.indexer.reindex_path(path)
            return {"accepted": True, "path": path}
        if name == "cross_reference":
            if not self.cross_reference:
                return {"error": "cross-reference service is unavailable"}
            return self.cross_reference.find(arguments.get("subject", ""), arguments.get("limit", 20))
        if name == "explain_change":
            if not self.cognitive:
                return {"error": "CognitiveLayerService is unavailable"}
            entity_path = arguments.get("entity_path")
            if not entity_path:
                return {"error": "entity_path is required for explain_change"}
            result = self.cognitive.explain_change(
                entity_path,
                arguments.get("workspace_id"),
                arguments.get("session_id"),
            )
            return {"explanation": result}
        if name == "get_causal_chain":
            if not self.causal:
                return {"error": "CausalGraphService is unavailable"}
            event_id = arguments.get("event_id")
            if not event_id:
                return {"error": "event_id is required for get_causal_chain"}
            chain = self.causal.get_causal_chain(event_id, arguments.get("direction", "forward"))
            return {"causal_chain": [{"id": e.get("id"), "event_type": e.get("event_type"), "path": e.get("path"), "timestamp": e.get("timestamp")} for e in chain]}
        if name == "compare_snapshots":
            if not self.evolution:
                return {"error": "ArchitectureEvolutionService is unavailable"}
            sid_a = arguments.get("snapshot_id_a")
            sid_b = arguments.get("snapshot_id_b")
            if not sid_a or not sid_b:
                return {"error": "snapshot_id_a and snapshot_id_b are required for compare_snapshots"}
            try:
                diff = self.evolution.compare_snapshots(sid_a, sid_b)
            except ValueError as e:
                return {"error": str(e)}
            return {"diff": diff}
        if name == "list_decisions":
            if not self.decisions:
                return {"error": "DecisionTrackingService is unavailable"}
            records = self.decisions.get_decisions(arguments.get("workspace_id"), arguments.get("session_id"))
            return {"decisions": records}
        if name == "get_decision":
            if not self.decisions:
                return {"error": "DecisionTrackingService is unavailable"}
            decision_id = arguments.get("decision_id")
            if not decision_id:
                return {"error": "decision_id is required for get_decision"}
            record = self.decisions.get_decision(decision_id)
            if not record:
                return {"error": "Decision not found: " + str(decision_id)}
            return {"decision": record}
        if name == "search_semantic":
            if not self.vector_search or not self.vector_search.enabled:
                return {"error": "Vector search is unavailable (embeddings disabled)"}
            query = arguments.get("query", "")
            if not query:
                return {"error": "query is required for search_semantic"}
            table = arguments.get("table", "chunks")
            top_k = int(arguments.get("top_k", 10))
            if table == "all":
                results = self.vector_search.search_cross_entity(query, top_k)
            else:
                results = self.vector_search.search(query, table, top_k)
            return {"results": results}
        if name == "get_similar":
            if not self.vector_search or not self.vector_search.enabled:
                return {"error": "Vector search is unavailable (embeddings disabled)"}
            row_id = arguments.get("row_id")
            table = arguments.get("table", "chunks")
            top_k = int(arguments.get("top_k", 5))
            results = self.vector_search.find_similar(row_id, table, top_k)
            return {"results": results}
        if name == "get_awareness_signals":
            if not self.awareness:
                return {"error": "SemanticAwarenessService is unavailable"}
            signal_type = arguments.get("signal_type")
            limit = int(arguments.get("limit", 20))
            signals = self.awareness.get_signals(signal_type, limit)
            return {"signals": signals}
        if name == "list_connectors":
            if not self.connector or not self.connector.get_manager():
                return {"error": "ConnectorService is unavailable"}
            manager = self.connector.get_manager()
            connectors = []
            for cid in manager.list_ids():
                try:
                    status = manager.connector_status(cid)
                    connectors.append(status)
                except Exception:
                    connectors.append({"id": cid, "state": "error"})
            return {"connectors": connectors}
        if name == "get_connector_status":
            if not self.connector or not self.connector.get_manager():
                return {"error": "ConnectorService is unavailable"}
            connector_id = arguments.get("connector_id", "")
            if not connector_id:
                return {"error": "connector_id is required"}
            try:
                status = self.connector.get_manager().connector_status(connector_id)
                return {"status": status}
            except Exception as e:
                return {"error": str(e)}
        if name == "get_connector_health_all":
            if not self.connector or not self.connector.get_manager():
                return {"error": "ConnectorService is unavailable"}
            health = self.connector.get_manager().check_health_all()
            return {"health": health}
        if name == "get_evidence_stats":
            if not self.evidence_ingestion:
                return {"error": "EvidenceIngestionService is unavailable"}
            return {"stats": self.evidence_ingestion.get_stats()}
        if name == "get_connector_evidence":
            if not self.connector or not self.connector.get_manager():
                return {"error": "ConnectorService is unavailable"}
            connector_id = arguments.get("connector_id", "")
            if not connector_id:
                return {"error": "connector_id is required"}
            try:
                evidence = self.connector.get_manager().collect_evidence(connector_id)
                if evidence and self.evidence_ingestion:
                    result = self.evidence_ingestion.ingest(connector_id, evidence)
                    return {"evidence_count": len(evidence), "connector_id": connector_id, "ingested": result}
                return {"evidence_count": len(evidence), "connector_id": connector_id}
            except Exception as e:
                return {"error": str(e)}
        if name == "github_connector_status":
            if not self.connector or not self.connector.get_manager():
                return {"error": "ConnectorService is unavailable"}
            cid = arguments.get("connector_id", "github")
            try:
                status = self.connector.get_manager().connector_status(cid)
                return {"status": status}
            except Exception as e:
                return {"error": str(e)}
        if name == "connector_sync":
            if not self.connector or not self.connector.get_manager():
                return {"error": "ConnectorService is unavailable"}
            connector_id = arguments.get("connector_id", "")
            if not connector_id:
                return {"error": "connector_id is required"}
            try:
                manager = self.connector.get_manager()
                evidence = manager.collect_evidence(connector_id)
                if evidence and self.evidence_ingestion:
                    result = self.evidence_ingestion.ingest(connector_id, evidence)
                    return {"synced": len(evidence), "connector_id": connector_id, "ingested": result}
                return {"synced": len(evidence), "connector_id": connector_id}
            except Exception as e:
                return {"error": str(e)}
        if name == "connector_metrics":
            if not self.connector or not self.connector.get_manager():
                return {"error": "ConnectorService is unavailable"}
            connector_id = arguments.get("connector_id", "")
            try:
                manager = self.connector.get_manager()
                if connector_id:
                    connector = manager.get_connector(connector_id)
                    if hasattr(connector, 'get_metrics_collector'):
                        metrics = connector.get_metrics_collector()
                        return {"metrics": metrics.get_metrics(connector_id).to_dict() if metrics.get_metrics(connector_id) else {}}
                    return {"metrics": {"connector_id": connector_id, "note": "metrics not available"}}
                all_metrics = {}
                for cid in manager.list_ids():
                    connector = manager.get_connector(cid)
                    if hasattr(connector, 'get_metrics_collector'):
                        m = connector.get_metrics_collector().get_all_metrics()
                        all_metrics.update(m)
                return {"metrics": all_metrics}
            except Exception as e:
                return {"error": str(e)}
        if name == "connector_last_sync":
            if not self.connector or not self.connector.get_manager():
                return {"error": "ConnectorService is unavailable"}
            connector_id = arguments.get("connector_id", "")
            if not connector_id:
                return {"error": "connector_id is required"}
            try:
                connector = self.connector.get_manager().get_connector(connector_id)
                if hasattr(connector, 'get_sync_engine'):
                    sync_info = connector.get_sync_engine().last_sync(connector_id)
                    return {"last_sync": sync_info}
                return {"last_sync": None}
            except Exception as e:
                return {"error": str(e)}
        if name == "connector_health_details":
            if not self.connector or not self.connector.get_manager():
                return {"error": "ConnectorService is unavailable"}
            connector_id = arguments.get("connector_id", "")
            try:
                manager = self.connector.get_manager()
                if connector_id:
                    connector = manager.get_connector(connector_id)
                    health = connector.health().to_dict()
                    if hasattr(connector, 'get_metrics_collector'):
                        metrics = connector.get_metrics_collector().get_health_details(connector_id, health)
                        return {"health": metrics}
                    return {"health": health}
                all_health = {}
                for cid in manager.list_ids():
                    connector = manager.get_connector(cid)
                    h = connector.health().to_dict()
                    if hasattr(connector, 'get_metrics_collector'):
                        h = connector.get_metrics_collector().get_health_details(cid, h)
                    all_health[cid] = h
                return {"health": all_health}
            except Exception as e:
                return {"error": str(e)}
        if name == "explain_project_state":
            if not self.reasoning or not self.explainable:
                return {"error": "ReasoningEngine or ExplainableAIService unavailable"}
            query = arguments.get("query", "")
            if not query:
                return {"error": "query is required"}
            result = self.explainable.explain(
                query,
                arguments.get("path"),
                arguments.get("workspace_id"),
                arguments.get("session_id"),
            )
            return {"explanation": result}
        if name == "analyze_project_risk":
            if not self.project_intelligence:
                return {"error": "ProjectIntelligenceEngine unavailable"}
            ws_id = arguments.get("workspace_id")
            blockers = self.project_intelligence.detect_blockers(ws_id)
            bottlenecks = self.project_intelligence.detect_bottlenecks()
            stale = self.project_intelligence.detect_stale_work()
            drift = self.project_intelligence.detect_architecture_drift()
            return {
                "blockers": blockers,
                "bottlenecks": bottlenecks,
                "stale_work": stale,
                "architecture_drift": drift,
            }
        if name == "root_cause_analysis":
            if not self.root_cause:
                return {"error": "RootCauseAnalysisService unavailable"}
            issue = arguments.get("issue", "")
            if not issue:
                return {"error": "issue is required for root_cause_analysis"}
            result = self.root_cause.analyze(issue, arguments.get("path"), arguments.get("session_id"))
            return {"root_cause_analysis": result}
        if name == "impact_analysis":
            if not self.impact:
                return {"error": "ImpactAnalysisService unavailable"}
            path = arguments.get("path", "")
            if not path:
                return {"error": "path is required for impact_analysis"}
            result = self.impact.analyze(path)
            return {"impact_analysis": result}
        if name == "project_health":
            if not self.project_intelligence:
                return {"error": "ProjectIntelligenceEngine unavailable"}
            result = self.project_intelligence.project_health(arguments.get("workspace_id"))
            return {"project_health": result}
        if name == "reasoning_trace":
            if not self.reasoning:
                return {"error": "ReasoningEngine unavailable"}
            query = arguments.get("query", "")
            mode = arguments.get("mode", "cross_connector")
            if not query:
                return {"error": "query is required for reasoning_trace"}
            if mode == "cross_connector":
                result = self.reasoning.reason_cross_connector(query)
            elif mode == "dependencies":
                result = self.reasoning.reason_dependencies(query)
            elif mode == "timeline":
                result = self.reasoning.reason_timeline(query)
            elif mode == "evidence_correlation":
                result = self.reasoning.reason_evidence_correlation()
            elif mode == "historical":
                result = self.reasoning.reason_historical(query)
            else:
                return {"error": "Unknown reasoning mode: " + mode}
            return {"reasoning_trace": result}
        if name == "evidence_lineage":
            if not self.decision_lineage:
                return {"error": "DecisionLineageService unavailable"}
            decision_id = arguments.get("decision_id", "")
            if decision_id:
                result = self.decision_lineage.trace(decision_id)
                return {"evidence_lineage": result}
            result = self.decision_lineage.list_lineages(
                arguments.get("workspace_id"), arguments.get("session_id"))
            return {"evidence_lineages": result}
        if name == "dependency_graph":
            if not self.reasoning:
                return {"error": "ReasoningEngine unavailable"}
            path = arguments.get("path", "")
            if not path:
                return {"error": "path is required for dependency_graph"}
            depth = int(arguments.get("depth", 2))
            result = self.reasoning.reason_dependencies(path, depth)
            return {"dependency_graph": result}
        if name == "ai_twin_status":
            if not self.ai_twin:
                return {"error": "AITwinOrchestrator unavailable"}
            return {"ai_twin_status": self.ai_twin.twin_status()}
        if name == "ai_twin_health":
            if not self.ai_twin:
                return {"error": "AITwinOrchestrator unavailable"}
            return {"ai_twin_health": self.ai_twin.twin_health()}
        if name == "ai_twin_integrity":
            if not self.twin_validator:
                return {"error": "TwinIntegrityValidator unavailable"}
            if arguments.get("all"):
                return {"ai_twin_integrity": self.twin_validator.check_all()}
            return {"ai_twin_integrity": {
                "kg_consistency": self.twin_validator.check_kg_consistency(),
                "evidence_consistency": self.twin_validator.check_evidence_consistency(),
                "relationship_consistency": self.twin_validator.check_relationship_consistency(),
            }}
        if name == "ai_twin_overview":
            if not self.unified_twin:
                return {"error": "UnifiedProjectTwin unavailable"}
            return {"ai_twin_overview": self.unified_twin.overview()}
        if name == "ai_twin_summary":
            if not self.twin_report:
                return {"error": "UniversalTwinReport unavailable"}
            return {"ai_twin_summary": self.twin_report.generate_summary(arguments.get("workspace_id"))}
        if name == "ai_twin_connectors":
            if not self.unified_twin:
                return {"error": "UnifiedProjectTwin unavailable"}
            return {"ai_twin_connectors": self.unified_twin.connector_twin()}
        if name == "ai_twin_reasoning":
            if not self.unified_twin:
                return {"error": "UnifiedProjectTwin unavailable"}
            query = arguments.get("query", "")
            mode = arguments.get("mode", "evidence_correlation")
            result = self.unified_twin.reasoning_twin(query if query else None, mode)
            return {"ai_twin_reasoning": result}
        if name == "ai_twin_report":
            if not self.twin_report:
                return {"error": "UniversalTwinReport unavailable"}
            return {"ai_twin_report": self.twin_report.generate(arguments.get("workspace_id"))}
        if name == "discover_project_twin":
            if not self.project_twin:
                return {"error": "ProjectTwinDiscoveryService unavailable"}
            project_path = arguments.get("project_path", "")
            if not project_path:
                return {"error": "project_path is required"}
            result = self.project_twin.discover_project(project_path)
            return {"discovery": result}
        return {"error": "Unknown tool: " + str(name)}
