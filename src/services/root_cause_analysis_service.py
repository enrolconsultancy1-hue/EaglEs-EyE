"""Root Cause Analysis Service — determine what changed, why it changed,
which connector observed it, which evidence supports it, confidence score,
and related artifacts.

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


class RootCauseAnalysisService(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None
        self.kg = None
        self.causal = None
        self.evolution = None
        self.confidence = None
        self.connector_svc = None
        self.reasoning = None

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        self.kg = self.kernel.get_service("KnowledgeGraphService")
        self.causal = self.kernel.get_service("CausalGraphService")
        self.evolution = self.kernel.get_service("ArchitectureEvolutionService")
        self.confidence = self.kernel.get_service("ConfidenceEngine")
        self.connector_svc = self.kernel.get_service("ConnectorService")
        self.reasoning = self.kernel.get_service("ReasoningEngine")
        if not all((self.store, self.confidence, self.reasoning)):
            raise RuntimeError("RootCauseAnalysisService requires KnowledgeStoreService, ConfidenceEngine, and ReasoningEngine.")

    def analyze(self, issue, path=None, session_id=None):
        supporting_evidence = []
        connector_sources = set()
        observation_surfaces = set()
        reasoning_trace = []
        supporting_relationships = []

        reasoning_trace.append({"step": "rca_start", "issue": issue})

        events = self.store.session_events(session_id=session_id) if session_id else self.store.recent_events(100)

        related_events = []
        for e in events:
            payload_str = str(e.get("payload", {}))
            if issue.lower() in str(e.get("path", "")).lower() or issue.lower() in payload_str.lower():
                related_events.append(e)
                supporting_evidence.append({
                    "citation": "event:%s" % e["id"],
                    "event_type": e.get("event_type", ""),
                    "path": e.get("path", ""),
                    "payload": e.get("payload", {}),
                    "timestamp": e.get("created_at", ""),
                })

        if path:
            path_events = [e for e in events if path in str(e.get("path", ""))]
            for e in path_events:
                if e["id"] not in {ev["citation"].split(":")[-1] for ev in supporting_evidence}:
                    supporting_evidence.append({
                        "citation": "event:%s" % e["id"],
                        "event_type": e.get("event_type", ""),
                        "path": e.get("path", ""),
                        "timestamp": e.get("created_at", ""),
                    })
            reasoning_trace.append({"step": "path_filtered", "path": path, "count": len(path_events)})

        reasoning_trace.append({"step": "events_collected", "related_count": len(related_events)})

        if self.causal and related_events:
            for e in related_events:
                upstream = self.causal.get_upstream_events(e["id"]) if hasattr(self.causal, "get_upstream_events") else []
                for ue in upstream:
                    supporting_relationships.append({
                        "source": "event:%s" % ue.get("id"),
                        "target": "event:%s" % e["id"],
                        "relation": "causal_upstream",
                        "path": ue.get("path"),
                    })
            reasoning_trace.append({"step": "causal_chain_checked", "upstream_count": sum(
                1 for _ in related_events)})

        if self.evolution and path:
            symbols = self.store.find_symbols(path.split("/")[-1].replace(".py", "")) if path else []
            for sym in symbols[:5]:
                qualname = sym.get("qualname") or sym["name"]
                evo = self.evolution.get_evolution(qualname)
                if evo.get("history"):
                    supporting_relationships.append({
                        "type": "evolution",
                        "symbol": qualname,
                        "history": evo["history"],
                    })
            reasoning_trace.append({"step": "evolution_checked", "symbols": len(symbols[:5])})

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

        what_changed = []
        for ev in supporting_evidence:
            etype = ev.get("event_type", "")
            epath = ev.get("path", "")
            if etype:
                what_changed.append("%s:%s" % (etype, epath))

        conclusion = "Root cause analysis for '%s': %d related event(s), %d causal relationship(s)" % (
            issue, len(related_events), len(supporting_relationships))
        if related_events:
            first = related_events[0]
            conclusion += ". Earliest related event: %s at %s" % (first.get("event_type", ""), first.get("created_at", ""))
        if not related_events and not path:
            conclusion = "No evidence found for issue '%s'" % issue

        reasoning_trace.append({"step": "rca_complete"})

        result = _wrap_result(conclusion, confidence, supporting_evidence,
                              sorted(connector_sources), sorted(observation_surfaces),
                              reasoning_trace, supporting_relationships)
        result["what_changed"] = what_changed[:10]
        return result
