"""Architecture snapshots, symbol evolution tracking, and historical comparison."""

import json

from services.service import Service


class ArchitectureEvolutionService(Service):
    def __init__(self, kernel):
        super().__init__(kernel); self.store = None; self.graph = None

    def start(self):
        super().start(); self.store = self.kernel.get_service("KnowledgeStoreService")
        self.graph = self.kernel.get_service("KnowledgeGraphService")
        if not self.store: raise RuntimeError("ArchitectureEvolutionService requires KnowledgeStoreService.")

    def create_snapshot(self, workspace_id, session_id=None, label=None):
        symbols = self.store.find_symbols("") if self.graph else []
        symbol_index = {}
        for sym in symbols:
            path = sym.get("path", "unknown")
            symbol_index.setdefault(path, []).append({
                "name": sym["name"], "qualname": sym["qualname"],
                "kind": sym["kind"], "line": sym.get("line"),
            })
        snapshot_id = self.store.save_architecture_snapshot(workspace_id, session_id, label or "auto", symbol_index)
        return self.store.get_architecture_snapshot(snapshot_id)

    def compare_snapshots(self, snapshot_id_a, snapshot_id_b):
        a = self.store.get_architecture_snapshot(snapshot_id_a)
        b = self.store.get_architecture_snapshot(snapshot_id_b)
        if not a or not b: raise ValueError("Both snapshots must exist.")
        data_a, data_b = a["symbol_data"], b["symbol_data"]
        paths_a, paths_b = set(data_a.keys()), set(data_b.keys())
        added = [{"path": p, "symbols": data_b[p]} for p in paths_b - paths_a]
        removed = [{"path": p, "symbols": data_a[p]} for p in paths_a - paths_b]
        changed = []
        for p in paths_a & paths_b:
            names_a = {(s["name"], s["kind"]) for s in data_a[p]}
            names_b = {(s["name"], s["kind"]) for s in data_b[p]}
            if names_a != names_b:
                changed.append({
                    "path": p,
                    "added_symbols": [s for s in data_b[p] if (s["name"], s["kind"]) not in names_a],
                    "removed_symbols": [s for s in data_a[p] if (s["name"], s["kind"]) not in names_b],
                })
        return {
            "snapshot_a": a["id"], "snapshot_b": b["id"],
            "added_paths": added, "removed_paths": removed,
            "changed_paths": changed,
            "scope": "Observable symbol differences only.",
        }

    def get_evolution(self, qualname, workspace_id):
        snapshots = self.store.list_architecture_snapshots(workspace_id=workspace_id)
        history = []
        for snap in snapshots:
            for path, symbols in snap["symbol_data"].items():
                matching = [s for s in symbols if s["qualname"] == qualname]
                if matching:
                    history.append({"snapshot_id": snap["id"], "created_at": snap["created_at"],
                                    "path": path, "symbols": matching, "label": snap.get("label")})
        return {"qualname": qualname, "history": history, "scope": "Observable symbol history only."}

    def list_snapshots(self, workspace_id=None, session_id=None):
        return self.store.list_architecture_snapshots(workspace_id, session_id)
