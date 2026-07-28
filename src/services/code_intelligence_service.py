"""CodeIntelligenceService — analyzes source code to enrich the Project Twin
with language detection, source scanning, code knowledge graphs, and
architecture understanding.

No external LLM calls. All analysis is deterministic regex-based scanning
of source files.
"""

import os
import re

from services.service import Service


_LANGUAGE_MAP = {
    ".py": "Python",
    ".dart": "Dart",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".cs": "C#",
    ".go": "Go",
}

_SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", "build", "dist",
    ".dart_tool", ".pub-cache", "coverage", ".idea", ".vscode",
    "packages", ".github", "android", "ios", "vendor",
}

_SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pubspec.lock", "Gemfile.lock",
}

_ARCH_LAYER_PATTERNS = {
    "service": "Service Layer",
    "repository": "Repository Layer",
    "controller": "Controller Layer",
    "provider": "Provider Layer",
    "model": "Data Layer",
    "entity": "Data Layer",
    "view": "Presentation Layer",
    "widget": "Presentation Layer",
    "screen": "Presentation Layer",
    "page": "Presentation Layer",
    "handler": "Handler Layer",
    "middleware": "Middleware Layer",
    "filter": "Middleware Layer",
    "interceptor": "Middleware Layer",
    "helper": "Utility Layer",
    "util": "Utility Layer",
    "utility": "Utility Layer",
    "config": "Configuration Layer",
    "setting": "Configuration Layer",
    "manager": "Manager Layer",
    "engine": "Engine Layer",
    "adapter": "Adapter Layer",
    "factory": "Factory Layer",
    "mapper": "Mapper Layer",
    "dto": "Data Layer",
    "request": "Data Layer",
    "response": "Data Layer",
    "command": "Command Layer",
    "event": "Event Layer",
    "listener": "Event Layer",
    "observer": "Observer Layer",
    "decorator": "Decorator Layer",
}


class CodeIntelligenceService(Service):
    """Analyzes project source code to extract language, structure,
    dependencies, and architecture understanding."""

    def __init__(self, kernel):
        super().__init__(kernel)
        self._analysis_cache = {}

    def start(self):
        super().start()

    def clear_cache(self):
        self._analysis_cache = {}

    def has_analysis(self):
        return bool(self._analysis_cache)

    # ------------------------------------------------------------------
    # 1. Main entry point
    # ------------------------------------------------------------------

    def analyze_project(self, project_path):
        """Detect languages, scan sources, build knowledge graph,
        detect architecture.

        Returns a code_summary dict with all analysis data.
        """
        if not project_path or not os.path.isdir(project_path):
            return {"error": "Invalid project path"}
        resolved = os.path.abspath(project_path)
        if resolved in self._analysis_cache:
            return self._analysis_cache[resolved]

        languages = self.detect_languages(project_path)
        scan_result = self.scan_sources(project_path)
        code_graph = self.build_code_graph(scan_result)
        arch_layers = self.analyze_code_architecture(scan_result)
        entry_points = self._find_entry_points(project_path)
        important_files = self._find_important_files(scan_result)
        complexity = self._estimate_complexity(scan_result)

        result = {
            "languages": languages,
            "components": scan_result.get("all_classes", []),
            "architecture_layers": arch_layers,
            "complexity": complexity,
            "entry_points": entry_points,
            "important_files": important_files,
            "code_graph": code_graph,
            "all_classes": scan_result.get("all_classes", []),
            "all_functions": scan_result.get("all_functions", []),
            "all_imports": scan_result.get("all_imports", []),
            "files": scan_result.get("files", []),
            "module_structure": scan_result.get("module_structure", {}),
        }
        self._analysis_cache[resolved] = result
        return result

    # ------------------------------------------------------------------
    # 2. Language Detection
    # ------------------------------------------------------------------

    def detect_languages(self, project_path):
        ext_counts = {}
        total = 0
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
            for f in files:
                if f in _SKIP_FILES:
                    continue
                ext = os.path.splitext(f)[1].lower()
                if ext in _LANGUAGE_MAP:
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1
                    total += 1
        if total == 0:
            return []
        languages = []
        for ext, lang in sorted(_LANGUAGE_MAP.items(), key=lambda x: -ext_counts.get(x[0], 0)):
            count = ext_counts.get(ext, 0)
            if count > 0:
                languages.append({
                    "name": lang,
                    "files": count,
                    "percentage": round(count / total * 100, 1),
                })
        return languages

    # ------------------------------------------------------------------
    # 3. Source Code Scanning
    # ------------------------------------------------------------------

    def scan_sources(self, project_path):
        files = []
        all_classes = []
        all_functions = []
        all_imports = []
        module_structure = {}

        for root, dirs, filenames in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
            for fname in filenames:
                if fname in _SKIP_FILES:
                    continue
                ext = os.path.splitext(fname)[1].lower()
                if ext not in _LANGUAGE_MAP:
                    continue
                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath, project_path)
                lang = _LANGUAGE_MAP[ext]

                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                except Exception:
                    continue

                classes = self._extract_classes(content, lang)
                functions = self._extract_functions(content, lang)
                imports = self._extract_imports(content, lang)

                parts = rel_path.replace("\\", "/").split("/")
                if len(parts) > 1:
                    mod = parts[0]
                    module_structure.setdefault(mod, {"files": 0, "classes": 0, "functions": 0})
                    module_structure[mod]["files"] += 1
                    module_structure[mod]["classes"] += len(classes)
                    module_structure[mod]["functions"] += len(functions)

                file_info = {
                    "path": rel_path,
                    "language": lang,
                    "classes": classes,
                    "functions": functions,
                    "imports": imports,
                    "lines": len(content.splitlines()),
                }
                files.append(file_info)
                all_classes.extend([{"name": c, "file": rel_path, "language": lang} for c in classes])
                all_functions.extend([{"name": fn, "file": rel_path, "language": lang} for fn in functions])
                all_imports.extend([{"source": imp, "file": rel_path} for imp in imports])

        return {
            "files": files,
            "all_classes": all_classes,
            "all_functions": all_functions,
            "all_imports": all_imports,
            "module_structure": module_structure,
        }

    _CLASS_RE = re.compile(
        r'(?:^|\n)\s*(?:public\s+|private\s+|protected\s+'
        r'|internal\s+|abstract\s+|static\s+|sealed\s+)*'
        r'(?:class|interface|struct|enum|trait)\s+(\w+)',
        re.MULTILINE,
    )

    def _extract_classes(self, content, language):
        return [m.group(1) for m in self._CLASS_RE.finditer(content)]

    def _extract_functions(self, content, language):
        functions = []
        if language == "Python":
            for m in re.finditer(r'(?:^|\n)\s*async\s+def\s+(\w+)\s*\(', content, re.MULTILINE):
                functions.append(m.group(1))
            for m in re.finditer(r'(?:^|\n)\s*def\s+(\w+)\s*\(', content, re.MULTILINE):
                functions.append(m.group(1))
        elif language == "Dart":
            for m in re.finditer(
                r'(?:^|\n)\s*(?:\w+\s+)?(\w+)\s*\([^)]*\)\s*(?:\{|=>)',
                content,
            ):
                name = m.group(1)
                if name and not name.startswith(("if", "for", "while", "switch", "catch")):
                    functions.append(name)
        elif language in ("JavaScript", "TypeScript"):
            for m in re.finditer(
                r'(?:^|\n)\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(',
                content,
            ):
                functions.append(m.group(1))
            for m in re.finditer(
                r'(?:^|\n)\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\(|=>)',
                content,
            ):
                functions.append(m.group(1))
        elif language in ("Java", "C#"):
            for m in re.finditer(
                r'^\s*(?:public|private|protected|internal|static|'
                r'virtual|override|abstract|async)\s+(?:\w+(?:<[^>]*>)?\s+)*(\w+)\s*\(',
                content,
                re.MULTILINE,
            ):
                name = m.group(1)
                if name and name not in (
                    "if", "for", "while", "switch", "catch", "return",
                    "new", "throw", "out", "ref",
                ):
                    functions.append(name)
        elif language == "Go":
            for m in re.finditer(
                r'(?:^|\n)\s*func\s+(?:\([^)]*\)\s+)?(\w+)\s*\(',
                content,
            ):
                functions.append(m.group(1))
        return functions

    def _extract_imports(self, content, language):
        imports = []
        if language == "Python":
            for m in re.finditer(r'^import\s+(\w+(?:\.\w+)*)', content, re.MULTILINE):
                imports.append(m.group(1))
            for m in re.finditer(r'^from\s+(\w+(?:\.\w+)*)\s+import', content, re.MULTILINE):
                imports.append(m.group(1))
        elif language == "Dart":
            for m in re.finditer(r"""^import\s+['"]([\w/.\-_]+)['"]""", content, re.MULTILINE):
                imports.append(m.group(1))
        elif language in ("JavaScript", "TypeScript"):
            for m in re.finditer(
                r"""import\s+(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)\s+from\s+['"]([^'"]+)['"]""",
                content,
            ):
                imports.append(m.group(1))
            for m in re.finditer(
                r"""(?:const|let|var)\s+\w+\s*=\s*require\s*\(\s*['"]([^'"]+)['"]\s*\)""",
                content,
            ):
                imports.append(m.group(1))
        elif language == "Java":
            for m in re.finditer(r'^import\s+([\w.]+);', content, re.MULTILINE):
                imports.append(m.group(1))
        elif language == "C#":
            for m in re.finditer(r'^using\s+([\w.]+);', content, re.MULTILINE):
                imports.append(m.group(1))
        elif language == "Go":
            for m in re.finditer(r'^import\s+["]([\w/.\-]+)["]', content, re.MULTILINE):
                imports.append(m.group(1))
            for m in re.finditer(r'import\s*\(([^)]+)\)', content, re.DOTALL):
                for im in re.finditer(r"""["]([\w/.\-]+)["]""", m.group(1)):
                    imports.append(im.group(1))
        return imports

    # ------------------------------------------------------------------
    # 4. Code Knowledge Graph
    # ------------------------------------------------------------------

    def build_code_graph(self, scan_result):
        nodes = []
        edges = []
        seen_nodes = set()

        for mod_name in scan_result.get("module_structure", {}):
            if mod_name not in seen_nodes:
                nodes.append({"name": mod_name, "type": "module"})
                seen_nodes.add(mod_name)

        for cls in scan_result.get("all_classes", []):
            name = cls["name"]
            if name not in seen_nodes:
                nodes.append({"name": name, "type": "class"})
                seen_nodes.add(name)

        for imp in scan_result.get("all_imports", []):
            source_module = imp["source"].split(".")[0]
            parts = imp["file"].replace("\\", "/").split("/")
            target_mod = parts[0] if len(parts) > 1 else "root"
            edges.append({
                "from": target_mod,
                "to": source_module,
                "relation": "imports",
            })

        for cls in scan_result.get("all_classes", []):
            parts = cls["file"].replace("\\", "/").split("/")
            mod = parts[0] if len(parts) > 1 else "root"
            edges.append({
                "from": cls["name"],
                "to": mod,
                "relation": "defined_in",
            })

        return {"nodes": nodes, "edges": edges}

    # ------------------------------------------------------------------
    # 5. Architecture Understanding
    # ------------------------------------------------------------------

    def analyze_code_architecture(self, scan_result):
        layer_map = {}
        for finfo in scan_result.get("files", []):
            fname_lower = finfo["path"].lower()
            detected_layers = set()
            for pattern, layer in _ARCH_LAYER_PATTERNS.items():
                if pattern in fname_lower:
                    detected_layers.add(layer)
                for cls in finfo.get("classes", []):
                    if pattern in cls.lower():
                        detected_layers.add(layer)
            for l in detected_layers:
                layer_map.setdefault(l, []).append(finfo["path"])

        arch_layers = []
        for layer_name in sorted(layer_map.keys()):
            files = layer_map[layer_name]
            arch_layers.append({
                "layer": layer_name,
                "files": files[:20],
                "count": len(files),
            })
        return arch_layers

    # ------------------------------------------------------------------
    # 6. Helper Methods
    # ------------------------------------------------------------------

    def _find_entry_points(self, project_path):
        entry_patterns = [
            "main.py", "main.dart", "main.js", "main.ts",
            "app.py", "app.js", "app.ts",
            "index.js", "index.ts",
            "lib/main.dart",
        ]
        entry_points = []
        for pattern in entry_patterns:
            fpath = os.path.join(project_path, pattern)
            alt_path = os.path.join(project_path, "src", pattern)
            if os.path.isfile(fpath):
                entry_points.append(pattern)
            elif os.path.isfile(alt_path):
                entry_points.append("src/" + pattern)
        return entry_points

    def _find_important_files(self, scan_result):
        scored = []
        for finfo in scan_result.get("files", []):
            score = (
                len(finfo.get("classes", [])) * 3
                + len(finfo.get("imports", [])) * 1
                + (finfo.get("lines", 0) / 100)
            )
            scored.append((score, finfo["path"], finfo.get("classes", [])[:3]))
        scored.sort(reverse=True)
        important = []
        for s, p, cls in scored[:10]:
            important.append({"path": p, "classes": cls, "score": round(s, 1)})
        return important

    def _estimate_complexity(self, scan_result):
        files = scan_result.get("files", [])
        total_classes = len(scan_result.get("all_classes", []))
        total_lines = sum(f.get("lines", 0) for f in files)
        if total_lines > 50000 or total_classes > 200:
            return "high"
        elif total_lines > 10000 or total_classes > 50:
            return "medium"
        return "low"

    # ------------------------------------------------------------------
    # 7. Code Query
    # ------------------------------------------------------------------

    def code_query(self, question, project_path=None):
        if not self._analysis_cache and project_path:
            self.analyze_project(project_path)

        if not self._analysis_cache:
            return {
                "answer": "No project analyzed. Provide a project path first.",
                "evidence": [],
                "confidence": "none",
            }

        last = list(self._analysis_cache.values())[-1]
        if "error" in last:
            return {"answer": last["error"], "evidence": [], "confidence": "none"}

        q = question.lower().strip()

        if any(kw in q for kw in ("class", "classes", "what classes")):
            return self._answer_classes(last)
        if any(kw in q for kw in ("function", "method", "functions", "methods")):
            return self._answer_functions(last)
        if any(kw in q for kw in ("language", "languages", "programming")):
            return self._answer_languages(last)
        if any(kw in q for kw in ("dependency", "import", "dependencies", "imports")):
            return self._answer_imports(last)
        if any(kw in q for kw in ("graph", "node", "edge", "knowledge graph")):
            return self._answer_graph(last)
        if any(kw in q for kw in (
            "architecture", "layer", "service layer", "repository", "controller",
        )):
            return self._answer_architecture(last)
        if any(kw in q for kw in ("entry", "main", "start", "begin")):
            return self._answer_entry_points(last)
        if any(kw in q for kw in ("file", "important", "important files")):
            return self._answer_important_files(last)
        if any(kw in q for kw in ("complexity", "size", "large", "big")):
            return self._answer_complexity(last)
        if any(kw in q for kw in ("component", "module", "part")):
            return self._answer_components(last)
        if any(kw in q for kw in ("overview", "summary", "explain", "describe", "about")):
            return self._answer_code_overview(last)

        result = self._search_code(q, last)
        if result:
            return result

        return {
            "answer": (
                "I don't understand that code question. "
                "Try: classes, functions, languages, imports, graph, "
                "architecture, entry points, important files, "
                "complexity, components, or overview."
            ),
            "evidence": [],
            "confidence": "none",
        }

    def _search_code(self, query, analysis):
        """Search code entities by keyword (e.g. 'authentication')."""
        results = []
        seen = set()
        # Search by individual keywords
        words = [w for w in query.split() if len(w) > 2]

        for cls in analysis.get("all_classes", []):
            for w in words:
                if w in cls["name"].lower() or w in cls["file"].lower():
                    key = ("class", cls["name"], cls["file"])
                    if key not in seen:
                        seen.add(key)
                        results.append({
                            "type": "class", "name": cls["name"], "file": cls["file"],
                        })
                    break

        for fn in analysis.get("all_functions", []):
            for w in words:
                if w in fn["name"].lower() or w in fn["file"].lower():
                    key = ("function", fn["name"], fn["file"])
                    if key not in seen:
                        seen.add(key)
                        results.append({
                            "type": "function", "name": fn["name"], "file": fn["file"],
                        })
                    break

        for f in analysis.get("files", []):
            p = f["path"].lower()
            for w in words:
                if w in p and f["path"] not in {r["file"] for r in results}:
                    results.append({
                        "type": "file", "name": f["path"], "file": f["path"],
                    })
                    break

        if not results:
            return None

        parts = [f"Found {len(results)} result(s) for '{query}':"]
        for r in results[:20]:
            parts.append(f"  [{r['type']}] {r['name']} ({r['file']})")
        evidence = [
            {
                "type": "code_intelligence",
                "source": "code_search",
                "detail": f"{len(results)} results for '{query}'",
            },
        ]
        return {"answer": "\n".join(parts), "evidence": evidence, "confidence": "high"}

    # ------------------------------------------------------------------
    # Question handlers
    # ------------------------------------------------------------------

    def _answer_code_overview(self, analysis):
        langs = analysis.get("languages", [])
        comps = analysis.get("components", [])
        layers = analysis.get("architecture_layers", [])
        entry = analysis.get("entry_points", [])
        complexity = analysis.get("complexity", "unknown")

        parts = ["Code Intelligence Analysis:"]
        if langs:
            lang_strs = [
                f"{l['name']} ({l['files']} files, {l['percentage']}%)"
                for l in langs
            ]
            parts.append(f"Languages: {', '.join(lang_strs)}.")
        parts.append(f"Classes/Interfaces: {len(comps)}.")
        parts.append(f"Architecture layers detected: {len(layers)}.")
        if entry:
            parts.append(f"Entry points: {', '.join(entry)}.")
        parts.append(f"Complexity: {complexity}.")

        evidence = [
            {"type": "code_intelligence", "source": "language_detection",
             "detail": f"{len(langs)} language(s)"},
            {"type": "code_intelligence", "source": "source_scanning",
             "detail": f"{len(comps)} class(es)"},
            {"type": "code_intelligence", "source": "architecture_detection",
             "detail": f"{len(layers)} layer(s)"},
        ]
        return {"answer": " ".join(parts), "evidence": evidence, "confidence": "high"}

    def _answer_classes(self, analysis):
        classes = analysis.get("all_classes", [])
        if not classes:
            return {"answer": "No classes or interfaces detected.", "evidence": [], "confidence": "low"}
        file_classes = {}
        for c in classes:
            file_classes.setdefault(c.get("file", "unknown"), []).append(c["name"])
        parts = [
            f"Detected {len(classes)} classes/interfaces across "
            f"{len(file_classes)} file(s):",
        ]
        for f, cls_list in sorted(file_classes.items()):
            display = ", ".join(cls_list[:5])
            if len(cls_list) > 5:
                display += "..."
            parts.append(f"  {f}: {display}")
        evidence = [
            {"type": "code_intelligence", "source": "source_scanning",
             "detail": f"{len(classes)} classes"},
        ]
        return {"answer": "\n".join(parts), "evidence": evidence, "confidence": "high"}

    def _answer_functions(self, analysis):
        functions = analysis.get("all_functions", [])
        if not functions:
            return {"answer": "No functions or methods detected.", "evidence": [], "confidence": "low"}
        file_fns = {}
        for fn in functions:
            file_fns.setdefault(fn.get("file", "unknown"), []).append(fn["name"])
        parts = [
            f"Detected {len(functions)} functions/methods across "
            f"{len(file_fns)} file(s):",
        ]
        for f, fn_list in sorted(file_fns.items()):
            display = ", ".join(fn_list[:8])
            if len(fn_list) > 8:
                display += "..."
            parts.append(f"  {f}: {display}")
        evidence = [
            {"type": "code_intelligence", "source": "source_scanning",
             "detail": f"{len(functions)} functions"},
        ]
        return {"answer": "\n".join(parts), "evidence": evidence, "confidence": "high"}

    def _answer_languages(self, analysis):
        langs = analysis.get("languages", [])
        if not langs:
            return {"answer": "No programming languages detected.", "evidence": [], "confidence": "low"}
        parts = [f"Detected {len(langs)} programming language(s):"]
        for l in langs:
            parts.append(f"  {l['name']}: {l['files']} files ({l['percentage']}%)")
        evidence = [
            {"type": "code_intelligence", "source": "language_detection",
             "detail": str(langs)},
        ]
        return {"answer": "\n".join(parts), "evidence": evidence, "confidence": "high"}

    def _answer_imports(self, analysis):
        imports = analysis.get("all_imports", [])
        if not imports:
            return {"answer": "No imports detected.", "evidence": [], "confidence": "low"}
        # Count unique import sources
        sources = {}
        for imp in imports:
            s = imp["source"]
            sources[s] = sources.get(s, 0) + 1
        sorted_sources = sorted(sources.items(), key=lambda x: -x[1])
        parts = [
            f"Detected {len(imports)} import(s) across "
            f"{len(sources)} unique source(s):",
        ]
        for src, cnt in sorted_sources[:15]:
            parts.append(f"  {src} ({cnt} use(s))")
        evidence = [
            {"type": "code_intelligence", "source": "import_analysis",
             "detail": f"{len(imports)} imports"},
        ]
        return {"answer": "\n".join(parts), "evidence": evidence, "confidence": "high"}

    def _answer_graph(self, analysis):
        graph = analysis.get("code_graph", {})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        if not nodes and not edges:
            return {"answer": "No code graph available.", "evidence": [], "confidence": "low"}
        parts = [
            f"Code knowledge graph with {len(nodes)} node(s) and "
            f"{len(edges)} edge(s):",
        ]
        if nodes:
            class_nodes = [n["name"] for n in nodes if n["type"] == "class"]
            mod_nodes = [n["name"] for n in nodes if n["type"] == "module"]
            parts.append(f"  Classes: {len(class_nodes)}. Modules: {len(mod_nodes)}.")
        evidence = [
            {"type": "code_intelligence", "source": "code_graph",
             "detail": f"{len(nodes)} nodes, {len(edges)} edges"},
        ]
        return {"answer": "\n".join(parts), "evidence": evidence, "confidence": "high"}

    def _answer_architecture(self, analysis):
        layers = analysis.get("architecture_layers", [])
        if not layers:
            return {"answer": "No architecture layers detected.", "evidence": [], "confidence": "low"}
        parts = [f"Detected {len(layers)} architecture layer(s):"]
        for l in layers:
            parts.append(f"  {l['layer']}: {l['count']} file(s)")
            for f in l["files"][:3]:
                parts.append(f"    - {f}")
        evidence = [
            {"type": "code_intelligence", "source": "architecture_detection",
             "detail": str([l["layer"] for l in layers])},
        ]
        return {"answer": "\n".join(parts), "evidence": evidence, "confidence": "high"}

    def _answer_entry_points(self, analysis):
        entry = analysis.get("entry_points", [])
        if not entry:
            return {"answer": "No entry points detected.", "evidence": [], "confidence": "low"}
        parts = [f"Entry points ({len(entry)}):"]
        for e in entry:
            parts.append(f"  {e}")
        evidence = [
            {"type": "code_intelligence", "source": "entry_point_detection",
             "detail": str(entry)},
        ]
        return {"answer": "\n".join(parts), "evidence": evidence, "confidence": "high"}

    def _answer_important_files(self, analysis):
        files = analysis.get("important_files", [])
        if not files:
            return {"answer": "No important files identified.", "evidence": [], "confidence": "low"}
        parts = [f"Top {len(files)} important file(s):"]
        for f in files:
            cls_str = ", ".join(f.get("classes", []))
            parts.append(
                f"  {f['path']} (score: {f['score']})"
                + (f" — classes: {cls_str}" if cls_str else "")
            )
        evidence = [
            {"type": "code_intelligence", "source": "importance_scoring",
             "detail": f"{len(files)} files"},
        ]
        return {"answer": "\n".join(parts), "evidence": evidence, "confidence": "high"}

    def _answer_complexity(self, analysis):
        complexity = analysis.get("complexity", "unknown")
        files = analysis.get("files", [])
        total_lines = sum(f.get("lines", 0) for f in files)
        total_classes = len(analysis.get("all_classes", []))
        total_functions = len(analysis.get("all_functions", []))
        total_files = len(files)
        parts = [
            f"Complexity: {complexity}.",
            f"Files: {total_files}, Lines: {total_lines}, "
            f"Classes: {total_classes}, Functions: {total_functions}.",
        ]
        evidence = [
            {"type": "code_intelligence", "source": "complexity_estimation",
             "detail": f"complexity={complexity}, lines={total_lines}"},
        ]
        return {"answer": " ".join(parts), "evidence": evidence, "confidence": "high"}

    def _answer_components(self, analysis):
        mod_structure = analysis.get("module_structure", {})
        if not mod_structure:
            return {"answer": "No modules or components detected.", "evidence": [], "confidence": "low"}
        parts = [f"Detected {len(mod_structure)} module(s):"]
        for mod, info in sorted(mod_structure.items()):
            parts.append(
                f"  {mod}: {info['files']} file(s), "
                f"{info['classes']} class(es), {info['functions']} function(s)"
            )
        evidence = [
            {"type": "code_intelligence", "source": "module_analysis",
             "detail": f"{len(mod_structure)} modules"},
        ]
        return {"answer": "\n".join(parts), "evidence": evidence, "confidence": "high"}
