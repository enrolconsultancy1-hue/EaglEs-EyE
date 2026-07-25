from collections import Counter, defaultdict

from services.service import Service


class ArchitectureAnalyzerService(Service):
    """Conservative static health observations persisted as reflections."""
    def __init__(self, kernel):
        super().__init__(kernel); self.store = None
    def start(self):
        super().start(); self.store = self.kernel.get_service("KnowledgeStoreService")
    def analyze(self):
        with self.store.transaction() as connection:
            rows = [dict(row) for row in connection.execute("SELECT documents.path, relationships.target_path FROM relationships JOIN documents ON documents.id = relationships.source_document_id WHERE relationships.relation = 'imports'")]
            symbols = [dict(row) for row in connection.execute("SELECT document_id, name, kind FROM symbols WHERE active = 1")]
        modules = {path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1].rsplit(".", 1)[0]: path for path in {row["path"] for row in rows}}
        graph = defaultdict(set)
        for row in rows:
            source = row["path"]; target = row["target_path"].split(".")[0]
            if target in modules: graph[source].add(modules[target])
        cycles = self._cycles(graph)
        duplicates = [name for name, count in Counter(item["name"] for item in symbols).items() if count > 1]
        class_counts = Counter(item["document_id"] for item in symbols if item["kind"] in ("method", "async_method"))
        observation = {"circular_dependencies": cycles, "duplicate_symbols": duplicates, "large_classes": [str(key) for key, value in class_counts.items() if value > 20], "relationship_count": sum(len(value) for value in graph.values())}
        self.store.record_reflection("Architecture analysis", observation)
        return observation
    @staticmethod
    def _cycles(graph):
        found, visiting, visited = [], set(), set()
        def walk(node, trail):
            if node in visiting:
                found.append(trail[trail.index(node):]); return
            if node in visited: return
            visiting.add(node)
            for target in graph[node]: walk(target, trail + [target])
            visiting.remove(node); visited.add(node)
        for node in graph: walk(node, [node])
        return found
