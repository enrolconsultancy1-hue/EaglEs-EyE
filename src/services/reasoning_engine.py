"""Reasoning Engine — single entry point for all Phase 17 reasoning.

Universal Reasoning Policy:
Every reasoning result SHALL preserve complete evidence provenance.
A reasoning result SHALL NEVER exist without:
  - Source Connector(s)
  - Observation Surface(s)
  - Evidence IDs
  - Confidence Score
  - Reasoning Trace
  - Supporting Relationships
  - Timestamp(s)
"""

from datetime import datetime, timezone
from services.service import Service


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _wrap_result(conclusion, confidence, supporting_evidence, connector_sources,
                 observation_surfaces, reasoning_trace, supporting_relationships):
    return {
        "conclusion": conclusion,
        "confidence": confidence,
        "supporting_evidence": supporting_evidence,
        "connector_sources": connector_sources,
        "observation_surfaces": observation_surfaces,
        "reasoning_trace": reasoning_trace,
        "supporting_relationships": supporting_relationships,
        "timestamp": _utc_now(),
    }


class ReasoningEngine(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None
        self.kg = None
        self.causal = None
        self.cognitive = None
        self.confidence = None
        self.connector_svc = None
        self.evidence_ingestion = None
        self.decisions = None
        self.evolution = None
        self.timeline = None
        self.retrieval = None
        self.context = None

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        self.kg = self.kernel.get_service("KnowledgeGraphService")
        self.causal = self.kernel.get_service("CausalGraphService")
        self.cognitive = self.kernel.get_service("CognitiveLayerService")
        self.confidence = self.kernel.get_service("ConfidenceEngine")
        self.connector_svc = self.kernel.get_service("ConnectorService")
        self.evidence_ingestion = self.kernel.get_service("EvidenceIngestionService")
        self.decisions = self.kernel.get_service("DecisionTrackingService")
        self.evolution = self.kernel.get_service("ArchitectureEvolutionService")
        self.timeline = self.kernel.get_service("ExecutionTimelineService")
        self.retrieval = self.kernel.get_service("RetrievalService")
        self.context = self.kernel.get_service("ContextBuilderService")
        missing = [name for name, svc in [("KnowledgeStoreService", self.store),
                                          ("KnowledgeGraphService", self.kg),
                                          ("ConfidenceEngine", self.confidence)]
                   if not svc]
        if missing:
            raise RuntimeError("ReasoningEngine requires: " + ", ".join(missing))
        print("[REASONING ENGINE] Ready.")

    # -- Cross-connector reasoning --

    def reason_cross_connector(self, query, connector_ids=None):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        search_results = self.retrieval.search(query, limit=10) if self.retrieval else []
        for r in search_results:
            supporting_evidence.append({"citation": r.get("citation", ""), "text": r.get("text", "")[:200]})

        if self.connector_svc and self.connector_svc.get_manager():
            manager = self.connector_svc.get_manager()
            ids = connector_ids or manager.list_ids()
            for cid in ids:
                try:
                    connector = manager.get_connector(cid)
                    connector_sources.add(cid)
                    surfaces = connector.get_active_surfaces() if hasattr(connector, "get_active_surfaces") else []
                    for s in surfaces:
                        observation_surfaces.add(s)
                    reasoning_trace.append({"step": "queried_connector", "connector_id": cid, "surfaces": list(surfaces)})
                except Exception:
                    reasoning_trace.append({"step": "connector_unavailable", "connector_id": cid})

        if self.kg:
            for cid in connector_sources:
                correlated = self.kg.multi_source_correlate([cid])
                for target, rels in correlated.items():
                    supporting_relationships.append({"target": target, "count": len(rels)})

        confidence, conf_details = self.confidence.score_evidence(supporting_evidence) if self.confidence else (0.5, {})

        conclusion = "Cross-connector analysis for '%s' found %d evidence items across %d connectors." % (
            query, len(supporting_evidence), len(connector_sources))
        if not supporting_evidence:
            conclusion = "No evidence found for '%s' across available connectors." % query

        reasoning_trace.append({"step": "cross_connector_complete", "evidence_count": len(supporting_evidence)})

        return _wrap_result(conclusion, confidence, supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    # -- Dependency reasoning --

    def reason_dependencies(self, path, depth=2):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "dependency_analysis_start", "path": path})

        if self.kg:
            weighted = self.kg.related_weighted(path)
            for rel in weighted:
                target = rel.get("target_path", "")
                supporting_relationships.append({
                    "target": target,
                    "relation": rel.get("relation", ""),
                    "weight": rel.get("weight", 1.0),
                })
                doc = self.store.get_document(target, include_chunks=False) if target else None
                if doc:
                    supporting_evidence.append({"citation": "document:%s" % target, "path": target})
            reasoning_trace.append({"step": "kg_relationships_found", "count": len(weighted)})

            propagated = self.kg.propagate_confidence([path], 1.0, depth)
            for p, conf in propagated.items():
                if p != path:
                    supporting_relationships.append({"target": p, "propagated_confidence": conf, "depth": depth})
            reasoning_trace.append({"step": "confidence_propagated", "paths": len(propagated)})

        if self.connector_svc and self.connector_svc.get_manager():
            for cid in self.connector_svc.get_manager().list_ids():
                connector_sources.add(cid)
                try:
                    connector = self.connector_svc.get_manager().get_connector(cid)
                    surfaces = connector.get_active_surfaces() if hasattr(connector, "get_active_surfaces") else []
                    for s in surfaces:
                        observation_surfaces.add(s)
                except Exception:
                    pass

        confidence, conf_details = self.confidence.aggregate(
            (self.confidence.score_evidence(supporting_evidence) if self.confidence else (None, None)),
            (self.confidence.score_relationships(supporting_relationships) if self.confidence else (None, None)),
        ) if self.confidence else (0.5, {})

        conclusion = "Dependency analysis for '%s' found %d relationships and %d propagated paths." % (
            path, len(supporting_relationships),
            len([r for r in supporting_relationships if r.get("propagated_confidence")]))

        reasoning_trace.append({"step": "dependency_complete"})

        return _wrap_result(conclusion, confidence, supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    # -- Timeline reasoning --

    def reason_timeline(self, path=None, workspace_id=None, session_id=None):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "timeline_reasoning_start"})

        events = self.store.session_events(workspace_id, session_id) if (session_id or workspace_id) else (
            self.store.session_events(workspace_id=workspace_id) if workspace_id else []
        )
        if path:
            events = [e for e in events if path in str(e.get("path", ""))]

        for e in events:
            supporting_evidence.append({
                "citation": "event:%s" % e["id"],
                "event_type": e.get("event_type", ""),
                "path": e.get("path", ""),
                "timestamp": e.get("created_at", ""),
            })

        for idx, e in enumerate(events):
            if idx > 0:
                supporting_relationships.append({
                    "source": "event:%s" % events[idx - 1]["id"],
                    "target": "event:%s" % e["id"],
                    "relation": "happened_before",
                })

        reasoning_trace.append({"step": "events_collected", "count": len(events)})

        if self.connector_svc and self.connector_svc.get_manager():
            for cid in self.connector_svc.get_manager().list_ids():
                connector_sources.add(cid)

        confidence, _ = self.confidence.score_evidence(supporting_evidence) if self.confidence else (0.5, {})

        conclusion = "Timeline analysis: %d events found" % len(events)
        if session_id:
            conclusion += " for session %s" % session_id
        if path:
            conclusion += " related to %s" % path
        if not events:
            conclusion = "No events found for the given criteria."

        reasoning_trace.append({"step": "timeline_complete"})

        return _wrap_result(conclusion, confidence, supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    # -- State transition reasoning --

    def reason_state_transitions(self, path):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "state_transition_start", "path": path})

        doc = self.store.get_document(path) if path else None
        if doc:
            versions = []
            with self.store.transaction() as connection:
                rows = connection.execute(
                    "SELECT version, created_at, status FROM documents WHERE path = ? ORDER BY version",
                    (path,),
                ).fetchall()
            for row in rows:
                versions.append({"version": row["version"], "timestamp": row[1], "status": row[2]})
                supporting_evidence.append({
                    "citation": "document:version:%s:%d" % (path, row["version"]),
                    "version": row["version"],
                    "timestamp": row[1],
                })
            for idx in range(1, len(versions)):
                supporting_relationships.append({
                    "source": "version:%d" % versions[idx - 1]["version"],
                    "target": "version:%d" % versions[idx]["version"],
                    "relation": "transition",
                    "from_status": versions[idx - 1]["status"],
                    "to_status": versions[idx]["status"],
                })
            reasoning_trace.append({"step": "versions_found", "count": len(versions)})
        else:
            reasoning_trace.append({"step": "document_not_found", "path": path})

        if self.connector_svc and self.connector_svc.get_manager():
            for cid in self.connector_svc.get_manager().list_ids():
                connector_sources.add(cid)

        confidence, _ = self.confidence.score_evidence(supporting_evidence) if self.confidence else (0.5, {})

        conclusion = "State transition analysis for '%s': %d version(s)" % (path, doc["version"] if doc else 0) if doc else "No document found at '%s'" % path

        reasoning_trace.append({"step": "state_transition_complete"})

        return _wrap_result(conclusion, confidence, supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    # -- Relationship inference --

    def reason_relationships(self, path):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "relationship_inference_start", "path": path})

        if self.kg:
            weighted = self.kg.related_weighted(path)
            for rel in weighted:
                supporting_relationships.append(rel)
            reasoning_trace.append({"step": "weighted_relationships", "count": len(weighted)})

        doc = self.store.get_document(path, include_chunks=False) if path else None
        if doc:
            supporting_evidence.append({"citation": "document:%s" % path, "path": path})

        symbols = self.store.find_symbols(path.split("/")[-1].replace(".py", "")) if path else []
        for sym in symbols:
            supporting_evidence.append({"citation": "symbol:%s" % sym.get("qualname", sym["name"]), "symbol": sym.get("qualname", sym["name"])})

        if self.kg:
            used = self.kg.where_used(path.split("/")[-1].replace(".py", "")) if path else {}
            for rel in used.get("relationships", []):
                supporting_relationships.append({"source": rel.get("path", ""), "target": path, "relation": rel.get("relation", "")})

        reasoning_trace.append({"step": "where_used_checked", "count": len(used.get("relationships", [])) if path else 0})

        if self.connector_svc and self.connector_svc.get_manager():
            for cid in self.connector_svc.get_manager().list_ids():
                connector_sources.add(cid)

        confidence, conf_details = self.confidence.score_relationships(supporting_relationships) if self.confidence else (0.5, {})

        conclusion = "Relationship inference for '%s': %d relationships, %d symbols" % (
            path, len(supporting_relationships), len(symbols)) if doc else "No document found for '%s'" % path

        reasoning_trace.append({"step": "relationship_inference_complete"})

        return _wrap_result(conclusion, confidence, supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    # -- Evidence correlation --

    def reason_evidence_correlation(self, connector_ids=None):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "evidence_correlation_start"})

        if self.connector_svc and self.connector_svc.get_manager():
            manager = self.connector_svc.get_manager()
            ids = connector_ids or manager.list_ids()
            for cid in ids:
                connector_sources.add(cid)
                reasoning_trace.append({"step": "correlating_connector", "connector_id": cid})
                if self.kg:
                    correlated = self.kg.multi_source_correlate([cid])
                    for target, rels in correlated.items():
                        supporting_relationships.append({"target": target, "sources": [cid], "count": len(rels)})
                        for r in rels:
                            supporting_evidence.append({"citation": r.get("citation", "evidence:%s" % target), "target": target})

        reasoning_trace.append({"step": "correlation_complete", "connectors": len(connector_sources)})

        confidence, conf_details = self.confidence.aggregate(
            (self.confidence.score_evidence(supporting_evidence) if self.confidence else (None, None)),
            (self.confidence.score_relationships(supporting_relationships) if self.confidence else (None, None)),
        ) if self.confidence else (0.5, {})

        conclusion = "Evidence correlation across %d connector(s): %d correlated evidence items." % (
            len(connector_sources), len(supporting_evidence))

        return _wrap_result(conclusion, confidence, supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    # -- Historical reconstruction --

    def reason_historical(self, path, session_id=None):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "historical_reconstruction_start", "path": path})

        events = self.store.session_events(session_id=session_id) if session_id else self.store.recent_events(50)
        if path:
            events = [e for e in events if path in str(e.get("path", ""))]

        for e in events:
            supporting_evidence.append({
                "citation": "event:%s" % e["id"],
                "event_type": e.get("event_type", ""),
                "path": e.get("path", ""),
                "timestamp": e.get("created_at", ""),
            })

        if self.evolution and path:
            symbols = self.store.find_symbols(path.split("/")[-1].replace(".py", ""))
            for sym in symbols[:10]:
                qualname = sym.get("qualname") or sym["name"]
                evo = self.evolution.get_evolution(qualname)
                if evo.get("history"):
                    supporting_relationships.append({"type": "evolution", "symbol": qualname, "history": evo["history"]})
            reasoning_trace.append({"step": "evolution_checked", "symbols": len(symbols[:10])})

        if self.causal:
            for e in events[:5]:
                downstream = self.causal.get_downstream_events(e["id"])
                for d in downstream:
                    supporting_relationships.append({
                        "source": "event:%s" % e["id"],
                        "target": "event:%s" % d["id"],
                        "relation": "causal",
                    })

        if self.connector_svc and self.connector_svc.get_manager():
            for cid in self.connector_svc.get_manager().list_ids():
                connector_sources.add(cid)

        confidence, _ = self.confidence.score_evidence(supporting_evidence) if self.confidence else (0.5, {})

        n_days = 0
        if supporting_evidence:
            timestamps = [e.get("timestamp", "") for e in supporting_evidence if e.get("timestamp")]
            if timestamps:
                n_days = len(set(t[:10] for t in timestamps))

        conclusion = "Historical reconstruction for '%s': %d events across %d day(s)" % (
            path, len(events), n_days) if events else "No historical events found for '%s'" % path

        reasoning_trace.append({"step": "historical_reconstruction_complete"})

        return _wrap_result(conclusion, confidence, supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)
