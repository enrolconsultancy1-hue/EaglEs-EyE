import os

from services.service import Service


class DocumentationLinkService(Service):
    DOCS = ("README.md", "ARCHITECTURE.md", "PROJECT_STATUS.md", "NEXT_TASK.md")
    def __init__(self, kernel):
        super().__init__(kernel); self.store = None
    def start(self):
        super().start(); self.store = self.kernel.get_service("KnowledgeStoreService")
    def analyze(self, root="."):
        text = {}
        for name in self.DOCS:
            path = os.path.join(root, name)
            try:
                with open(path, encoding="utf-8") as file: text[name] = file.read()
            except OSError: text[name] = ""
        services = self.store.find_symbols("Service", limit=1000)
        linked, undocumented = [], []
        for symbol in services:
            if symbol["kind"] not in ("class", "dataclass"): continue
            matches = [name for name, content in text.items() if symbol["name"] in content]
            (linked if matches else undocumented).append({"service": symbol["name"], "documents": matches})
        result = {"links": linked, "undocumented": undocumented, "coverage": 100 if not linked and not undocumented else round(100 * len(linked) / (len(linked) + len(undocumented)), 1)}
        self.store.record_reflection("Documentation link analysis", result)
        return result
