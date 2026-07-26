"""Explainable AI Service — every answer shall be explainable with why, how,
supporting evidence, related knowledge, and connector sources.

Every conclusion preserves observation provenance per Universal Reasoning Policy.
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


class ExplainableAIService(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None
        self.kg = None
        self.causal = None
        self.cognitive = None
        self.confidence = None
        self.connector_svc = None
        self.reasoning = None
        self.decisions = None
        self.evolution = None

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        self.kg = self.kernel.get_service("KnowledgeGraphService")
        self.causal = self.kernel.get_service("CausalGraphService")
        self.cognitive = self.kernel.get_service("CognitiveLayerService")
        self.confidence = self.kernel.get_service("ConfidenceEngine")
        self.connector_svc = self.kernel.get_service("ConnectorService")
        self.reasoning = self.kernel.get_service("ReasoningEngine")
        self.decisions = self.kernel.get_service("DecisionTrackingService")
        self.evolution = self.kernel.get_service("ArchitectureEvolutionService")
        if not all((self.store, self.confidence, self.reasoning)):
            raise RuntimeError("ExplainableAIService requires KnowledgeStoreService, ConfidenceEngine, and ReasoningEngine.")

    def explain(self, query_text, path=None, workspace_id=None, session_id=None):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "explain_start", "query": query_text})

        # Phase 1: Gather facts
        facts_evidence = self._gather_facts(query_text, path, workspace_id, session_id)
        supporting_evidence.extend(facts_evidence["evidence"])
        reasoning_trace.append({"step": "facts_gathered", "count": len(facts_evidence["evidence"])})

        # Phase 2: Derive relationships
        derived = self._derive_relationships(facts_evidence)
        supporting_relationships.extend(derived["relationships"])
        reasoning_trace.append({"step": "relationships_derived", "count": len(derived["relationships"])})

        # Phase 3: Build explanation
        explanation_parts = self._build_explanation(query_text, facts_evidence, derived)

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

        confidence, conf_details = self.confidence.score_evidence(supporting_evidence) if self.confidence else (0.5, {})

        conclusion = explanation_parts["summary"]
        how = explanation_parts["how"]
        why = explanation_parts["why"]

        reasoning_trace.append({"step": "explain_complete"})

        result = _wrap_result(conclusion, confidence, supporting_evidence,
                              sorted(connector_sources), sorted(observation_surfaces),
                              reasoning_trace, supporting_relationships)
        result["why"] = why
        result["how"] = how
        result["related_knowledge"] = facts_evidence.get("related_knowledge", [])
        result["citations"] = [ev.get("citation", "") for ev in supporting_evidence]
        return result

    def _gather_facts(self, query_text, path, workspace_id, session_id):
        evidence = []
        related_knowledge = []

        if self.cognitive and path:
            try:
                change_expl = self.cognitive.explain_change(path, workspace_id, session_id)
                for c in change_expl.get("citations", []):
                    evidence.append({"citation": c, "path": path})
                related_knowledge.append({"type": "cognitive_explain", "data": change_expl})
            except Exception:
                pass

        if self.store:
            if path:
                doc = self.store.get_document(path)
                if doc:
                    evidence.append({"citation": "document:%s" % path, "path": path})
                    related_knowledge.append({"type": "document", "path": path})

            if session_id or workspace_id:
                events = self.store.session_events(workspace_id, session_id) if workspace_id else (
                    self.store.session_events(session_id=session_id) if session_id else [])
                for e in events:
                    if path is None or path in str(e.get("path", "")):
                        evidence.append({
                            "citation": "event:%s" % e["id"],
                            "event_type": e.get("event_type", ""),
                            "path": e.get("path", ""),
                            "timestamp": e.get("created_at", ""),
                        })

            symbols = self.store.find_symbols(path.split("/")[-1].replace(".py", "")) if path else []
            for sym in symbols[:5]:
                evidence.append({
                    "citation": "symbol:%s" % sym.get("qualname", sym["name"]),
                    "symbol": sym.get("qualname", sym["name"]),
                })

        if self.kg and path:
            weighted = self.kg.related_weighted(path)
            for rel in weighted[:10]:
                related_knowledge.append({"type": "relationship", "data": rel})

        return {"evidence": evidence, "related_knowledge": related_knowledge}

    def _derive_relationships(self, facts):
        relationships = []
        seen_citations = set()
        for ev in facts["evidence"]:
            citation = ev.get("citation", "")
            if citation and citation not in seen_citations:
                seen_citations.add(citation)
                relationships.append({
                    "source": citation,
                    "relation": "observed_fact",
                    "detail": ev.get("event_type", "evidence_record"),
                })
        return {"relationships": relationships}

    def _build_explanation(self, query_text, facts, derived):
        evidence_count = len(facts["evidence"])
        rel_count = len(derived["relationships"])

        summary = "Explanation for '%s': %d evidence records, %d derived relationships." % (
            query_text, evidence_count, rel_count)
        if not evidence_count:
            summary = "No evidence found for '%s'" % query_text

        how = "Evidence was gathered from knowledge store events, documents, and symbols."
        if facts["related_knowledge"]:
            types = set(k.get("type", "") for k in facts["related_knowledge"])
            how += " Related knowledge sources: " + ", ".join(sorted(types)) + "."

        why = "Conclusion is based on %d observed facts with %d derived relationships." % (evidence_count, rel_count)
        if evidence_count == 0:
            why = "Insufficient evidence to determine why."

        return {"summary": summary, "how": how, "why": why}
