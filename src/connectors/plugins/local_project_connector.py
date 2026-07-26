"""LocalProjectConnector — discovers project identity, structure, and stack from
a local project folder. Creates a Project Twin representation.

Complies with Universal Observation Policy and Universal Connector Framework.
"""

import os
import re
import json

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
        return sorted(frameworks)

    def _detect_git(self):
        git_dir = os.path.join(self._project_path, ".git")
        return os.path.isdir(git_dir)

    def _extract_dependencies(self, type_info):
        deps = set()
        for dep_file in type_info.get("dep_files", []):
            path = os.path.join(self._project_path, dep_file)
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
        return sorted(deps)

    def _count_files(self):
        count = 0
        for root, dirs, files in os.walk(self._project_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules" and d != "build" and d != ".dart_tool"]
            count += len(files)
        return count

    def observe(self) -> list:
        observations = []
        if not self._project_path or not os.path.isdir(self._project_path):
            return observations

        project_name = os.path.basename(self._project_path)
        ptype, type_info = self._detect_project_type()
        languages = self._detect_languages(type_info)
        frameworks = self._detect_frameworks(type_info)
        has_git = self._detect_git()
        dependencies = self._extract_dependencies(type_info)
        file_count = self._count_files()

        self._discovery_result = {
            "project": {
                "name": project_name,
                "path": self._project_path,
                "type": ptype,
                "languages": languages,
                "frameworks": frameworks,
            },
            "repository": {
                "type": "git" if has_git else "none",
                "detected": has_git,
            },
            "dependencies": dependencies,
            "statistics": {"file_count": file_count},
        }

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
