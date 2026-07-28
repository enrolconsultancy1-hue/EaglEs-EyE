"""LocalProjectConnector — discovers project identity, structure, and stack from
a local project folder. Creates a Project Twin representation.

Complies with Universal Observation Policy and Universal Connector Framework.
"""

import os
import re
import json
import hashlib
import collections

from connectors.connector import Connector
from connectors.health import ConnectorState
from connectors.models import (
    Source, RawPayload, Observation, Evidence, NormalizedPayload,
    Artifact, TraceInformation,
)
from connectors.observation_discovery import (
    ObservationSurface, ObservationDiscoveryEngine, SurfaceQuality,
    EvidenceQuality, LatencyClass, Completeness, Reliability,
)


PROJECT_INDICATORS = {
    "Flutter Application": {
        "markers": ["pubspec.yaml", "lib/main.dart"],
        "languages": {"Dart"},
        "frameworks": {"Flutter"},
        "dep_files": ["pubspec.yaml"],
    },
    "Python Application": {
        "markers": ["setup.py", "pyproject.toml", "requirements.txt", "Pipfile"],
        "languages": {"Python"},
        "frameworks": set(),
        "dep_files": ["requirements.txt", "Pipfile", "pyproject.toml", "setup.py"],
    },
    "Node.js Application": {
        "markers": ["package.json"],
        "languages": {"JavaScript", "TypeScript"},
        "frameworks": {"Node.js"},
        "dep_files": ["package.json"],
    },
    "React Application": {
        "markers": ["package.json"],
        "languages": {"JavaScript", "TypeScript"},
        "frameworks": {"React", "Node.js"},
        "dep_files": ["package.json"],
    },
    "Java Application": {
        "markers": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "languages": {"Java", "Kotlin"},
        "frameworks": set(),
        "dep_files": ["pom.xml", "build.gradle"],
    },
    "Rust Application": {
        "markers": ["Cargo.toml"],
        "languages": {"Rust"},
        "frameworks": set(),
        "dep_files": ["Cargo.toml"],
    },
    "Go Application": {
        "markers": ["go.mod"],
        "languages": {"Go"},
        "frameworks": set(),
        "dep_files": ["go.mod"],
    },
    ".NET Application": {
        "markers": ["*.csproj", "*.sln"],
        "languages": {"C#"},
        "frameworks": {".NET"},
        "dep_files": ["*.csproj"],
    },
}


class LocalProjectConnector(Connector):
    id = "local_project"
    name = "Local Project Connector"
    version = "1.0.0"
    vendor = "EaglEs EyE"
    description = "Discovers project identity, structure, and technology stack from local folders"
    capabilities = ["filesystem", "documents", "project_discovery"]
    permissions = ["read", "observe"]

    def __init__(self, config=None):
        super().__init__(config)
        self._project_path = self.config.get("project_path", "")
        self._discovery_result = None

    def connect(self) -> bool:
        if not self._project_path or not os.path.isdir(self._project_path):
            self._health.state = ConnectorState.ERROR
            return False
        self._health.state = ConnectorState.CONNECTED
        return True

    def disconnect(self) -> bool:
        self._discovery_result = None
        self._health.state = ConnectorState.DISCONNECTED
        return True

    def discover(self) -> list:
        if not self._project_path or not os.path.isdir(self._project_path):
            return []
        return [Source.create(type_="local_project", path=self._project_path)]

    def _detect_project_type(self):
        for ptype, info in PROJECT_INDICATORS.items():
            for marker in info["markers"]:
                if "*" in marker:
                    pattern = marker.replace("*", "")
                    if any(f.endswith(pattern) for f in os.listdir(self._project_path)):
                        return ptype, info
                else:
                    if os.path.isfile(os.path.join(self._project_path, marker)):
                        return ptype, info
        # Recursive fallback: search subdirectories for markers
        for root, dirs, files in self._walk():
            if root == self._project_path:
                continue
            for ptype, info in PROJECT_INDICATORS.items():
                for marker in info["markers"]:
                    if "*" not in marker and os.path.isfile(os.path.join(root, marker)):
                        return ptype, info
        return "Unknown Project", {
            "languages": set(),
            "frameworks": set(),
            "dep_files": [],
        }

    def _detect_languages(self, type_info):
        langs = set(type_info.get("languages", []))
        if os.path.isfile(os.path.join(self._project_path, "pubspec.yaml")):
            langs.add("Dart")
        for f in os.listdir(self._project_path):
            if f.endswith(".py"):
                langs.add("Python")
            elif f.endswith(".js") or f.endswith(".jsx"):
                langs.add("JavaScript")
            elif f.endswith(".ts") or f.endswith(".tsx"):
                langs.add("TypeScript")
            elif f.endswith(".java"):
                langs.add("Java")
            elif f.endswith(".rs"):
                langs.add("Rust")
            elif f.endswith(".go"):
                langs.add("Go")
            elif f.endswith(".cs"):
                langs.add("C#")
            elif f.endswith(".kt") or f.endswith(".kts"):
                langs.add("Kotlin")
            elif f.endswith(".swift"):
                langs.add("Swift")
        # Walk deeper for more language detection
        for root, dirs, files in os.walk(self._project_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules" and d != "build" and d != ".dart_tool"]
            for f in files:
                if f.endswith(".py"):
                    langs.add("Python")
                elif f.endswith(".dart"):
                    langs.add("Dart")
                elif f.endswith((".js", ".jsx")):
                    langs.add("JavaScript")
                elif f.endswith((".ts", ".tsx")):
                    langs.add("TypeScript")
                elif f.endswith(".java"):
                    langs.add("Java")
                elif f.endswith(".rs"):
                    langs.add("Rust")
                elif f.endswith(".go"):
                    langs.add("Go")
                elif f.endswith(".cs"):
                    langs.add("C#")
                elif f.endswith((".kt", ".kts")):
                    langs.add("Kotlin")
                elif f.endswith(".swift"):
                    langs.add("Swift")
                elif f.endswith(".rb"):
                    langs.add("Ruby")
                elif f.endswith(".php"):
                    langs.add("PHP")
                elif f.endswith(".yaml") or f.endswith(".yml"):
                    langs.add("YAML")
                elif f.endswith(".json"):
                    langs.add("JSON")
        return sorted(langs)

    def _detect_frameworks(self, type_info):
        frameworks = set(type_info.get("frameworks", []))
        pubspec_path = os.path.join(self._project_path, "pubspec.yaml")
        if os.path.isfile(pubspec_path):
            try:
                with open(pubspec_path, encoding="utf-8") as f:
                    content = f.read()
                if "firebase" in content.lower():
                    frameworks.add("Firebase")
                if "flutter" in content.lower():
                    frameworks.add("Flutter")
            except Exception:
                pass
        package_path = os.path.join(self._project_path, "package.json")
        if os.path.isfile(package_path):
            try:
                with open(package_path, encoding="utf-8") as f:
                    pkg = json.load(f)
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "react" in deps:
                    frameworks.add("React")
                if "vue" in deps:
                    frameworks.add("Vue")
                if "express" in deps:
                    frameworks.add("Express")
                if "next" in deps:
                    frameworks.add("Next.js")
                if "angular" in deps or "@angular/core" in deps:
                    frameworks.add("Angular")
                if "firebase" in deps:
                    frameworks.add("Firebase")
            except Exception:
                pass
        # Recursive scan: find manifest files in subdirectories
        for root, dirs, files in self._walk():
            if root == self._project_path:
                continue
            for f in files:
                if f == "pubspec.yaml":
                    try:
                        with open(os.path.join(root, f), encoding="utf-8") as fh:
                            content = fh.read()
                        if "firebase" in content.lower():
                            frameworks.add("Firebase")
                        if "flutter" in content.lower():
                            frameworks.add("Flutter")
                    except Exception:
                        pass
                elif f == "package.json":
                    try:
                        with open(os.path.join(root, f), encoding="utf-8") as fh:
                            pkg = json.load(fh)
                        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                        if "react" in deps:
                            frameworks.add("React")
                        if "vue" in deps:
                            frameworks.add("Vue")
                        if "express" in deps:
                            frameworks.add("Express")
                        if "next" in deps:
                            frameworks.add("Next.js")
                        if "angular" in deps or "@angular/core" in deps:
                            frameworks.add("Angular")
                        if "firebase" in deps:
                            frameworks.add("Firebase")
                    except Exception:
                        pass
        return sorted(frameworks)

    def _detect_git(self):
        git_dir = os.path.join(self._project_path, ".git")
        return os.path.isdir(git_dir)

    def _extract_dependencies(self, type_info):
        deps = set()

        def _do_extract(path, dep_file):
            try:
                if dep_file == "pubspec.yaml" and os.path.isfile(path):
                    with open(path, encoding="utf-8") as f:
                        for line in f:
                            m = re.match(r'^  (\S+):', line)
                            if m:
                                deps.add(m.group(1))
                elif dep_file == "package.json" and os.path.isfile(path):
                    with open(path, encoding="utf-8") as f:
                        pkg = json.load(f)
                    deps.update(pkg.get("dependencies", {}).keys())
                    deps.update(pkg.get("devDependencies", {}).keys())
                elif dep_file == "requirements.txt" and os.path.isfile(path):
                    with open(path, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#"):
                                m = re.match(r'^([a-zA-Z0-9_.-]+)', line)
                                if m:
                                    deps.add(m.group(1))
                elif dep_file in ("Cargo.toml", "go.mod") and os.path.isfile(path):
                    with open(path, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and not line.startswith("["):
                                m = re.match(r'^(\S+)', line)
                                if m and m.group(1) not in ("edition", "name", "version"):
                                    deps.add(m.group(1))
            except Exception:
                pass

        for dep_file in type_info.get("dep_files", []):
            # Root-level manifest
            _do_extract(os.path.join(self._project_path, dep_file), dep_file)
            # Recursive: find same dep_file in subdirectories
            for root, dirs, files in self._walk():
                if root == self._project_path:
                    continue
                if dep_file in files:
                    _do_extract(os.path.join(root, dep_file), dep_file)
        return sorted(deps)

    def _walk(self):
        """Generator yielding (root, dirs, files) with standard exclusions."""
        for root, dirs, files in os.walk(self._project_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules" and d != "build" and d != ".dart_tool"]
            yield root, dirs, files

    def _count_files(self):
        count = 0
        for root, dirs, files in self._walk():
            count += len(files)
        return count

    def _discover_documentation(self):
        """Find and categorise documentation files; extract README summary."""
        docs = []
        summary = ""
        arch_topic = ""
        for root, dirs, files in self._walk():
            for f in files:
                if not f.endswith((".md", ".rst", ".txt")):
                    continue
                path = os.path.join(root, f)
                rel = os.path.relpath(path, self._project_path)
                try:
                    with open(path, encoding="utf-8", errors="replace") as fh:
                        content = fh.read()
                except Exception:
                    continue
                fl = f.lower()
                lines = content.strip().split("\n")
                first_heading = ""
                first_para = ""
                for line in lines:
                    s = line.strip()
                    if s.startswith("# ") or s.startswith("## "):
                        if not first_heading:
                            first_heading = s.lstrip("#").strip()
                    if not s.startswith("#") and not s.startswith("!") and len(s) > 20:
                        if not first_para:
                            first_para = s[:300]
                if fl == "readme.md":
                    role = "readme"
                    summary = first_para or first_heading
                elif "architecture" in fl:
                    role = "architecture"
                    arch_topic = first_heading
                elif fl in ("changelog.md", "change_log.md", "history.md"):
                    role = "changelog"
                elif fl in ("contributing.md", "contributing.rst"):
                    role = "contributing"
                elif fl in ("license", "license.md", "license.txt", "copying"):
                    role = "license"
                elif fl in ("code_of_conduct.md", "conduct.md"):
                    role = "code_of_conduct"
                elif fl in ("security.md",):
                    role = "security"
                else:
                    role = "documentation"
                docs.append({
                    "path": rel, "role": role, "size": len(content),
                    "heading": first_heading, "preview": first_para,
                })
        return {
            "files": docs, "count": len(docs),
            "summary": summary, "architecture_topic": arch_topic,
        }

    def _detect_yaml_configs(self):
        """Detect YAML configuration files and categorise by purpose."""
        configs = []
        ci_types = set()
        for root, dirs, files in self._walk():
            for f in files:
                if not f.endswith((".yaml", ".yml")):
                    continue
                path = os.path.join(root, f)
                rel = os.path.relpath(path, self._project_path)
                fl = f.lower()
                if fl == "pubspec.yaml":
                    continue
                purpose = "configuration"
                if "docker-compose" in fl or fl in ("docker-compose.yml", "compose.yaml"):
                    purpose = "docker"
                elif ".github" in rel.replace("\\", "/").split("/") or "github" in fl:
                    purpose = "ci"
                    ci_types.add("GitHub Actions")
                elif "gitlab" in fl:
                    purpose = "ci"
                    ci_types.add("GitLab CI")
                elif "circleci" in fl or "circle" in fl:
                    purpose = "ci"
                    ci_types.add("CircleCI")
                elif "k8s" in fl or "kubernetes" in fl or "deployment" in fl:
                    purpose = "kubernetes"
                elif "helm" in fl or "chart" in fl:
                    purpose = "helm"
                elif "ansible" in rel.replace("\\", "/").split("/"):
                    purpose = "ansible"
                elif "terraform" in fl:
                    purpose = "terraform"
                configs.append({"path": rel, "purpose": purpose})
        return {"files": configs, "count": len(configs), "ci_types": sorted(ci_types)}

    def _detect_additional_frameworks(self):
        """Detect frameworks and tooling not covered by type_info markers."""
        detected = set()
        project = self._project_path
        # Containerisation
        if os.path.isfile(os.path.join(project, "Dockerfile")):
            detected.add("Docker")
        for fn in ("docker-compose.yml", "docker-compose.yaml", "compose.yaml"):
            if os.path.isfile(os.path.join(project, fn)):
                detected.add("Docker Compose")
        # CI / task runners
        if os.path.isdir(os.path.join(project, ".github")):
            detected.add("GitHub Actions")
        if os.path.isfile(os.path.join(project, "Makefile")):
            detected.add("Make")
        if os.path.isfile(os.path.join(project, "Dockerfile")):
            detected.add("Docker")
        # Python frameworks via setup.py / pyproject.toml
        for fn in ("setup.py", "pyproject.toml"):
            path = os.path.join(project, fn)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    text = f.read().lower()
            except Exception:
                continue
            if "django" in text:
                detected.add("Django")
            if "flask" in text:
                detected.add("Flask")
            if "fastapi" in text:
                detected.add("FastAPI")
            if "pytest" in text:
                detected.add("pytest")
            if "celery" in text:
                detected.add("Celery")
            if "sqlalchemy" in text:
                detected.add("SQLAlchemy")
            if "tensorflow" in text or "torch" in text or "keras" in text:
                detected.add("ML/AI")
        # Go frameworks
        if os.path.isfile(os.path.join(project, "go.mod")):
            try:
                with open(os.path.join(project, "go.mod"), encoding="utf-8") as f:
                    text = f.read().lower()
                if "gin" in text:
                    detected.add("Gin")
                if "echo" in text or "labstack/echo" in text:
                    detected.add("Echo")
                if "gorilla/mux" in text or "mux" in text:
                    detected.add("gorilla/mux")
            except Exception:
                pass
        return sorted(detected)

    def _extract_setup_py_deps(self):
        """Extract dependencies listed in setup.py install_requires."""
        deps = set()
        path = os.path.join(self._project_path, "setup.py")
        if not os.path.isfile(path):
            return deps
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            m = re.search(r'install_requires\s*=\s*\[([^\]]*)\]', text, re.DOTALL)
            if m:
                for line in m.group(1).split(","):
                    line = line.strip().strip("'\"").strip()
                    if line and not line.startswith("#"):
                        pkg = re.split(r'[>=<!\[]', line)[0].strip()
                        if pkg:
                            deps.add(pkg)
        except Exception:
            pass
        return deps

    def _extract_pyproject_deps(self):
        """Extract dependencies from pyproject.toml."""
        deps = set()
        path = os.path.join(self._project_path, "pyproject.toml")
        if not os.path.isfile(path):
            return deps
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("[") or line.startswith("#") or line.startswith("requires-python"):
                        continue
                    if "=" in line and not line.startswith("name") and not line.startswith("version"):
                        parts = line.split("=", 1)
                        key = parts[0].strip().strip("\"'")
                        if key and " " not in key and not key.startswith("_"):
                            val = parts[1].strip().strip("\"'")
                            if val and not val.startswith("{") and not val.startswith("["):
                                deps.add(key)
        except Exception:
            pass
        return deps

    def _classify_project(self, doc_info, frameworks, languages, ptype):
        """Classify project domain from multiple evidence sources.

        Returns dict with domain label, confidence, and evidence list.
        """
        evidence = []
        summary = doc_info.get("summary", "").lower() if doc_info else ""
        name = os.path.basename(self._project_path).lower()

        # Evidence from README / summary
        if summary:
            if any(kw in summary for kw in ("mobile", "android", "ios", "flutter")):
                evidence.append(("readme", "mobile_keywords"))
            if any(kw in summary for kw in ("web", "website", "frontend", "react", "vue")):
                evidence.append(("readme", "web_keywords"))
            if any(kw in summary for kw in ("api", "rest", "backend", "service", "microservice")):
                evidence.append(("readme", "backend_keywords"))
            if any(kw in summary for kw in ("ml", "machine learning", "ai", "tensorflow", "neural")):
                evidence.append(("readme", "ai_keywords"))
            if any(kw in summary for kw in ("enterprise", "platform", "multi-tenant", "saas")):
                evidence.append(("readme", "enterprise_keywords"))

        # Evidence from architecture doc content
        for doc_file in (doc_info.get("files") or []):
            if doc_file.get("role") == "architecture":
                text = doc_file.get("preview", "").lower()
                if any(kw in text for kw in ("mobile", "android", "ios")):
                    evidence.append(("architecture_doc", "mobile"))
                if any(kw in text for kw in ("web", "browser", "frontend")):
                    evidence.append(("architecture_doc", "web"))
                if any(kw in text for kw in ("api", "service", "backend", "microservice")):
                    evidence.append(("architecture_doc", "backend"))

        # Evidence from frameworks
        fw_set = {f.lower() for f in frameworks}
        if fw_set & {"flutter", "react native", "kotlin multi-platform", "swiftui"}:
            evidence.append(("framework", "mobile"))
        if fw_set & {"react", "vue", "angular", "next.js", "svelte"}:
            evidence.append(("framework", "web"))
        if fw_set & {"express", "django", "flask", "fastapi", "spring", "gin"}:
            evidence.append(("framework", "backend"))
        if fw_set & {"tensorflow", "pytorch", "keras", "ml/ai"}:
            evidence.append(("framework", "ai"))
        if fw_set & {"firebase", "supabase"}:
            evidence.append(("framework", "enterprise_platform"))

        # Evidence from project type
        if "flutter" in ptype.lower():
            evidence.append(("project_type", "mobile"))

        # Score each domain
        scores = {
            "mobile_application": 0,
            "web_application": 0,
            "backend_service": 0,
            "ai_system": 0,
            "enterprise_platform": 0,
        }
        domain_map = {
            "mobile_keywords": "mobile_application", "mobile": "mobile_application",
            "web_keywords": "web_application", "web": "web_application",
            "backend_keywords": "backend_service", "backend": "backend_service",
            "ai_keywords": "ai_system", "ai": "ai_system",
            "enterprise_keywords": "enterprise_platform", "enterprise_platform": "enterprise_platform",
        }
        for src, keyword in evidence:
            domain = domain_map.get(keyword)
            if domain:
                scores[domain] += 1

        # Determine best domain
        sorted_domains = sorted(scores.items(), key=lambda x: -x[1])
        top_domain = sorted_domains[0][0]
        top_score = sorted_domains[0][1]
        runner_up = sorted_domains[1][1] if len(sorted_domains) > 1 else 0

        if top_score == 0:
            confidence = "low"
            domain_label = "general_application"
        elif top_score >= 3:
            confidence = "high"
            domain_label = top_domain
        elif top_score >= 2 and top_score > runner_up:
            confidence = "medium"
            domain_label = top_domain
        else:
            confidence = "low"
            domain_label = top_domain if top_score > 0 else "general_application"

        return {
            "domain": domain_label,
            "confidence": confidence,
            "evidence": [{"source": s, "signal": k} for s, k in evidence],
            "scores": scores,
        }

    def _rank_frameworks(self, all_frameworks):
        """Rank frameworks into primary, secondary, and infrastructure tiers."""
        infrastructure_keywords = {
            "docker", "docker compose", "github actions", "gitlab ci", "circleci",
            "make", "jenkins", "travis ci", "teamcity", "ansible", "terraform",
            "kubernetes", "helm", "nginx",
        }
        primary_keywords = {
            "flutter", "react", "react native", "vue", "angular", "svelte",
            "django", "flask", "fastapi", "express", "spring", "gin",
            "tensorflow", "pytorch", "keras",
            "next.js", "nuxt", "gatsby",
            "asp.net", "rails", "laravel", "symfony",
        }
        secondary_keywords = {
            "firebase", "provider", "redux", "vuex", "ngrx",
            "sqlalchemy", "celery", "redis", "rabbitmq",
            "graphql", "apollo", "restify",
            "mongoose", "prisma", "typeorm",
            "pytest", "jest", "mocha", "junit",
            "bootstrap", "tailwindcss", "material ui",
            "firestore", "cloud_firestore", "cloud functions",
        }

        primary = []
        secondary = []
        infrastructure = []

        for fw in all_frameworks:
            fw_lower = fw.lower()
            if fw_lower in infrastructure_keywords:
                infrastructure.append(fw)
            elif fw_lower in primary_keywords:
                primary.append(fw)
            elif fw_lower in secondary_keywords:
                secondary.append(fw)
            else:
                secondary.append(fw)  # unclassified frameworks go to secondary

        return {
            "primary": sorted(primary),
            "secondary": sorted(secondary),
            "infrastructure": sorted(infrastructure),
        }

    def _categorize_documentation(self, doc_info):
        """Categorize documentation files into Architecture, Product, Build tiers."""
        arch_docs = []
        product_docs = []
        build_docs = []
        other_docs = []

        for doc in doc_info.get("files") or []:
            role = doc.get("role", "")
            fpath = doc.get("path", "").lower()
            heading = doc.get("heading", "").lower()

            if role == "architecture":
                arch_docs.append(doc)
            elif role in ("readme",):
                product_docs.append(doc)
            elif role == "changelog":
                build_docs.append(doc)
            elif role == "contributing":
                build_docs.append(doc)
            elif any(kw in fpath for kw in ("roadmap", "requirements", "goal", "vision", "features")):
                product_docs.append(doc)
            elif any(kw in fpath for kw in ("cmake", "makefile", "build", "compile", "ci")):
                build_docs.append(doc)
            elif any(kw in fpath for kw in ("database", "db", "schema", "data_model")):
                arch_docs.append(doc)
            elif any(kw in fpath for kw in ("system", "design", "spec", "specification")):
                arch_docs.append(doc)
            else:
                other_docs.append(doc)

        return {
            "architecture": arch_docs,
            "product": product_docs,
            "build": build_docs,
            "other": other_docs,
        }

    def _analyze_project_purpose(self, doc_info):
        """Infer project purpose with priority:
        1. Architecture documents
        2. README summary
        3. Project name
        4. Documentation headings
        Ignores generated, asset, and template files.
        """
        clues = []
        all_doc_files = doc_info.get("files") or []

        # Helper: ignore generated/asset/template paths
        def _is_generated(path):
            p = path.lower()
            return any(kw in p for kw in (
                "node_modules/", ".dart_tool/", "build/", "dist/",
                ".git/", ".github/", "coverage/", "__pycache__/",
                "generated", "template", "asset", "assets/",
            ))

        # Priority 1: Architecture documents
        for doc in all_doc_files:
            if _is_generated(doc.get("path", "")):
                continue
            if doc.get("role") == "architecture":
                preview = doc.get("preview", "").strip()
                if preview and len(preview) > 10:
                    clues.append(("architecture", preview))

        # Priority 2: README summary
        summary = doc_info.get("summary", "").strip()
        if summary and not _is_generated("readme.md"):
            clues.append(("readme", summary))

        # Priority 3: Project name
        name = os.path.basename(self._project_path).lower()
        if not _is_generated(name):
            if "api" in name or "service" in name or "backend" in name:
                clues.append(("project_name", "backend_service"))
            if "mobile" in name or "app" in name:
                clues.append(("project_name", "mobile_application"))
            if "web" in name or "frontend" in name or "ui" in name:
                clues.append(("project_name", "web_application"))
            if "cli" in name or "tool" in name:
                clues.append(("project_name", "cli_tool"))
            if "lib" in name or "sdk" in name or "package" in name:
                clues.append(("project_name", "library_package"))

        # Priority 4: Documentation headings (non-readme, non-arch)
        for doc in all_doc_files:
            if _is_generated(doc.get("path", "")):
                continue
            if doc.get("role") in ("readme", "architecture"):
                continue
            heading = doc.get("heading", "").strip()
            if heading and len(heading) > 10:
                clues.append(("heading", heading))

        # Build human-readable purpose summary
        purpose_parts = []
        seen = set()
        for source, text in clues:
            if text not in seen:
                seen.add(text)
                if source == "architecture":
                    purpose_parts.append("Architecture: " + text[:120])
                elif source == "readme":
                    purpose_parts.append(text[:120])
                elif source == "project_name":
                    purpose_parts.append("Project category: " + text.replace("_", " "))
                elif source == "heading":
                    purpose_parts.append("See: " + text[:80])

        return {
            "clues": clues,
            "summary": purpose_parts[0] if purpose_parts else "Unknown",
            "details": purpose_parts,
        }

    def _generate_architect_summary(self, doc_info, frameworks, languages, classification, ptype, framework_tiers=None):
        """Produce a clean architect-level project briefing.

        Prefers README + ARCHITECTURE.md, strips noisy fragments,
        and produces concise paragraph for the Architect Summary card.
        """
        parts = []
        summary = doc_info.get("summary", "").strip() if doc_info else ""
        domain = classification.get("domain", "").replace("_", " ")
        fw_tiers = framework_tiers or {}
        primary_fws = fw_tiers.get("primary", [])

        # Sentence 1: type + domain + primary language
        lang_str = ", ".join(languages[:3]) if languages else "Unknown"
        type_str = ptype.replace(" Application", "").replace(" Framework", "")
        domain_label = domain.replace("_", " ").title() if domain else type_str
        s1 = f"This is a {type_str.lower()} project"
        if domain and domain != "general_application":
            s1 += f" in the {domain_label} domain"
        s1 += f", built with {lang_str}."
        parts.append(s1)

        # Sentence 2: primary frameworks
        if primary_fws:
            fw_list = ", ".join(primary_fws)
            parts.append(f"Primary technology: {fw_list}.")

        # Sentence 3: supporting frameworks
        secondary_fws = fw_tiers.get("secondary", [])
        if secondary_fws:
            supporting = [f for f in secondary_fws if f.lower() not in ("flutter",)]
            if supporting:
                parts.append(f"Supporting libraries: {', '.join(supporting)}.")

        # Sentence 4: infrastructure
        infra = fw_tiers.get("infrastructure", [])
        if infra:
            parts.append(f"Infrastructure: {', '.join(infra)}.")

        # Sentence 5: purpose from readme (clean, brief)
        if summary:
            clean = summary[:200].rstrip("., ")
            if not clean.endswith("."):
                clean += "."
            parts.append(clean)

        return " ".join(parts)

    def observe(self) -> list:
        observations = []
        if not self._project_path or not os.path.isdir(self._project_path):
            return observations

        project_name = os.path.basename(self._project_path)
        ptype, type_info = self._detect_project_type()
        languages = self._detect_languages(type_info)
        frameworks = self._detect_frameworks(type_info)
        additional_frameworks = self._detect_additional_frameworks()
        all_frameworks = sorted(set(frameworks) | set(additional_frameworks))
        has_git = self._detect_git()
        dependencies = self._extract_dependencies(type_info)
        setup_py_deps = self._extract_setup_py_deps()
        pyproject_deps = self._extract_pyproject_deps()
        all_deps = sorted(set(dependencies) | setup_py_deps | pyproject_deps)
        file_count = self._count_files()
        doc_info = self._discover_documentation()
        yaml_info = self._detect_yaml_configs()
        purpose_clues = self._analyze_project_purpose(doc_info)
        classification = self._classify_project(doc_info, all_frameworks, languages, ptype)
        ranked_frameworks = self._rank_frameworks(all_frameworks)
        doc_categories = self._categorize_documentation(doc_info)
        architect_summary = self._generate_architect_summary(
            doc_info, all_frameworks, languages, classification, ptype, ranked_frameworks,
        )

        self._discovery_result = {
            "project": {
                "name": project_name,
                "path": self._project_path,
                "type": ptype,
                "languages": languages,
                "frameworks": all_frameworks,
                "classification": classification,
                "framework_tiers": ranked_frameworks,
            },
            "twin_version": 0,
            "timestamp": "",
            "fingerprint": "",
            "previous_fingerprint": "",
            "repository": {
                "type": "git" if has_git else "none",
                "detected": has_git,
            },
            "dependencies": all_deps,
            "statistics": {"file_count": file_count},
            "documentation": doc_info,
            "documentation_categories": doc_categories,
            "config_files": yaml_info,
            "purpose_clues": purpose_clues,
            "architect_summary": architect_summary,
        }
        self._discovery_result["fingerprint"] = self._compute_fingerprint(self._discovery_result)

        raw = RawPayload.from_dict(self._discovery_result)
        source = Source.create(type_="local_project", path=self._project_path)
        observation = Observation.create(
            type_="project_discovery",
            source=source,
            raw=raw,
            metadata={"connector": self.id, "project_name": project_name},
        )
        observations.append(observation)

        return observations

    def collect(self) -> list:
        evidence_list = []
        observations = self.observe()
        for obs in observations:
            normalized = self.normalize(obs.raw)
            artifact = Artifact.create(
                type_="project_twin",
                content=json.dumps(self._discovery_result) if self._discovery_result else "",
                path=self._project_path,
                mime_type="application/json",
            )
            trace = TraceInformation(
                connector_id=self.id,
                connector_version=self.version,
                pipeline=["observe", "collect", "normalize", "emit"],
                duration_ms=0.0,
            )
            evidence = Evidence.create(
                observation=obs,
                normalized=normalized,
                trace=trace,
                artifacts=[artifact],
            )
            evidence_list.append(evidence)
        return evidence_list

    def normalize(self, raw):
        return NormalizedPayload.structured(
            self._discovery_result or {"status": "no_data"}
        )

    def _compute_fingerprint(self, discovery_result):
        """Deterministic SHA-256 fingerprint of the project snapshot.

        Incorporates file paths (relative, sorted), dependencies, frameworks,
        languages, and config types — anything that would meaningfully change
        between project snapshots.
        """
        if not discovery_result:
            return ""
        raw = []
        # File names from documentation + config (best available file list)
        doc_files = discovery_result.get("documentation", {}).get("files", [])
        for d in doc_files:
            raw.append("DOC:" + d.get("path", ""))
        config_files = discovery_result.get("config_files", {}).get("files", [])
        for c in config_files:
            raw.append("CFG:" + c.get("path", ""))
        # Dependencies
        for dep in discovery_result.get("dependencies", []):
            raw.append("DEP:" + dep)
        # Frameworks
        for fw in discovery_result.get("project", {}).get("frameworks", []):
            raw.append("FW:" + fw)
        # Languages
        for lang in discovery_result.get("project", {}).get("languages", []):
            raw.append("LANG:" + lang)
        # Project type
        raw.append("TYPE:" + discovery_result.get("project", {}).get("type", ""))
        # Purpose summary
        purpose = discovery_result.get("purpose_clues", {}).get("summary", "")
        if purpose:
            raw.append("PURPOSE:" + purpose[:200])
        # Architect summary (condensed)
        arch = discovery_result.get("architect_summary", "")
        if arch:
            raw.append("ARCH:" + arch[:200])
        combined = "\n".join(sorted(raw))
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]

    def get_discovery_result(self):
        return self._discovery_result

    def discover_observation_surfaces(self) -> list:
        return [
            ObservationSurface.LOCAL_WORKSPACE,
            ObservationSurface.PROJECT_FILES,
            ObservationSurface.CONFIG_FILES,
        ]

    def rank_observation_surfaces(self) -> list:
        engine = ObservationDiscoveryEngine()
        surfaces = self.discover_observation_surfaces()
        qualities = {
            ObservationSurface.LOCAL_WORKSPACE: SurfaceQuality(
                surface=ObservationSurface.LOCAL_WORKSPACE,
                quality=EvidenceQuality.HIGH,
                latency=LatencyClass.REALTIME,
                completeness=Completeness.FULL,
                reliability=Reliability.HIGH,
                supports_incremental_sync=True,
                authentication_required="none",
                description="Direct local project folder access",
            ),
            ObservationSurface.PROJECT_FILES: SurfaceQuality(
                surface=ObservationSurface.PROJECT_FILES,
                quality=EvidenceQuality.HIGH,
                latency=LatencyClass.BATCH,
                completeness=Completeness.FULL,
                reliability=Reliability.HIGH,
                supports_incremental_sync=False,
                authentication_required="none",
                description="File metadata and content scanning",
            ),
            ObservationSurface.CONFIG_FILES: SurfaceQuality(
                surface=ObservationSurface.CONFIG_FILES,
                quality=EvidenceQuality.HIGH,
                latency=LatencyClass.BATCH,
                completeness=Completeness.PARTIAL,
                reliability=Reliability.HIGH,
                supports_incremental_sync=False,
                authentication_required="none",
                description="Project configuration files analysis",
            ),
        }
        return engine.rank_surfaces(surfaces, qualities)

    def select_observation_pipeline(self) -> list:
        engine = ObservationDiscoveryEngine()
        ranked = self.rank_observation_surfaces()
        return engine.select_pipeline(ranked)
