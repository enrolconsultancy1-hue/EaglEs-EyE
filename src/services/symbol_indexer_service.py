"""Version-aware Python symbol extraction, independent from graph traversal."""

import ast
import os

from services.service import Service


class SymbolIndexerService(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        if not self.store:
            raise RuntimeError("SymbolIndexerService requires KnowledgeStoreService.")
        print("[SYMBOL INDEXER] Ready.")

    def index_document(self, path):
        document = self.store.get_document(path)
        if not document or document["status"] != "active" or not path.endswith(".py"):
            return []
        source = self._source(document["chunks"])
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        module = os.path.splitext(os.path.basename(path))[0]
        visitor = _SymbolVisitor(module)
        visitor.visit(tree)
        self.store.replace_symbols(document["id"], document["version"], visitor.symbols)
        return visitor.symbols

    @staticmethod
    def _source(chunks):
        parts, cursor = [], 0
        for chunk in sorted(chunks, key=lambda item: item["offset"]):
            offset, text = chunk["offset"], chunk["text"]
            if offset < cursor:
                text = text[cursor - offset:]
            parts.append(text)
            cursor = max(cursor, offset + len(chunk["text"]))
        return "".join(parts)


class _SymbolVisitor(ast.NodeVisitor):
    def __init__(self, module):
        self.module = module
        self.scope = []
        self.symbols = [{
            "name": module, "qualname": module, "kind": "module", "module": module,
            "parent_symbol": None, "line": 1, "end_line": None, "docstring": None,
            "visibility": "public", "signature": None,
        }]

    def _visibility(self, name):
        return "private" if name.startswith("__") else "protected" if name.startswith("_") else "public"

    def _add(self, node, name, kind, signature=None, docstring=None, metadata=None):
        parent = ".".join(self.scope) or None
        qualname = ".".join(self.scope + [name]) if self.scope else name
        self.symbols.append({
            "name": name, "qualname": qualname, "kind": kind, "module": self.module,
            "parent_symbol": parent, "line": getattr(node, "lineno", 1),
            "end_line": getattr(node, "end_lineno", None), "docstring": docstring,
            "visibility": self._visibility(name), "signature": signature, "metadata": metadata or {},
        })

    def visit_ClassDef(self, node):
        decorators = [self._name(item) for item in node.decorator_list]
        bases = [self._name(item) for item in node.bases]
        kind = "dataclass" if any(name.endswith("dataclass") for name in decorators) else "enum" if any(name.endswith("Enum") for name in bases) else "class"
        self._add(node, node.name, kind, docstring=ast.get_docstring(node), metadata={"decorators": decorators, "bases": bases})
        self.scope.append(node.name); self.generic_visit(node); self.scope.pop()

    def visit_FunctionDef(self, node): self._function(node, False)
    def visit_AsyncFunctionDef(self, node): self._function(node, True)

    def _function(self, node, asynchronous):
        decorators = [self._name(item) for item in node.decorator_list]
        kind = "property" if any(name.endswith("property") for name in decorators) else "async_method" if asynchronous and self.scope else "async_function" if asynchronous else "method" if self.scope else "function"
        args = [argument.arg for argument in node.args.args]
        self._add(node, node.name, kind, "(" + ", ".join(args) + ")", ast.get_docstring(node), {"decorators": decorators})
        self.scope.append(node.name); self.generic_visit(node); self.scope.pop()

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._add(target, target.id, "constant" if target.id.isupper() else "variable")
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if isinstance(node.target, ast.Name):
            self._add(node.target, node.target.id, "constant" if node.target.id.isupper() else "variable")
        self.generic_visit(node)

    @staticmethod
    def _name(node):
        if isinstance(node, ast.Name): return node.id
        if isinstance(node, ast.Attribute):
            value = _SymbolVisitor._name(node.value)
            return (value + "." if value else "") + node.attr
        if isinstance(node, ast.Call): return _SymbolVisitor._name(node.func)
        return ""
