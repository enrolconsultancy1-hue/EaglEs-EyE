"""Static project intelligence for Python sources.

Facts are deliberately conservative: unsupported or unresolved references are
stored as named graph targets rather than guessed filesystem paths.
"""

import ast
import os

from services.service import Service


class KnowledgeGraphService(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        if not self.store:
            raise RuntimeError("KnowledgeGraphService requires KnowledgeStoreService.")
        print("[KNOWLEDGE GRAPH] Ready.")

    def analyze_document(self, path):
        document = self.store.get_document(path)
        if not document or not path.endswith(".py") or document["status"] != "active":
            return []
        source = self._reconstruct_source(document["chunks"])
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        visitor = _ProjectVisitor()
        visitor.visit(tree)
        # Symbol ownership belongs to SymbolIndexerService.  Keep a fallback
        # for callers using this service independently during migration.
        if not self.kernel.get_service("SymbolIndexerService"):
            self.store.replace_symbols(document["id"], document["version"], visitor.symbols)
        self._replace_relationships(document["id"], visitor.relationships)
        return visitor.relationships

    @staticmethod
    def _reconstruct_source(chunks):
        """Remove intentional index overlap before passing text to the parser."""
        parts = []
        cursor = 0
        for chunk in sorted(chunks, key=lambda item: item["offset"]):
            offset = chunk["offset"]
            text = chunk["text"]
            if offset < cursor:
                text = text[cursor - offset:]
            if text:
                parts.append(text)
                cursor = max(cursor, offset + len(chunk["text"]))
        return "".join(parts)

    def _replace_relationships(self, document_id, relationships):
        with self.store.transaction() as connection:
            connection.execute("DELETE FROM relationships WHERE source_document_id = ?", (document_id,))
        for target, relation, metadata in relationships:
            self.store.add_relationship(document_id, target, relation, metadata)

    def related(self, path):
        document = self.store.get_document(path, include_chunks=False)
        if not document:
            return []
        with self.store.transaction() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT target_path, relation, metadata, created_at FROM relationships WHERE source_document_id = ?",
                (document["id"],),
            )]

    def where_used(self, name):
        """Find symbol definitions and named static relationships."""
        symbols = self.store.find_symbols(name)
        with self.store.transaction() as connection:
            relationships = [dict(row) for row in connection.execute(
                """SELECT documents.path, relationships.target_path, relationships.relation, relationships.metadata
                FROM relationships JOIN documents ON documents.id = relationships.source_document_id
                WHERE relationships.target_path LIKE ? ORDER BY documents.path""",
                ("%" + name + "%",),
            )]
        return {"symbols": symbols, "relationships": relationships}


class _ProjectVisitor(ast.NodeVisitor):
    def __init__(self):
        self.symbols = []
        self.relationships = []
        self.scope = []
        self.class_names = set()

    def _qualname(self, name):
        return ".".join(self.scope + [name])

    def _add_symbol(self, node, name, kind, signature=None, metadata=None):
        self.symbols.append({
            "name": name, "qualname": self._qualname(name), "kind": kind,
            "line": getattr(node, "lineno", None), "end_line": getattr(node, "end_lineno", None),
            "signature": signature, "metadata": metadata or {},
        })

    def visit_Import(self, node):
        for alias in node.names:
            self.relationships.append((alias.name, "imports", {"line": node.lineno}))

    def visit_ImportFrom(self, node):
        module = node.module or ""
        for alias in node.names:
            target = module + ("." if module else "") + alias.name
            self.relationships.append((target, "imports", {"line": node.lineno, "relative": node.level}))

    def visit_ClassDef(self, node):
        decorators = [self._expression_name(item) for item in node.decorator_list]
        kind = "enum" if any(base.endswith("Enum") for base in map(self._expression_name, node.bases)) else "class"
        if any(item.endswith("dataclass") for item in decorators):
            kind = "dataclass"
        self._add_symbol(node, node.name, kind, metadata={"decorators": decorators})
        for base in node.bases:
            self.relationships.append((self._expression_name(base), "inherits", {"line": node.lineno}))
        self.class_names.add(node.name)
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node):
        self._function(node)

    def visit_AsyncFunctionDef(self, node):
        self._function(node)

    def _function(self, node):
        kind = "method" if self.scope else "function"
        decorators = [self._expression_name(item) for item in node.decorator_list]
        arguments = [argument.arg for argument in node.args.args]
        self._add_symbol(node, node.name, kind, "(" + ", ".join(arguments) + ")", {"decorators": decorators})
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name):
                kind = "constant" if target.id.isupper() else "variable"
                self._add_symbol(target, target.id, kind)
            elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                self.relationships.append((target.attr, "composes", {"line": node.lineno}))
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if isinstance(node.target, ast.Name):
            kind = "constant" if node.target.id.isupper() else "variable"
            self._add_symbol(node.target, node.target.id, kind)
        self.generic_visit(node)

    def visit_Call(self, node):
        name = self._expression_name(node.func)
        if name:
            self.relationships.append((name, "calls", {"line": node.lineno}))
        if name.endswith("register_service") and node.args:
            self.relationships.append((self._expression_name(node.args[0]), "registers_service", {"line": node.lineno}))
        if name.endswith("subscribe") and node.args and isinstance(node.args[0], ast.Constant):
            self.relationships.append(("event:" + str(node.args[0].value), "subscribes_to", {"line": node.lineno}))
        self.generic_visit(node)

    @staticmethod
    def _expression_name(node):
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = _ProjectVisitor._expression_name(node.value)
            return (parent + "." if parent else "") + node.attr
        if isinstance(node, ast.Constant):
            return str(node.value)
        if isinstance(node, ast.Call):
            return _ProjectVisitor._expression_name(node.func)
        return ""
