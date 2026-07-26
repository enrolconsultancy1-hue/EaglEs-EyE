"""Project Intelligence Engine — project health, blockers, bottlenecks, stale work,
orphaned artifacts, duplicate knowledge, missing documentation, architecture drift.

Every conclusion preserves evidence provenance per the Universal Reasoning Policy.
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


class ProjectIntelligenceEngine(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None
        self.kg = None
        self.causal = None
        self.confidence = None
        self.connector_svc = None
        self.evidence_ingestion = None
        self.reasoning = None

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        self.kg = self.kernel.get_service("KnowledgeGraphService")
        self.causal = self.kernel.get_service("CausalGraphService")
        self.confidence = self.kernel.get_service("ConfidenceEngine")
        self.connector_svc = self.kernel.get_service("ConnectorService")
        self.evidence_ingestion = self.kernel.get_service("EvidenceIngestionService")
        self.reasoning = self.kernel.get_service("ReasoningEngine")
        if not all((self.store, self.confidence, self.reasoning)):
            raise RuntimeError("ProjectIntelligenceEngine requires KnowledgeStoreService, ConfidenceEngine, and ReasoningEngine.")

    def project_health(self, workspace_id=None):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "health_check_start"})

        stats = self.store.statistics() if self.store else {}
        total_docs = stats.get("documents", 0)
        total_events = stats.get("events", 0)
        total_symbols = stats.get("symbols", 0)
        total_relationships = stats.get("relationships", 0)

        supporting_evidence.append({
            "citation": "store:statistics",
            "documents": total_docs,
            "events": total_events,
            "symbols": total_symbols,
            "relationships": total_relationships,
        })

        scores = []

        doc_score = min(total_docs / 100.0, 1.0) if total_docs > 0 else 0.1
        scores.append(doc_score)
        reasoning_trace.append({"step": "document_score", "score": doc_score})

        rel_score = min(total_relationships / max(total_symbols, 1) / 2.0, 1.0) if total_symbols > 0 else 0.1
        scores.append(rel_score)
        reasoning_trace.append({"step": "relationship_score", "score": rel_score})

        if self.connector_svc and self.connector_svc.get_manager():
            manager = self.connector_svc.get_manager()
            healthy = 0
            total = 0
            for cid in manager.list_ids():
                total += 1
                try:
                    status = manager.connector_status(cid)
                    if status.get("state") in ("running", "connected"):
                        healthy += 1
                    connector_sources.add(cid)
                except Exception:
                    pass
            connector_health = healthy / max(total, 1)
            scores.append(connector_health)
            reasoning_trace.append({"step": "connector_health", "healthy": healthy, "total": total})
            supporting_evidence.append({
                "citation": "connector:health",
                "healthy_connectors": healthy,
                "total_connectors": total,
            })

        if self.evidence_ingestion:
            ingested_stats = self.evidence_ingestion.get_stats() if hasattr(self.evidence_ingestion, "get_stats") else {}
            supporting_evidence.append({
                "citation": "evidence:ingestion_stats",
                "ingested_count": ingested_stats,
            })

        confidence = round(sum(scores) / max(len(scores), 1), 2) if scores else 0.5

        alerts = []
        if doc_score < 0.3:
            alerts.append("low_document_count")
        if rel_score < 0.2:
            alerts.append("low_relationship_coverage")
        if scores and len(scores) > 2 and scores[-1] < 0.5:
            alerts.append("connector_health_risk")

        health_status = "healthy" if confidence >= 0.7 else ("degraded" if confidence >= 0.4 else "critical")
        conclusion = "Project health: %s (confidence: %.2f). %d documents, %d events, %d symbols, %d relationships." % (
            health_status, confidence, total_docs, total_events, total_symbols, total_relationships)
        if alerts:
            conclusion += " Alerts: " + ", ".join(alerts)

        reasoning_trace.append({"step": "health_complete", "status": health_status})

        return _wrap_result(conclusion, confidence, supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    def detect_blockers(self, workspace_id=None):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "blocker_detection_start"})

        blockers = []

        events = self.store.session_events(workspace_id=workspace_id) if workspace_id else self.store.recent_events(100)
        errors = [e for e in events if "error" in str(e.get("event_type", "")).lower()
                  or "fail" in str(e.get("payload", {})).lower()]
        for e in errors:
            blockers.append({
                "type": "error_event",
                "event_id": e["id"],
                "path": e.get("path", ""),
                "timestamp": e.get("created_at", ""),
            })
            supporting_evidence.append({
                "citation": "event:%s" % e["id"],
                "event_type": e.get("event_type", ""),
                "path": e.get("path", ""),
            })

        reasoning_trace.append({"step": "error_events_found", "count": len(errors)})

        if self.connector_svc and self.connector_svc.get_manager():
            manager = self.connector_svc.get_manager()
            for cid in manager.list_ids():
                connector_sources.add(cid)
                try:
                    status = manager.connector_status(cid)
                    if status.get("state") == "error":
                        blockers.append({
                            "type": "connector_error",
                            "connector_id": cid,
                            "state": "error",
                        })
                        supporting_evidence.append({
                            "citation": "connector:status:%s" % cid,
                            "connector_id": cid,
                            "state": "error",
                        })
                except Exception:
                    pass

        if self.causal:
            all_edges = self.causal.get_causal_edges() if hasattr(self.causal, "get_causal_edges") else []
            for edge in all_edges:
                meta = edge.get("metadata", {}) if isinstance(edge.get("metadata"), dict) else {}
                if meta.get("is_blocker"):
                    supporting_relationships.append(edge)

        confidence = min(len(blockers) / 10.0, 1.0) if blockers else 0.0
        concept = "Blockers detected: %d issue(s)" % len(blockers) if blockers else "No blockers detected"
        conclusion = "%s across %d connector(s)" % (concept, len(connector_sources))

        reasoning_trace.append({"step": "blocker_detection_complete", "blocker_count": len(blockers)})

        return _wrap_result(conclusion, confidence, supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    def detect_bottlenecks(self):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "bottleneck_detection_start"})

        if self.connector_svc and self.connector_svc.get_manager():
            manager = self.connector_svc.get_manager()
            for cid in manager.list_ids():
                connector_sources.add(cid)
                try:
                    connector = manager.get_connector(cid)
                    if hasattr(connector, "get_metrics_collector"):
                        metrics = connector.get_metrics_collector()
                        all_m = metrics.get_all_metrics() if hasattr(metrics, "get_all_metrics") else {}
                        for mid, m in all_m.items():
                            if isinstance(m, dict) and m.get("failures", 0) > 5:
                                supporting_evidence.append({
                                    "citation": "metrics:%s:%s" % (cid, mid),
                                    "connector_id": cid,
                                    "failures": m.get("failures", 0),
                                    "retries": m.get("retries", 0),
                                })
                                supporting_relationships.append({
                                    "source": cid,
                                    "type": "bottleneck",
                                    "failures": m.get("failures", 0),
                                })
                except Exception:
                    pass

        events = self.store.recent_events(200)
        error_rates = {}
        for e in events:
            etype = e.get("event_type", "unknown")
            error_rates[etype] = error_rates.get(etype, 0) + 1
        for etype, count in error_rates.items():
            if count > 20:
                supporting_evidence.append({
                    "citation": "event_type:%s" % etype,
                    "event_type": etype,
                    "count": count,
                })

        confidence = len(supporting_evidence) / max(len(supporting_evidence) + 5, 1)
        confidence = min(max(confidence, 0.0), 1.0)

        conclusion = "Bottleneck analysis: %d potential bottlenecks identified across %d connectors" % (
            len(supporting_evidence), len(connector_sources))
        if not supporting_evidence:
            conclusion = "No bottlenecks detected"

        reasoning_trace.append({"step": "bottleneck_detection_complete"})

        return _wrap_result(conclusion, round(confidence, 2), supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    def detect_stale_work(self, days=30):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "stale_work_detection_start"})

        with self.store.transaction() as connection:
            stale_docs = connection.execute(
                """SELECT path, updated_at, status FROM documents
                   WHERE status = 'active' AND updated_at < datetime('now', ?)
                   ORDER BY updated_at LIMIT 20""",
                ("-%d days" % days,),
            ).fetchall()
        for row in stale_docs:
            supporting_evidence.append({
                "citation": "document:%s" % row["path"],
                "path": row["path"],
                "last_updated": row[1],
                "status": row[2],
            })
        reasoning_trace.append({"step": "stale_documents", "count": len(stale_docs)})

        with self.store.transaction() as connection:
            orphaned = connection.execute(
                """SELECT path FROM documents WHERE status = 'active' AND path NOT IN
                   (SELECT DISTINCT target_path FROM relationships) LIMIT 20"""
            ).fetchall()
        for row in orphaned:
            supporting_evidence.append({
                "citation": "document:%s" % row["path"],
                "path": row["path"],
                "orphaned": True,
            })
        reasoning_trace.append({"step": "orphaned_documents", "count": len(orphaned)})

        if self.connector_svc and self.connector_svc.get_manager():
            for cid in self.connector_svc.get_manager().list_ids():
                connector_sources.add(cid)

        confidence = min(len(supporting_evidence) / 20.0, 1.0)
        conclusion = "Stale work: %d stale documents (>%d days), %d orphaned documents" % (
            len(stale_docs), days, len(orphaned))
        if not stale_docs and not orphaned:
            conclusion = "No stale or orphaned work detected"

        reasoning_trace.append({"step": "stale_work_detection_complete"})

        return _wrap_result(conclusion, round(confidence, 2), supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    def detect_architecture_drift(self):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "architecture_drift_detection_start"})

        snapshots = self.store.list_architecture_snapshots() if hasattr(self.store, "list_architecture_snapshots") else []
        if len(snapshots) >= 2:
            latest = snapshots[-1]
            previous = snapshots[-2]
            latest_symbols = set(latest.get("symbol_data", {}).keys()) if isinstance(latest.get("symbol_data"), dict) else set()
            prev_symbols = set(previous.get("symbol_data", {}).keys()) if isinstance(previous.get("symbol_data"), dict) else set()
            added = latest_symbols - prev_symbols
            removed = prev_symbols - latest_symbols
            if added:
                supporting_evidence.append({
                    "citation": "snapshot:%s" % latest["id"],
                    "type": "symbols_added",
                    "count": len(added),
                    "symbols": list(added)[:10],
                })
            if removed:
                supporting_evidence.append({
                    "citation": "snapshot:%s" % latest["id"],
                    "type": "symbols_removed",
                    "count": len(removed),
                    "symbols": list(removed)[:10],
                })
            supporting_relationships.append({
                "source": "snapshot:%s" % previous["id"],
                "target": "snapshot:%s" % latest["id"],
                "relation": "drift",
                "added": len(added),
                "removed": len(removed),
            })
            reasoning_trace.append({"step": "snapshot_comparison", "added": len(added), "removed": len(removed)})
        else:
            reasoning_trace.append({"step": "insufficient_snapshots", "count": len(snapshots)})

        if self.connector_svc and self.connector_svc.get_manager():
            for cid in self.connector_svc.get_manager().list_ids():
                connector_sources.add(cid)

        confidence, _ = self.confidence.score_evidence(supporting_evidence) if self.confidence else (0.5, {})
        conclusion = "Architecture drift analysis: %d changes detected across %d snapshots" % (
            len(supporting_evidence), len(snapshots)) if len(snapshots) >= 2 else "Insufficient snapshots for drift detection (%d available)" % len(snapshots)

        reasoning_trace.append({"step": "architecture_drift_detection_complete"})

        return _wrap_result(conclusion, confidence, supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)
