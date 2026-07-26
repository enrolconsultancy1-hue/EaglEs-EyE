"""Impact Analysis Service — determine files affected, components affected,
documentation affected, tasks affected, connectors involved, estimated project impact.

Every conclusion must include evidence citations.
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


class ImpactAnalysisService(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None
        self.kg = None
        self.causal = None
        self.confidence = None
        self.connector_svc = None
        self.reasoning = None

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        self.kg = self.kernel.get_service("KnowledgeGraphService")
        self.causal = self.kernel.get_service("CausalGraphService")
        self.confidence = self.kernel.get_service("ConfidenceEngine")
        self.connector_svc = self.kernel.get_service("ConnectorService")
        self.reasoning = self.kernel.get_service("ReasoningEngine")
        if not all((self.store, self.confidence, self.reasoning)):
            raise RuntimeError("ImpactAnalysisService requires KnowledgeStoreService, ConfidenceEngine, and ReasoningEngine.")

    def analyze(self, path):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "impact_analysis_start", "path": path})

        affected_files = set()
        affected_components = set()
        affected_docs = set()

        if self.kg:
            weighted = self.kg.related_weighted(path)
            for rel in weighted:
                target = rel.get("target_path", "")
                if target:
                    affected_files.add(target)
                supporting_relationships.append(rel)
            reasoning_trace.append({"step": "kg_relationships", "count": len(weighted)})

            used = self.kg.where_used(path.split("/")[-1].replace(".py", ""))
            for rel in used.get("relationships", []):
                source = rel.get("path", "")
                if source:
                    affected_files.add(source)
                    if "doc" in source.lower():
                        affected_docs.add(source)
                    affected_components.add(source.split("/")[0] if "/" in source else source)
            reasoning_trace.append({"step": "where_used_checked", "count": len(used.get("relationships", []))})

        doc = self.store.get_document(path, include_chunks=False) if path else None
        if doc:
            supporting_evidence.append({
                "citation": "document:%s" % path,
                "path": path,
                "status": doc.get("status"),
            })

        if self.causal:
            events = self.store.session_events() if hasattr(self.store, "session_events") else []
            path_events = [e for e in events if path in str(e.get("path", ""))]
            for e in path_events:
                downstream = self.causal.get_downstream_events(e["id"]) if hasattr(self.causal, "get_downstream_events") else []
                for d in downstream:
                    d_path = d.get("path", "")
                    if d_path:
                        affected_files.add(d_path)
                        if "doc" in d_path.lower():
                            affected_docs.add(d_path)
                    supporting_relationships.append({
                        "source": "event:%s" % e["id"],
                        "target": "event:%s" % d.get("id"),
                        "path": d_path,
                        "relation": "causal_downstream",
                    })
            reasoning_trace.append({"step": "causal_downstream_checked"})

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

        impact_level = "low"
        total_affected = len(affected_files) + len(affected_docs)
        if total_affected > 10:
            impact_level = "high"
        elif total_affected > 3:
            impact_level = "medium"

        conclusion = "Impact analysis for '%s': %d files affected, %d components affected, %d docs affected. Impact level: %s" % (
            path, len(affected_files), len(affected_components), len(affected_docs), impact_level)

        reasoning_trace.append({"step": "impact_analysis_complete",
                                "files": len(affected_files),
                                "components": len(affected_components),
                                "docs": len(affected_docs)})

        result = _wrap_result(conclusion, confidence, supporting_evidence,
                              sorted(connector_sources), sorted(observation_surfaces),
                              reasoning_trace, supporting_relationships)
        result["affected_files"] = sorted(affected_files)
        result["affected_components"] = sorted(affected_components)
        result["affected_documentation"] = sorted(affected_docs)
        result["impact_level"] = impact_level
        return result
