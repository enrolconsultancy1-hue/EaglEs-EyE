"""Observable event relationship tracking with citation-backed causal candidates."""

from services.service import Service


class CausalGraphService(Service):
    def __init__(self, kernel):
        super().__init__(kernel); self.store = None

    def start(self):
        super().start(); self.store = self.kernel.get_service("KnowledgeStoreService")
        if not self.store: raise RuntimeError("CausalGraphService requires KnowledgeStoreService.")

    def link_events(self, source_event_id, target_event_id, relation_type, metadata=None):
        self.store.add_causal_edge(source_event_id, target_event_id, relation_type, metadata)
        edge = self.store.get_causal_edges(event_id=source_event_id, relation_type=relation_type)
        return [e for e in edge if e["target_event_id"] == target_event_id][0] if edge else None

    def get_downstream_events(self, event_id):
        edges = self.store.get_causal_edges(event_id=event_id)
        downstream = [e["target_event_id"] for e in edges if e["source_event_id"] == event_id]
        return [self.store.get_event_by_id(eid) for eid in downstream if eid]

    def get_upstream_events(self, event_id):
        edges = self.store.get_causal_edges(event_id=event_id)
        upstream = [e["source_event_id"] for e in edges if e["target_event_id"] == event_id]
        return [self.store.get_event_by_id(eid) for eid in upstream if eid]

    def get_causal_chain(self, event_id, direction="forward"):
        chain, visited = [], {event_id}
        queue = [event_id]
        while queue:
            current = queue.pop(0)
            event = self.store.get_event_by_id(current)
            if event and event["id"] != event_id:
                chain.append(event)
            edges = self.store.get_causal_edges(event_id=current)
            for edge in edges:
                next_id = edge["target_event_id"] if direction == "forward" else edge["source_event_id"]
                if next_id not in visited and next_id != current:
                    visited.add(next_id); queue.append(next_id)
        return chain

    def get_events_by_relation(self, relation_type):
        edges = self.store.get_causal_edges(relation_type=relation_type)
        event_ids = set()
        for e in edges:
            event_ids.add(e["source_event_id"]); event_ids.add(e["target_event_id"])
        return [self.store.get_event_by_id(eid) for eid in sorted(event_ids) if eid]
