"""Evidence-backed explanation engine grounded in observed facts and derived relationships.

Extends the read-only reasoning foundation with structured, citated explanations
that maintain strict separation between observed facts, derived relationships,
and evidence-backed conclusions.
"""

from services.service import Service


class CognitiveLayerService(Service):
    def __init__(self, kernel):
        super().__init__(kernel); self.store = None; self.causal = None
        self.evolution = None; self.decisions = None; self.timeline = None

    def start(self):
        super().start(); self.store = self.kernel.get_service("KnowledgeStoreService")
        self.causal = self.kernel.get_service("CausalGraphService")
        self.evolution = self.kernel.get_service("ArchitectureEvolutionService")
        self.decisions = self.kernel.get_service("DecisionTrackingService")
        self.timeline = self.kernel.get_service("ExecutionTimelineService")
        if not all((self.store, self.causal, self.timeline)):
            raise RuntimeError("CognitiveLayerService requires KnowledgeStoreService, CausalGraphService, and ExecutionTimelineService.")

    def explain_change(self, entity_path, workspace_id=None, session_id=None):
        observed_facts = self._gather_facts(entity_path, workspace_id, session_id)
        derived = self._derive_relationships(entity_path, observed_facts)
        explanation = self._build_explanation(entity_path, observed_facts, derived)
        return explanation

    def _gather_facts(self, entity_path, workspace_id, session_id):
        facts = {"events": [], "decisions": [], "symbols": []}
        events = self.store.session_events(workspace_id, session_id) if session_id else (
            self.store.session_events(workspace_id=workspace_id) if workspace_id else []
        )
        for event in events:
            if event.get("path") and entity_path in event["path"]:
                event["citation"] = "event:%s" % event["id"]
                facts["events"].append(event)
        if self.decisions:
            decisions = self.decisions.get_decisions(workspace_id, session_id)
            for d in decisions:
                if entity_path in str(d.get("payload", {})):
                    facts["decisions"].append(d)
        if self.evolution:
            symbols = self.store.find_symbols(entity_path.split("/")[-1].replace(".py", ""))
            facts["symbols"] = symbols
        return facts

    def _derive_relationships(self, entity_path, facts):
        relationships = {"causal_chains": [], "evolution": [], "event_ordering": []}
        event_ids = sorted([e["id"] for e in facts["events"]])
        for idx, event_id in enumerate(event_ids):
            if idx > 0:
                relationships["event_ordering"].append({
                    "source": "event:%s" % event_ids[idx - 1],
                    "target": "event:%s" % event_id,
                    "relation": "happened_before",
                })
            if self.causal:
                downstream = self.causal.get_downstream_events(event_id)
                for d in downstream:
                    relationships["causal_chains"].append({
                        "source": "event:%s" % event_id,
                        "target": "event:%s" % d["id"],
                        "relation": d.get("path", "unknown"),
                        "path": d.get("path"),
                    })
        if self.evolution and facts["symbols"]:
            ws_id = None
            if facts["events"] and facts["events"][0].get("workspace_id"):
                ws_id = facts["events"][0]["workspace_id"]
            for sym in facts["symbols"][:5]:
                qualname = sym.get("qualname") or sym["name"]
                evo = self.evolution.get_evolution(qualname, ws_id)
                if evo["history"]:
                    relationships["evolution"].append(evo)
        return relationships

    @staticmethod
    def _build_explanation(entity_path, facts, derived):
        lines = []
        if facts["events"]:
            count = len(facts["events"])
            line = "%d observable event(s) recorded for %s." % (count, entity_path)
            event_types = set(e["event_type"] for e in facts["events"])
            line += " Types: %s." % ", ".join(sorted(event_types))
            lines.append(line)
        if derived["event_ordering"]:
            lines.append("Event sequence: %d events ordered by timestamp." % len(derived["event_ordering"]))
        if derived["causal_chains"]:
            lines.append("%d causal relationship(s) link these events to downstream changes." % len(derived["causal_chains"]))
        if facts["decisions"]:
            lines.append("%d explicit decision record(s) reference this entity." % len(facts["decisions"]))
        if derived["evolution"]:
            lines.append("%d symbol evolution record(s) track structural changes." % len(derived["evolution"]))
        citations = [event["citation"] for event in facts["events"]]
        for d in facts["decisions"]:
            citations.extend(d.get("evidence_citations", []))
        if not lines:
            lines.append("No observable evidence found for %s." % entity_path)
        return {
            "entity": entity_path,
            "explanation": " ".join(lines),
            "observed_facts": {
                "event_count": len(facts["events"]),
                "decision_count": len(facts["decisions"]),
                "symbol_count": len(facts["symbols"]),
            },
            "derived_relationships": {
                "event_ordering_count": len(derived["event_ordering"]),
                "causal_chain_count": len(derived["causal_chains"]),
                "evolution_records": len(derived["evolution"]),
            },
            "citations": list(set(citations)),
            "scope": "Observable evidence only. No hidden reasoning is claimed.",
        }

    def query(self, question, workspace_id=None, session_id=None):
        tokens = question.lower().split()
        entity = None
        for word in tokens:
            if ".py" in word or "." in word:
                entity = word.strip("?.,!:;")
                break
        if not entity:
            for word in tokens:
                if "service" in word or "class" in word or "file" in word:
                    entity = word.strip("?.,!:;")
                    break
        if entity:
            result = self.explain_change(entity, workspace_id, session_id)
            result["question"] = question
            return result
        return {
            "question": question,
            "explanation": "No specific entity identified in the question to query.",
            "citations": [],
            "scope": "Observable evidence only.",
        }
