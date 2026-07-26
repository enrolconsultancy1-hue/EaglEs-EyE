"""TwinIntegrityValidator — validates consistency and integrity across the
AI Twin: Knowledge Graph, evidence, relationships, connectors, sync, and
provenance.

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


class TwinIntegrityValidator(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None
        self.kg = None
        self.connector_svc = None
        self.sync_engine = None

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        self.kg = self.kernel.get_service("KnowledgeGraphService")
        self.connector_svc = self.kernel.get_service("ConnectorService")
        if not self.store:
            raise RuntimeError("TwinIntegrityValidator requires KnowledgeStoreService.")

    def _stats(self):
        return self.store.statistics() if self.store else {}

    def check_kg_consistency(self):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "kg_consistency_start"})

        stats = self._stats()
        total_symbols = stats.get("symbols", 0)
        total_docs = stats.get("documents", 0)
        total_relationships = stats.get("relationships", 0)

        issues = []
        if total_symbols > 0 and total_relationships == 0:
            issues.append("symbols_exist_without_relationships")
        if total_docs == 0 and total_symbols > 0:
            issues.append("symbols_without_documents")
        if total_symbols == 0 and total_relationships > 0:
            issues.append("relationships_without_symbols")

        supporting_evidence.append({
            "citation": "kg:stats",
            "symbols": total_symbols,
            "documents": total_docs,
            "relationships": total_relationships,
            "issues": issues,
        })

        if self.connector_svc and self.connector_svc.get_manager():
            for cid in self.connector_svc.get_manager().list_ids():
                connector_sources.add(cid)

        # Check active documents have at least one chunk
        try:
            with self.store.transaction() as conn:
                doc_count = conn.execute(
                    "SELECT COUNT(*) as count FROM documents WHERE status='active'"
                ).fetchone()["count"]
                chunk_count = conn.execute(
                    "SELECT COUNT(*) as count FROM chunks WHERE active=1"
                ).fetchone()["count"]
                if doc_count > 0 and chunk_count == 0:
                    issues.append("active_documents_without_chunks")
                supporting_evidence.append({
                    "citation": "kg:chunk_coverage",
                    "active_documents": doc_count,
                    "active_chunks": chunk_count,
                })
        except Exception:
            pass

        confidence = max(0.0, 1.0 - len(issues) * 0.25)
        conclusion = "KG consistency: %d issue(s)" % len(issues) if issues else "KG consistency: all checks passed"

        reasoning_trace.append({"step": "kg_consistency_complete", "issues": len(issues)})

        return _wrap_result(conclusion, round(confidence, 2), supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    def check_evidence_consistency(self):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "evidence_consistency_start"})

        issues = []
        try:
            with self.store.transaction() as conn:
                event_count = conn.execute("SELECT COUNT(*) as count FROM events").fetchone()["count"]
                obs_count = conn.execute("SELECT COUNT(*) as count FROM observations").fetchone()["count"]
                supporting_evidence.append({
                    "citation": "evidence:counts",
                    "events": event_count,
                    "observations": obs_count,
                })
                if obs_count > 0 and event_count == 0:
                    issues.append("observations_without_events")
        except Exception:
            issues.append("evidence_tables_unavailable")

        if self.connector_svc and self.connector_svc.get_manager():
            for cid in self.connector_svc.get_manager().list_ids():
                connector_sources.add(cid)

        confidence = max(0.0, 1.0 - len(issues) * 0.3)
        conclusion = "Evidence consistency: %d issue(s)" % len(issues) if issues else "Evidence consistency: all checks passed"

        reasoning_trace.append({"step": "evidence_consistency_complete", "issues": len(issues)})

        return _wrap_result(conclusion, round(confidence, 2), supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    def check_relationship_consistency(self):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "relationship_consistency_start"})

        issues = []
        try:
            with self.store.transaction() as conn:
                rel_count = conn.execute("SELECT COUNT(*) as count FROM relationships").fetchone()["count"]
                doc_count = conn.execute("SELECT COUNT(*) as count FROM documents WHERE status='active'").fetchone()["count"]
                dangling = conn.execute("""
                    SELECT COUNT(*) as count FROM relationships
                    WHERE target_document_id IS NOT NULL
                    AND target_document_id NOT IN (SELECT id FROM documents)
                """).fetchone()["count"]
                supporting_evidence.append({
                    "citation": "relationship:stats",
                    "total_relationships": rel_count,
                    "active_documents": doc_count,
                    "dangling_references": dangling,
                })
                if dangling > 0:
                    issues.append("dangling_references:%d" % dangling)
                    supporting_relationships.append({
                        "type": "dangling_reference",
                        "count": dangling,
                    })
        except Exception:
            issues.append("relationship_tables_unavailable")

        if self.connector_svc and self.connector_svc.get_manager():
            for cid in self.connector_svc.get_manager().list_ids():
                connector_sources.add(cid)

        confidence = max(0.0, 1.0 - len(issues) * 0.25)
        conclusion = "Relationship consistency: %d issue(s)" % len(issues) if issues else "Relationship consistency: all checks passed"

        reasoning_trace.append({"step": "relationship_consistency_complete", "issues": len(issues)})

        return _wrap_result(conclusion, round(confidence, 2), supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    def check_connector_consistency(self):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "connector_consistency_start"})

        issues = []
        if self.connector_svc and self.connector_svc.get_manager():
            manager = self.connector_svc.get_manager()
            for cid in manager.list_ids():
                connector_sources.add(cid)
                try:
                    status = manager.connector_status(cid)
                    supporting_evidence.append({
                        "citation": "connector:status:%s" % cid,
                        "connector_id": cid,
                        "state": status.get("state"),
                    })
                    if status.get("state") == "error":
                        issues.append("connector_error:%s" % cid)
                except Exception as e:
                    issues.append("connector_unreachable:%s" % cid)
                    supporting_evidence.append({
                        "citation": "connector:error:%s" % cid,
                        "connector_id": cid,
                        "error": str(e),
                    })
        else:
            issues.append("no_connector_service")

        confidence = max(0.0, 1.0 - len(issues) * 0.25)
        conclusion = "Connector consistency: %d issue(s)" % len(issues) if issues else "Connector consistency: all checks passed"

        reasoning_trace.append({"step": "connector_consistency_complete", "issues": len(issues)})

        return _wrap_result(conclusion, round(confidence, 2), supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    def check_sync_consistency(self):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "sync_consistency_start"})

        issues = []
        if self.connector_svc and self.connector_svc.get_manager():
            manager = self.connector_svc.get_manager()
            for cid in manager.list_ids():
                connector_sources.add(cid)
                try:
                    connector = manager.get_connector(cid)
                    if hasattr(connector, "get_sync_engine"):
                        sync_engine = connector.get_sync_engine()
                        status = sync_engine.status(cid) if hasattr(sync_engine, "status") else {}
                        supporting_evidence.append({
                            "citation": "sync:status:%s" % cid,
                            "connector_id": cid,
                            "sync_status": status,
                        })
                except Exception:
                    issues.append("sync_check_failed:%s" % cid)
        else:
            issues.append("no_connector_service")

        confidence = max(0.0, 1.0 - len(issues) * 0.25)
        conclusion = "Sync consistency: %d issue(s)" % len(issues) if issues else "Sync consistency: all checks passed"

        reasoning_trace.append({"step": "sync_consistency_complete", "issues": len(issues)})

        return _wrap_result(conclusion, round(confidence, 2), supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    def check_provenance_integrity(self):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "provenance_integrity_start"})

        issues = []
        try:
            with self.store.transaction() as conn:
                obs_with_provenance = conn.execute(
                    "SELECT COUNT(*) as count FROM observations WHERE source_connector IS NOT NULL"
                ).fetchone()["count"]
                obs_total = conn.execute(
                    "SELECT COUNT(*) as count FROM observations"
                ).fetchone()["count"]
                supporting_evidence.append({
                    "citation": "provenance:observation_coverage",
                    "total_observations": obs_total,
                    "with_provenance": obs_with_provenance,
                })
                if obs_total > 0 and obs_with_provenance < obs_total:
                    issues.append("observations_missing_provenance:%d" % (obs_total - obs_with_provenance))
        except Exception:
            issues.append("provenance_tables_unavailable")

        if self.connector_svc and self.connector_svc.get_manager():
            for cid in self.connector_svc.get_manager().list_ids():
                connector_sources.add(cid)

        confidence = max(0.0, 1.0 - len(issues) * 0.3)
        conclusion = "Provenance integrity: %d issue(s)" % len(issues) if issues else "Provenance integrity: all checks passed"

        reasoning_trace.append({"step": "provenance_integrity_complete", "issues": len(issues)})

        return _wrap_result(conclusion, round(confidence, 2), supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)

    def check_all(self):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "integrity_check_all_start"})

        checks = {
            "kg_consistency": self.check_kg_consistency(),
            "evidence_consistency": self.check_evidence_consistency(),
            "relationship_consistency": self.check_relationship_consistency(),
            "connector_consistency": self.check_connector_consistency(),
            "sync_consistency": self.check_sync_consistency(),
            "provenance_integrity": self.check_provenance_integrity(),
        }

        for check_name, result in checks.items():
            supporting_evidence.append({
                "citation": "integrity:%s" % check_name,
                "check": check_name,
                "conclusion": result["conclusion"],
                "confidence": result["confidence"],
            })
            if result.get("connector_sources"):
                connector_sources.update(result["connector_sources"])
            if result.get("supporting_evidence"):
                supporting_evidence.extend(result["supporting_evidence"])

        passed = sum(1 for r in checks.values() if "issue" not in r["conclusion"].lower() or "0 issue" in r["conclusion"].lower())
        total = len(checks)
        confidence = passed / total if total > 0 else 0.0
        conclusion = "Integrity check: %d/%d checks passed" % (passed, total)

        reasoning_trace.append({
            "step": "integrity_check_all_complete",
            "passed": passed,
            "total": total,
        })

        return _wrap_result(conclusion, round(confidence, 2), supporting_evidence,
                            sorted(connector_sources), sorted(observation_surfaces),
                            reasoning_trace, supporting_relationships)
