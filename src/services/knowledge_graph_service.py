"""Static project intelligence for Python sources.

Facts are deliberately conservative: unsupported or unresolved references are
stored as named graph targets rather than guessed filesystem paths.
"""

import ast
import json
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

    def ingest_connector_evidence(self, connector_id, evidence_list):
        """Ingest connector-sourced evidence as graph relationships.

        Each connector Evidence object is converted into a relationship entry
        linking the connector source to the evidence target. This provides a
        unified graph view that spans Python AST analysis and connector evidence.
        """
        imported = 0
        for evidence in evidence_list:
            target = getattr(evidence, "observation_id", "") or connector_id
            evidence_id = getattr(evidence, "id", "")
            confidence = getattr(evidence.confidence, "score", 1.0) if hasattr(evidence, "confidence") else 1.0
            metadata = {
                "connector_id": connector_id,
                "evidence_id": evidence_id,
                "confidence": confidence,
            }
            if hasattr(evidence, "relationships") and evidence.relationships:
                for rel in evidence.relationships:
                    rel_metadata = dict(metadata)
                    rel_metadata["relation_type"] = getattr(rel, "type", "connector_evidence")
                    self.store.add_relationship(
                        connector_id, getattr(rel, "target_id", target),
                        "connector_evidence", rel_metadata,
                    )
                    imported += 1
            else:
                self.store.add_relationship(
                    connector_id, target, "connector_evidence", metadata,
                )
                imported += 1
        return {"imported": imported, "connector_id": connector_id}

    def related_weighted(self, path):
        """Return relationships for a path, annotated with confidence weights."""
        document = self.store.get_document(path, include_chunks=False)
        if not document:
            return []
        with self.store.transaction() as connection:
            rows = connection.execute(
                """SELECT target_path, relation, metadata, created_at
                   FROM relationships WHERE source_document_id = ? ORDER BY created_at DESC""",
                (document["id"],),
            ).fetchall()
        result = []
        for row in rows:
            row = dict(row)
            meta = json.loads(row.get("metadata") or "{}") if isinstance(row.get("metadata"), str) else (row.get("metadata") or {})
            weight = self._compute_relationship_weight(meta)
            row["weight"] = weight
            result.append(row)
        return result

    def _compute_relationship_weight(self, metadata):
        base = 1.0
        confidence = metadata.get("confidence")
        if confidence is not None:
            base *= float(confidence)
        if metadata.get("resolution") == "local":
            base *= 1.2
        elif metadata.get("resolution") == "unresolved":
            base *= 0.5
        if metadata.get("relation_type"):
            base *= 1.1
        return round(min(base, 2.0), 2)

    def propagate_confidence(self, paths, initial_confidence=1.0, depth=3):
        """Propagate confidence from a set of paths along graph relationships."""
        propagated = {}
        visited = set()
        queue = [(p, initial_confidence, 0) for p in paths]
        for path, conf, d in queue:
            if path in visited or d > depth:
                continue
            visited.add(path)
            propagated[path] = max(propagated.get(path, 0), conf)
            relations = self.related(path)
            for rel in relations:
                target = rel.get("target_path", "")
                if target and target not in visited:
                    decay = conf * 0.85 ** (d + 1)
                    queue.append((target, decay, d + 1))
        return propagated

    def temporal_relationships(self, path, window_days=30):
        """Return relationships bounded by a recency window."""
        document = self.store.get_document(path, include_chunks=False)
        if not document:
            return []
        with self.store.transaction() as connection:
            rows = connection.execute(
                """SELECT target_path, relation, metadata, created_at
                   FROM relationships WHERE source_document_id = ?
                   AND created_at >= datetime('now', ?)
                   ORDER BY created_at DESC""",
                (document["id"], "-%d days" % window_days),
            ).fetchall()
        return [dict(row) for row in rows]

    def multi_source_correlate(self, connector_ids, relation="connector_evidence"):
        """Correlate evidence across multiple connector sources."""
        if not connector_ids:
            return {}
        placeholders = ",".join("?" for _ in connector_ids)
        with self.store.transaction() as connection:
            rows = connection.execute(
                """SELECT target_path, relation, metadata, created_at
                   FROM relationships
                   WHERE relation = ? AND source_document_id IN (%s)
                   ORDER BY target_path, created_at""" % placeholders,
                (relation, *connector_ids),
            ).fetchall()
        correlation = {}
        for row in rows:
            row = dict(row)
            target = row["target_path"]
            if target not in correlation:
                correlation[target] = []
            correlation[target].append(row)
        return correlation

    def resolve_workspace_imports(self, workspace):
        """Attach local-document evidence to imports after a complete index pass.

        Original import targets are retained. Resolution is only recorded when a
        target maps exactly to an indexed Python module within the workspace.
        """
        workspace = os.path.abspath(workspace)
        with self.store.transaction() as connection:
            documents = [dict(row) for row in connection.execute(
                "SELECT id, path FROM documents WHERE status = 'active' AND path LIKE ?",
                (workspace + "%",),
            )]
            relationships = [dict(row) for row in connection.execute(
                """SELECT relationships.id, documents.path AS source_path,
                   relationships.target_path, relationships.metadata
                   FROM relationships JOIN documents ON documents.id = relationships.source_document_id
                   WHERE relationships.relation = 'imports' AND documents.path LIKE ?""",
                (workspace + "%",),
            )]
            modules = self._workspace_modules(workspace, documents)
            for relationship in relationships:
                metadata = json.loads(relationship["metadata"] or "{}")
                resolved = self._resolve_import(modules, relationship["source_path"], metadata)
                if resolved:
                    metadata["resolved_document_path"] = resolved[1]
                    metadata["resolved_module"] = resolved[0]
                    metadata["resolution"] = "local"
                else:
                    metadata.pop("resolved_document_path", None)
                    metadata.pop("resolved_module", None)
                    metadata["resolution"] = "unresolved"
                connection.execute(
                    "UPDATE relationships SET metadata = ? WHERE id = ?",
                    (json.dumps(metadata, ensure_ascii=False, sort_keys=True), relationship["id"]),
                )

    @staticmethod
    def _workspace_modules(workspace, documents):
        modules = {}
        for document in documents:
            path = document["path"]
            if not path.endswith(".py"):
                continue
            relative = os.path.relpath(path, workspace)
            parts = relative.split(os.sep)
            filename = parts.pop()
            if filename == "__init__.py":
                module_parts = parts
            else:
                module_parts = parts + [os.path.splitext(filename)[0]]
            if module_parts:
                modules[".".join(module_parts)] = path
        return modules

    @staticmethod
    def _resolve_import(modules, source_path, metadata):
        source_module = next((name for name, path in modules.items() if path == source_path), "")
        source_parts = source_module.split(".") if source_module else []
        if not source_path.endswith("__init__.py") and source_parts:
            source_parts.pop()
        level = int(metadata.get("relative", 0) or 0)
        if level:
            source_parts = source_parts[:max(0, len(source_parts) - level + 1)]
        base = metadata.get("module", "")
        imported = metadata.get("imported_name", "")
        prefix = ".".join(part for part in [".".join(source_parts), base] if part)
        candidates = [".".join(part for part in [prefix, imported] if part), prefix]
        for candidate in candidates:
            if candidate in modules:
                return candidate, modules[candidate]
        return None


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
            self.relationships.append((alias.name, "imports", {
                "line": node.lineno, "module": alias.name, "imported_name": "",
                "relative": 0,
            }))

    def visit_ImportFrom(self, node):
        module = node.module or ""
        for alias in node.names:
            target = module + ("." if module else "") + alias.name
            self.relationships.append((target, "imports", {
                "line": node.lineno, "module": module, "imported_name": alias.name,
                "relative": node.level,
            }))

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
