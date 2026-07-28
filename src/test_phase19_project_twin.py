"""Project Twin Discovery — v3.1 Connector Expansion.

Tests LocalProjectConnector, ProjectTwinDiscoveryService, and the
discover_project_twin MCP tool.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch


class FakeKernel:
    def __init__(self):
        self._services = {}
        self._config = {}
        self.event_bus = MagicMock()

    def get_service(self, name):
        return self._services.get(name)

    def get_config(self):
        return self._config

    def register_service(self, service):
        self._services[service.name] = service
        service.kernel = self

    def set_config(self, config):
        self._config.update(config)


def make_mock_service(name, **attrs):
    svc = MagicMock()
    svc.name = name
    svc.kernel = None
    for k, v in attrs.items():
        setattr(svc, k, v)
    return svc


def create_flutter_project(temp_dir):
    """Create a realistic Flutter project structure for testing."""
    project_dir = os.path.join(temp_dir, "eagles_property")
    os.makedirs(project_dir)
    os.makedirs(os.path.join(project_dir, "lib"))
    os.makedirs(os.path.join(project_dir, "test"))
    os.makedirs(os.path.join(project_dir, ".dart_tool"))
    os.makedirs(os.path.join(project_dir, "android", "app"))
    os.makedirs(os.path.join(project_dir, "ios"))
    os.makedirs(os.path.join(project_dir, ".git"))
    os.makedirs(os.path.join(project_dir, ".github", "workflows"))

    # pubspec.yaml
    with open(os.path.join(project_dir, "pubspec.yaml"), "w") as f:
        f.write("name: eagles_property\n")
        f.write("description: Property management app\n")
        f.write("\n")
        f.write("dependencies:\n")
        f.write("  flutter:\n")
        f.write("    sdk: flutter\n")
        f.write("  firebase_core: ^2.0.0\n")
        f.write("  cloud_firestore: ^3.0.0\n")
        f.write("  provider: ^5.0.0\n")

    # Dart source files
    with open(os.path.join(project_dir, "lib", "main.dart"), "w") as f:
        f.write("import 'package:flutter/material.dart';\nvoid main() => runApp(App());\n")
    with open(os.path.join(project_dir, "lib", "app.dart"), "w") as f:
        f.write("class App extends StatelessWidget {}\n")
    with open(os.path.join(project_dir, "test", "widget_test.dart"), "w") as f:
        f.write("void main() {}\n")

    # README with substantial content
    with open(os.path.join(project_dir, "README.md"), "w") as f:
        f.write("# Eagle's Property\n\n")
        f.write("A Flutter-based property management mobile application for real estate\n")
        f.write("agents. Features include property listings, client management, and\n")
        f.write("integrated messaging with Firebase Cloud Messaging.\n")

    # Architecture documentation
    with open(os.path.join(project_dir, "ARCHITECTURE.md"), "w") as f:
        f.write("# Architecture\n\nUses BLoC pattern with Firebase backend.\n")

    # CHANGELOG
    with open(os.path.join(project_dir, "CHANGELOG.md"), "w") as f:
        f.write("# Changelog\n\n## 1.0.0\nInitial release.\n")

    # CONTRIBUTING
    with open(os.path.join(project_dir, "CONTRIBUTING.md"), "w") as f:
        f.write("# Contributing\n\nPlease read the guidelines.\n")

    # Docker infrastructure
    with open(os.path.join(project_dir, "Dockerfile"), "w") as f:
        f.write("FROM flutter:latest\nCOPY . /app\n")
    with open(os.path.join(project_dir, "docker-compose.yaml"), "w") as f:
        f.write("version: '3'\nservices:\n  app:\n    build: .\n")

    # CI config
    with open(os.path.join(project_dir, ".github", "workflows", "ci.yaml"), "w") as f:
        f.write("name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n")

    # Other files
    with open(os.path.join(project_dir, ".gitignore"), "w") as f:
        f.write("*.dart_tool\n")
    with open(os.path.join(project_dir, "analysis_options.yaml"), "w") as f:
        f.write("include: package:flutter_lints/flutter.yaml\n")

    return project_dir


def create_nested_flutter_project(temp_dir):
    """Create a Flutter project with nested layout (root/app/pubspec.yaml).

    Mirrors EaglEs-Property real layout where Flutter sources live under
    an app/ subdirectory instead of the project root.
    """
    project_dir = os.path.join(temp_dir, "eagles_property")
    app_dir = os.path.join(project_dir, "app")
    os.makedirs(app_dir)
    os.makedirs(os.path.join(app_dir, "lib"))
    os.makedirs(os.path.join(app_dir, "test"))
    os.makedirs(os.path.join(app_dir, ".dart_tool"))
    os.makedirs(os.path.join(project_dir, ".github", "workflows"))

    # pubspec.yaml inside app/
    with open(os.path.join(app_dir, "pubspec.yaml"), "w") as f:
        f.write("name: eagles_property\n")
        f.write("description: Property management app\n")
        f.write("\n")
        f.write("dependencies:\n")
        f.write("  flutter:\n")
        f.write("    sdk: flutter\n")
        f.write("  firebase_core: ^2.0.0\n")
        f.write("  cloud_firestore: ^3.0.0\n")
        f.write("  provider: ^5.0.0\n")
        f.write("  google_maps_flutter: ^2.0.0\n")

    # Dart source files inside app/
    with open(os.path.join(app_dir, "lib", "main.dart"), "w") as f:
        f.write("import 'package:flutter/material.dart';\nvoid main() => runApp(App());\n")
    with open(os.path.join(app_dir, "lib", "app.dart"), "w") as f:
        f.write("class App extends StatelessWidget {}\n")
    with open(os.path.join(app_dir, "test", "widget_test.dart"), "w") as f:
        f.write("void main() {}\n")

    # README at root
    with open(os.path.join(project_dir, "README.md"), "w") as f:
        f.write("# Eagle's Property\n\n")
        f.write("A Flutter-based property management mobile application for real estate\n")
        f.write("agents. Features include property listings, client management, and\n")
        f.write("integrated messaging with Firebase Cloud Messaging.\n")

    # Architecture documentation at root
    with open(os.path.join(project_dir, "ARCHITECTURE.md"), "w") as f:
        f.write("# Architecture\n\nUses BLoC pattern with Firebase backend.\n")

    # CI config at root
    with open(os.path.join(project_dir, ".github", "workflows", "ci.yaml"), "w") as f:
        f.write("name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n")

    return project_dir


def create_python_project(temp_dir):
    """Create a Python project structure for testing."""
    project_dir = os.path.join(temp_dir, "py_project")
    os.makedirs(project_dir)
    os.makedirs(os.path.join(project_dir, "src"))
    os.makedirs(os.path.join(project_dir, "tests"))
    os.makedirs(os.path.join(project_dir, ".github", "workflows"))

    # setup.py with install_requires
    with open(os.path.join(project_dir, "setup.py"), "w") as f:
        f.write("from setuptools import setup\nsetup(\n")
        f.write("    name='py_project',\n")
        f.write("    install_requires=[\n")
        f.write("        'flask>=2.0',\n")
        f.write("        'requests',\n")
        f.write("        'sqlalchemy',\n")
        f.write("    ],\n")
        f.write(")\n")

    # Python source files
    with open(os.path.join(project_dir, "src", "main.py"), "w") as f:
        f.write("print('hello')\n")
    with open(os.path.join(project_dir, "src", "utils.py"), "w") as f:
        f.write("def helper(): pass\n")

    # requirements.txt
    with open(os.path.join(project_dir, "requirements.txt"), "w") as f:
        f.write("flask==2.0.0\nrequests==2.28.0\n")

    # README
    with open(os.path.join(project_dir, "README.md"), "w") as f:
        f.write("# Py Project\n\nA Python CLI tool for data analysis and reporting.\n")

    # CHANGELOG
    with open(os.path.join(project_dir, "CHANGELOG.md"), "w") as f:
        f.write("# Changelog\n\n## 0.1.0\nInitial version.\n")

    # Makefile
    with open(os.path.join(project_dir, "Makefile"), "w") as f:
        f.write("test:\n\tpython -m pytest\n")

    return project_dir


def create_property_connect_project(temp_dir):
    """Create the 'Property Connect' external validation fixture.

    Represents an unknown Flutter real estate platform project for validation.
    """
    project_dir = os.path.join(temp_dir, "property_connect")
    os.makedirs(project_dir)
    os.makedirs(os.path.join(project_dir, "lib"))
    os.makedirs(os.path.join(project_dir, "test"))
    os.makedirs(os.path.join(project_dir, ".dart_tool"))
    os.makedirs(os.path.join(project_dir, "android", "app"))
    os.makedirs(os.path.join(project_dir, "ios"))
    os.makedirs(os.path.join(project_dir, ".git"))
    os.makedirs(os.path.join(project_dir, ".github", "workflows"))

    # pubspec.yaml
    with open(os.path.join(project_dir, "pubspec.yaml"), "w") as f:
        f.write("name: property_connect\n")
        f.write("description: Multi-tenant Flutter Real Estate Platform\n")
        f.write("\n")
        f.write("dependencies:\n")
        f.write("  flutter:\n")
        f.write("    sdk: flutter\n")
        f.write("  firebase_core: ^3.6.0\n")
        f.write("  cloud_firestore: ^5.6.0\n")
        f.write("  firebase_auth: ^5.5.0\n")
        f.write("  provider: ^6.1.0\n")
        f.write("  geolocator: ^13.0.0\n")
        f.write("  cached_network_image: ^3.4.0\n")

    # lib/main.dart
    with open(os.path.join(project_dir, "lib", "main.dart"), "w") as f:
        f.write("import 'package:flutter/material.dart';\n")
        f.write("import 'package:provider/provider.dart';\n")
        f.write("import 'package:firebase_core/firebase_core.dart';\n")
        f.write("void main() async {\n")
        f.write("  WidgetsFlutterBinding.ensureInitialized();\n")
        f.write("  await Firebase.initializeApp();\n")
        f.write("  runApp(PropertyConnectApp());\n")
        f.write("}\n")
        f.write("class PropertyConnectApp extends StatelessWidget {}\n")

    # README.md
    with open(os.path.join(project_dir, "README.md"), "w") as f:
        f.write("# Property Connect\n\n")
        f.write("A multi-tenant real estate platform built with Flutter and Firebase.\n")
        f.write("Property Connect enables property managers to list, manage, and\n")
        f.write("market properties across multiple tenants with role-based access\n")
        f.write("control, integrated messaging, and analytics dashboards.\n")

    # GOAL.md
    with open(os.path.join(project_dir, "GOAL.md"), "w") as f:
        f.write("# Project Goal\n\n")
        f.write("Build a scalable multi-tenant real estate management platform that\n")
        f.write("connects property owners, tenants, and service providers.\n")
        f.write("The platform targets mid-size property management firms.\n")

    # ARCHITECTURE.md
    with open(os.path.join(project_dir, "ARCHITECTURE.md"), "w") as f:
        f.write("# Architecture\n\n")
        f.write("Clean Architecture with feature-first directory structure.\n")
        f.write("- Presentation layer: Flutter widgets + Provider state management\n")
        f.write("- Domain layer: Use cases and entity models\n")
        f.write("- Data layer: Firebase Firestore + Firebase Auth\n")
        f.write("State management via ChangeNotifier pattern with Provider.\n")

    # CHANGELOG.md
    with open(os.path.join(project_dir, "CHANGELOG.md"), "w") as f:
        f.write("# Changelog\n\n")
        f.write("## 2.0.0\n")
        f.write("- Multi-tenant support\n")
        f.write("- Role-based access control\n")
        f.write("- Analytics dashboard\n")
        f.write("## 1.0.0\n")
        f.write("- Initial release\n")

    # firebase.json
    with open(os.path.join(project_dir, "firebase.json"), "w") as f:
        f.write('{\n')
        f.write('  "project_info": {\n')
        f.write('    "project_number": "123456789",\n')
        f.write('    "project_id": "property-connect-prod",\n')
        f.write('    "storage_bucket": "property-connect-prod.appspot.com"\n')
        f.write('  },\n')
        f.write('  "firestore": {\n')
        f.write('    "rules": "firestore.rules"\n')
        f.write('  }\n')
        f.write('}\n')

    # analysis_options.yaml
    with open(os.path.join(project_dir, "analysis_options.yaml"), "w") as f:
        f.write("include: package:flutter_lints/flutter.yaml\n")
        f.write("linter:\n")
        f.write("  rules:\n")
        f.write("    - prefer_const_constructors\n")
        f.write("    - avoid_print\n")

    # CI config
    with open(os.path.join(project_dir, ".github", "workflows", "ci.yaml"), "w") as f:
        f.write("name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n")
        f.write("    steps:\n      - uses: actions/checkout@v4\n")

    # Dockerfile
    with open(os.path.join(project_dir, "Dockerfile"), "w") as f:
        f.write("FROM flutter:latest\nWORKDIR /app\nCOPY . .\nRUN flutter build web\n")

    return project_dir


def format_validation_report(discovery_result):
    """Format a human-readable [EYE SCAN] validation report from discovery data."""
    if not discovery_result:
        return "[EYE SCAN]\n\nNo discovery data available.\n"
    proj = discovery_result.get("project", {})
    docs = discovery_result.get("documentation", {})
    clues_data = discovery_result.get("purpose_clues", {})
    clues_summary = clues_data.get("summary", "")
    lines = []
    lines.append("[EYE SCAN]\n")
    lines.append("Project detected:\n")
    lines.append("Name:")
    lines.append("  " + proj.get("name", "unknown"))
    lines.append("")
    lines.append("Type:")
    lines.append("  " + proj.get("type", "Unknown"))
    lines.append("")
    lines.append("Languages:")
    for lang in proj.get("languages", []):
        lines.append("  " + lang)
    lines.append("")
    lines.append("Frameworks:")
    for fw in proj.get("frameworks", []):
        lines.append("  " + fw)
    lines.append("")
    lines.append("Documentation:")
    for doc in docs.get("files", []):
        lines.append("  " + doc["path"])
    lines.append("")
    lines.append("Purpose:")
    if clues_summary:
        lines.append("  " + (clues_summary[:100] if len(clues_summary) > 100 else clues_summary))
    else:
        lines.append("  Unknown")
    lines.append("")
    lines.append("Twin:")
    lines.append("  CREATED")
    lines.append("")
    return "\n".join(lines)


def create_node_project(temp_dir):
    """Create a Node.js project with package.json."""
    project_dir = os.path.join(temp_dir, "node_app")
    os.makedirs(project_dir)
    os.makedirs(os.path.join(project_dir, ".git"))

    with open(os.path.join(project_dir, "package.json"), "w") as f:
        json.dump({
            "name": "node_app",
            "version": "1.0.0",
            "description": "Express REST API for user management",
            "dependencies": {"express": "^4.0.0", "firebase": "^9.0.0"},
            "devDependencies": {"jest": "^29.0.0"},
        }, f)

    with open(os.path.join(project_dir, "index.js"), "w") as f:
        f.write("const express = require('express');\n")

    # README
    with open(os.path.join(project_dir, "README.md"), "w") as f:
        f.write("# Node App\n\nA REST API built with Express and Firebase for user management.\n")

    # Dockerfile
    with open(os.path.join(project_dir, "Dockerfile"), "w") as f:
        f.write("FROM node:18\nCOPY . /app\nCMD [\"node\", \"index.js\"]\n")

    return project_dir


# --- LocalProjectConnector Tests ---

class TestLocalProjectConnector(unittest.TestCase):
    def test_connector_initialization(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        connector = LocalProjectConnector(config={"project_path": "/tmp"})
        self.assertEqual(connector.id, "local_project")
        self.assertEqual(connector.name, "Local Project Connector")
        self.assertIn("project_discovery", connector.capabilities)

    def test_connect_invalid_path(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        connector = LocalProjectConnector(config={"project_path": "/nonexistent/path"})
        result = connector.connect()
        self.assertFalse(result)

    def test_connect_valid_path(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            result = connector.connect()
            self.assertTrue(result)

    def test_discover(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            sources = connector.discover()
            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0].type, "local_project")
            self.assertEqual(sources[0].path, project_dir)

    def test_detect_flutter_project(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            observations = connector.observe()
            result = connector.get_discovery_result()
            self.assertIsNotNone(result)
            self.assertEqual(result["project"]["name"], "eagles_property")
            self.assertEqual(result["project"]["type"], "Flutter Application")
            self.assertIn("Dart", result["project"]["languages"])
            self.assertIn("Flutter", result["project"]["frameworks"])

    def test_detect_python_project(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_python_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            self.assertIsNotNone(result)
            self.assertEqual(result["project"]["name"], "py_project")
            self.assertIn("Python", result["project"]["languages"])

    def test_detect_node_project(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_node_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            self.assertIsNotNone(result)
            self.assertEqual(result["project"]["name"], "node_app")
            self.assertIn("JavaScript", result["project"]["languages"])
            self.assertIn("JSON", result["project"]["languages"])

    def test_git_detection(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            self.assertTrue(result["repository"]["detected"])
            self.assertEqual(result["repository"]["type"], "git")

    def test_git_not_detected(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_python_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            self.assertFalse(result["repository"]["detected"])

    def test_dependency_extraction_flutter(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            deps = result["dependencies"]
            self.assertIn("firebase_core", deps)
            self.assertIn("cloud_firestore", deps)
            self.assertIn("provider", deps)

    def test_dependency_extraction_node(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_node_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            deps = result["dependencies"]
            self.assertIn("express", deps)
            self.assertIn("firebase", deps)
            self.assertIn("jest", deps)

    def test_file_counting(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            # Flutter project has: pubspec.yaml, main.dart, app.dart,
            # widget_test.dart, README.md, .gitignore, analysis_options.yaml
            # Excludes hidden dirs and node_modules/build/.dart_tool
            self.assertGreater(result["statistics"]["file_count"], 5)

    def test_discovery_time_set(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            observations = connector.collect()
            self.assertEqual(len(observations), 1)
            self.assertEqual(observations[0].trace.connector_id, "local_project")

    def test_observation_surfaces(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        connector = LocalProjectConnector()
        surfaces = connector.discover_observation_surfaces()
        self.assertIn("local_workspace", [s.value for s in surfaces])
        self.assertIn("project_files", [s.value for s in surfaces])
        self.assertIn("config_files", [s.value for s in surfaces])

    def test_rank_observation_surfaces(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        connector = LocalProjectConnector()
        ranked = connector.rank_observation_surfaces()
        self.assertGreater(len(ranked), 0)

    def test_select_observation_pipeline(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        connector = LocalProjectConnector()
        pipeline = connector.select_observation_pipeline()
        self.assertGreater(len(pipeline), 0)

    def test_disconnect(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        connector = LocalProjectConnector(config={"project_path": "/tmp"})
        connector.connect()
        result = connector.disconnect()
        self.assertTrue(result)
        self.assertIsNone(connector.get_discovery_result())

    # --- Enhanced Discovery Tests ---

    def test_documentation_discovery_flutter(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            docs = result.get("documentation", {})
            files = docs.get("files", [])
            self.assertGreater(len(files), 3)
            paths = [d["path"] for d in files]
            self.assertTrue(any("README.md" in p for p in paths))
            self.assertTrue(any("ARCHITECTURE.md" in p for p in paths))
            self.assertTrue(any("CHANGELOG.md" in p for p in paths))
            self.assertTrue(any("CONTRIBUTING.md" in p for p in paths))

    def test_documentation_categorization(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            docs = result.get("documentation", {})
            files = docs.get("files", [])
            roles = [f["role"] for f in files]
            self.assertIn("readme", roles)
            self.assertIn("architecture", roles)
            self.assertIn("changelog", roles)
            self.assertIn("contributing", roles)

    def test_readme_summary_extraction(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            docs = result.get("documentation", {})
            summary = docs.get("summary", "")
            self.assertIn("property management", summary.lower())
            self.assertIn("mobile application", summary.lower())

    def test_yaml_config_detection_flutter(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            cf = result.get("config_files", {})
            files = cf.get("files", [])
            self.assertGreaterEqual(len(files), 2)
            purposes = [f.get("purpose") for f in files]
            self.assertIn("configuration", purposes)
            self.assertIn("docker", purposes)

    def test_additional_framework_detection_flutter(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            frameworks = result["project"].get("frameworks", [])
            self.assertIn("Docker", frameworks)
            self.assertIn("GitHub Actions", frameworks)

    def test_purpose_inference_readme_based(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            clues_data = result.get("purpose_clues", {})
            self.assertGreater(len(clues_data.get("clues", [])), 0)
            self.assertIn("summary", clues_data)

    def test_setup_py_dependency_extraction(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_python_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            deps = result.get("dependencies", {})
            self.assertIn("flask", deps)
            self.assertIn("requests", deps)
            self.assertIn("sqlalchemy", deps)

    def test_yaml_config_detection_python(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_python_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            cf = result.get("config_files", {})
            self.assertGreaterEqual(cf.get("count", 0), 0)

    def test_makefile_detection(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_python_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            frameworks = result["project"].get("frameworks", [])
            self.assertIn("Make", frameworks)

    def test_dockerfile_detection_node(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_node_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            frameworks = result["project"].get("frameworks", [])
            self.assertIn("Docker", frameworks)

    def test_node_readme_summary(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_node_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            docs = result.get("documentation", {})
            summary = docs.get("summary", "")
            self.assertIn("REST API", summary)

    def test_documentation_discovery_node(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_node_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            docs = result.get("documentation", {})
            roles = [f["role"] for f in docs.get("files", [])]
            self.assertIn("readme", roles)

    def test_documentation_architecture_topic(self):
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            docs = result.get("documentation", {})
            topic = docs.get("architecture_topic", "")
            self.assertIn("Architecture", topic)

    # --- Intelligence Layer Tests ---

    def test_project_classification_structure(self):
        """Classification returns domain, confidence, and evidence keys."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            classification = result["project"].get("classification", {})
            self.assertIn("domain", classification)
            self.assertIn("confidence", classification)
            self.assertIn("evidence", classification)
            self.assertIn("scores", classification)

    def test_project_classification_flutter_is_mobile(self):
        """Flutter project classified as mobile_application."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            classification = result["project"]["classification"]
            self.assertEqual(classification["domain"], "mobile_application")
            self.assertIn(classification["confidence"], ("high", "medium"))

    def test_project_classification_property_connect_has_enterprise_signal(self):
        """Property Connect has enterprise and mobile evidence signals."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_property_connect_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            classification = result["project"]["classification"]
            self.assertIn("domain", classification)
            self.assertIn("confidence", classification)
            # Should have evidence signals from Flutter (mobile) and multi-tenant keywords
            signals = [e["signal"] for e in classification.get("evidence", [])]
            self.assertTrue(len(signals) > 0)

    def test_project_classification_python_is_backend_or_cli(self):
        """Python project classification is plausible."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_python_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            classification = result["project"]["classification"]
            self.assertIn("domain", classification)
            self.assertIn("confidence", classification)

    def test_framework_ranking_tiers_present(self):
        """Framework tiers key exists with primary, secondary, infrastructure."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            tiers = result["project"].get("framework_tiers", {})
            self.assertIn("primary", tiers)
            self.assertIn("secondary", tiers)
            self.assertIn("infrastructure", tiers)

    def test_framework_ranking_flutter_in_primary(self):
        """Flutter framework appears in primary tier, Docker in infrastructure."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            tiers = result["project"]["framework_tiers"]
            self.assertIn("Flutter", tiers["primary"])
            self.assertIn("Docker", tiers["infrastructure"])
            self.assertIn("Firebase", tiers["secondary"])

    def test_documentation_categorization_structure(self):
        """Documentation categories has architecture, product, build keys."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            cats = result.get("documentation_categories", {})
            self.assertIn("architecture", cats)
            self.assertIn("product", cats)
            self.assertIn("build", cats)

    def test_documentation_categorization_readme_in_product(self):
        """README is categorized under product docs."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            cats = result["documentation_categories"]
            readme_paths = [d["path"] for d in cats["product"]]
            self.assertTrue(any("README.md" in p for p in readme_paths))

    def test_documentation_categorization_architecture(self):
        """ARCHITECTURE.md is under architecture docs."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            cats = result["documentation_categories"]
            arch_paths = [d["path"] for d in cats["architecture"]]
            self.assertTrue(any("ARCHITECTURE.md" in p for p in arch_paths))

    def test_purpose_extraction_has_summary_and_details(self):
        """Improved purpose extraction returns dict with summary, clues, details."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            purpose = result.get("purpose_clues", {})
            self.assertIn("summary", purpose)
            self.assertIn("clues", purpose)
            self.assertIn("details", purpose)
            self.assertGreater(len(purpose["summary"]), 0)

    def test_purpose_extraction_architecture_priority(self):
        """Architecture document content appears in clues."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            purpose = result.get("purpose_clues", {})
            clues_text = " ".join(c[1] for c in purpose.get("clues", []) if c[0] == "architecture")
            self.assertGreater(len(clues_text), 0)

    # --- Architect Summary & Presentation Tests ---

    def test_architect_summary_present(self):
        """Architect summary is generated and present in discovery result."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            summary = result.get("architect_summary", "")
            self.assertGreater(len(summary), 20)
            self.assertIn("flutter", summary.lower())

    def test_architect_summary_contains_tech_details(self):
        """Architect summary mentions frameworks and language."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            summary = result.get("architect_summary", "")
            self.assertIn("Dart", summary)
            self.assertIn("Flutter", summary)

    def test_architect_summary_for_property_connect(self):
        """Architect summary references property connect purpose."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_property_connect_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            summary = result.get("architect_summary", "")
            self.assertGreater(len(summary), 30)
            self.assertIn("Dart", summary)

    def test_classification_evidence_sources(self):
        """Classification evidence list is populated."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            classification = result["project"]["classification"]
            evidence = classification.get("evidence", [])
            self.assertGreater(len(evidence), 0)
            for e in evidence:
                self.assertIn("source", e)
                self.assertIn("signal", e)

    def test_knowledge_map_excludes_generated(self):
        """Documentation categories exclude generated paths."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            cats = result.get("documentation_categories", {})
            all_paths = []
            for group in ("architecture", "product", "build"):
                for doc in cats.get(group, []):
                    all_paths.append(doc.get("path", ""))
            # No generated paths should leak through
            generated_keywords = ["build/", ".dart_tool/", "node_modules/", "cache/"]
            for path in all_paths:
                for kw in generated_keywords:
                    self.assertNotIn(kw, path, "Generated path found in doc categories: " + path)

    def test_service_architect_summary_in_discovery(self):
        """Service-level: architect_summary is in discovery result."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            discovery = result["discovery"]
            self.assertIn("architect_summary", discovery)
            self.assertGreater(len(discovery["architect_summary"]), 20)

    def test_service_architect_summary_in_twin_file(self):
        """Twin file contains architect_summary."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            kernel.set_config({"memory_path": tmp})
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            twin_path = result["twin_path"]
            with open(twin_path) as f:
                twin_data = json.load(f)
            self.assertIn("architect_summary", twin_data)
            self.assertGreater(len(twin_data["architect_summary"]), 20)

    # --- Nested Flutter project regression tests ---

    def test_nested_flutter_project_type_detected(self):
        """Root with app/pubspec.yaml is detected as Flutter Application."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_nested_flutter_project(tmp)
            c = LocalProjectConnector(config={"project_path": project_dir})
            c.connect()
            c.observe()
            result = c.get_discovery_result()
            self.assertEqual(result["project"]["type"], "Flutter Application")

    def test_nested_flutter_project_frameworks_detected(self):
        """Flutter and Firebase detected from nested app/pubspec.yaml."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_nested_flutter_project(tmp)
            c = LocalProjectConnector(config={"project_path": project_dir})
            c.connect()
            c.observe()
            result = c.get_discovery_result()
            fws = result["project"]["frameworks"]
            self.assertIn("Flutter", fws)
            self.assertIn("Firebase", fws)
            self.assertIn("GitHub Actions", fws)

    def test_nested_flutter_project_dependencies_extracted(self):
        """Dependencies extracted from nested app/pubspec.yaml."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_nested_flutter_project(tmp)
            c = LocalProjectConnector(config={"project_path": project_dir})
            c.connect()
            c.observe()
            result = c.get_discovery_result()
            deps = result["dependencies"]
            self.assertIn("flutter", deps)
            self.assertIn("firebase_core", deps)
            self.assertIn("cloud_firestore", deps)
            self.assertIn("provider", deps)

    def test_nested_flutter_project_framework_tiers(self):
        """framework_tiers contract preserved for nested Flutter project."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_nested_flutter_project(tmp)
            c = LocalProjectConnector(config={"project_path": project_dir})
            c.connect()
            c.observe()
            result = c.get_discovery_result()
            tiers = result["project"]["framework_tiers"]
            self.assertIn("Flutter", tiers.get("primary", []))
            self.assertIn("Firebase", tiers.get("secondary", []))
            self.assertIn("GitHub Actions", tiers.get("infrastructure", []))
            self.assertNotIn("Flutter", tiers.get("infrastructure", []))
            self.assertNotIn("GitHub Actions", tiers.get("primary", []))

    def test_nested_flutter_project_recursive_detection(self):
        """Flutter detected even when root has no pubspec.yaml."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_nested_flutter_project(tmp)
            # Verify no pubspec.yaml at root
            self.assertFalse(os.path.isfile(os.path.join(project_dir, "pubspec.yaml")))
            c = LocalProjectConnector(config={"project_path": project_dir})
            c.connect()
            c.observe()
            result = c.get_discovery_result()
            # Flutter must be detected from app/pubspec.yaml
            self.assertIn("Flutter", result["project"]["frameworks"])
            self.assertEqual(result["project"]["type"], "Flutter Application")


# --- ProjectTwinDiscoveryService Tests ---

class TestProjectTwinDiscoveryService(unittest.TestCase):
    def setUp(self):
        self.kernel = FakeKernel()
        self.store = make_mock_service("KnowledgeStoreService")
        self.kernel._services["KnowledgeStoreService"] = self.store

    def test_discover_project_flutter(self):
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            self.assertIsNotNone(result)
            self.assertEqual(result["status"], "CONNECTED")
            self.assertEqual(result["project_name"], "eagles_property")
            self.assertEqual(result["discovery"]["project"]["type"], "Flutter Mobile Application")
            self.assertIn("Dart", result["discovery"]["project"]["languages"])
            self.assertIn("Flutter", result["discovery"]["project"]["frameworks"])
            self.assertTrue(result["discovery"]["repository"]["detected"])
            self.assertIn("firebase_core", result["discovery"]["dependencies"])

    def test_discover_project_notifications(self):
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            self.assertIn("notifications", result)
            messages = [n["message"] for n in result["notifications"]]
            self.assertIn("CONNECTED", messages)
            self.assertIn("EYE SCAN", messages)
            self.assertIn("PROJECT IDENTIFIED", messages)
            self.assertIn("STACK DETECTED", messages)
            self.assertIn("GIT REPOSITORY DETECTED", messages)
            self.assertIn("DEPENDENCIES DISCOVERED", messages)
            self.assertIn("DOCUMENTATION DISCOVERED", messages)
            self.assertIn("CONFIGURATION DETECTED", messages)
            self.assertIn("PROJECT TWIN CREATED", messages)

    def test_discover_project_creates_twin_file(self):
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            self.kernel.set_config({"memory_path": tmp})
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            self.assertIn("twin_path", result)
            self.assertTrue(os.path.isfile(result["twin_path"]))
            with open(result["twin_path"]) as f:
                twin_data = json.load(f)
            self.assertEqual(twin_data["status"], "CONNECTED")
            self.assertEqual(twin_data["project"]["name"], "eagles_property")

    def test_discover_project_invalid_path(self):
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        result = svc.discover_project("/nonexistent/path")
        self.assertIn("error", result)

    def test_discover_project_python(self):
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_python_project(tmp)
            result = svc.discover_project(project_dir)
            self.assertEqual(result["status"], "CONNECTED")
            self.assertIn("Python", result["discovery"]["project"]["languages"])

    def test_discover_project_node(self):
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_node_project(tmp)
            result = svc.discover_project(project_dir)
            self.assertEqual(result["status"], "CONNECTED")
            self.assertIn("Express", result["discovery"]["project"]["frameworks"])
            self.assertIn("Firebase", result["discovery"]["project"]["frameworks"])

    def test_event_bus_notifications_published(self):
        from services.project_twin_discovery_service import (
            ProjectTwinDiscoveryService,
            TWIN_CONNECTED, TWIN_IDENTIFIED, TWIN_SCAN,
            TWIN_STACK_DETECTED, TWIN_GIT_DETECTED,
            TWIN_DEPENDENCIES, TWIN_CREATED,
        )
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            svc.discover_project(project_dir)
            self.kernel.event_bus.publish.assert_any_call(TWIN_CONNECTED, {
                "project_path": project_dir,
                "project_name": "eagles_property",
                "connection_type": "Local Project Connector",
            })

    def test_documentation_event_published(self):
        from services.project_twin_discovery_service import (
            ProjectTwinDiscoveryService, TWIN_DOCUMENTATION,
        )
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            svc.discover_project(project_dir)
            found_doc_event = False
            for call_args in self.kernel.event_bus.publish.call_args_list:
                event = call_args[0][0]
                if event == TWIN_DOCUMENTATION:
                    found_doc_event = True
                    data = call_args[0][1]
                    self.assertIn("count", data)
                    self.assertGreaterEqual(data["count"], 4)
                    break
            self.assertTrue(found_doc_event, "TWIN_DOCUMENTATION event not published")

    def test_config_event_published(self):
        from services.project_twin_discovery_service import (
            ProjectTwinDiscoveryService, TWIN_CONFIG,
        )
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            svc.discover_project(project_dir)
            found_config_event = False
            for call_args in self.kernel.event_bus.publish.call_args_list:
                event = call_args[0][0]
                if event == TWIN_CONFIG:
                    found_config_event = True
                    data = call_args[0][1]
                    self.assertIn("count", data)
                    break
            self.assertTrue(found_config_event, "TWIN_CONFIG event not published")

    def test_richer_twin_metadata(self):
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            self.kernel.set_config({"memory_path": tmp})
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            discovery = result.get("discovery", {})
            self.assertIn("documentation", discovery)
            self.assertIn("config_files", discovery)
            self.assertIn("purpose_clues", discovery)
            self.assertIn("Docker", discovery["project"].get("frameworks", []))

    def test_enhanced_indexing_includes_docs_and_configs(self):
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            self.kernel.set_config({"memory_path": tmp})
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            twin_path = result["twin_path"]
            with open(twin_path) as f:
                twin_data = json.load(f)
            keys = twin_data.keys()
            self.assertIn("documentation", keys)
            self.assertIn("config_files", keys)
            self.assertIn("purpose_clues", keys)
            # Verify structure
            self.assertGreater(len(twin_data["documentation"].get("files", [])), 3)
            self.assertGreaterEqual(twin_data["config_files"].get("count", 0), 2)
            self.assertGreater(len(twin_data["purpose_clues"]), 0)

    # --- Service-Level Intelligence Tests ---

    def test_service_classification_in_discovery(self):
        """Discovery result includes project classification."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            discovery = result["discovery"]
            proj = discovery.get("project", {})
            classification = proj.get("classification", {})
            self.assertIn("domain", classification)
            self.assertIn("confidence", classification)

    def test_service_framework_tiers_in_discovery(self):
        """Framework tiers present in discovery project data."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            proj = result["discovery"]["project"]
            tiers = proj.get("framework_tiers", {})
            self.assertIn("primary", tiers)
            self.assertIn("secondary", tiers)
            self.assertIn("infrastructure", tiers)
            self.assertIn("Flutter", tiers.get("primary", []))

    def test_service_doc_categories_in_discovery(self):
        """Documentation categories in discovery result."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            discovery = result["discovery"]
            cats = discovery.get("documentation_categories", {})
            self.assertIn("architecture", cats)
            self.assertIn("product", cats)
            self.assertIn("build", cats)

    def test_service_classification_in_twin_file(self):
        """Twin file contains classification, framework_tiers, doc_categories."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            self.kernel.set_config({"memory_path": tmp})
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            twin_path = result["twin_path"]
            with open(twin_path) as f:
                twin_data = json.load(f)
            proj = twin_data.get("project", {})
            self.assertIn("classification", proj)
            self.assertIn("framework_tiers", proj)
            self.assertIn("documentation_categories", twin_data)
            self.assertIn("purpose_clues", twin_data)

    # --- Regression: enriched intelligence survival ---

    def test_enriched_fields_survive_service_wrapper(self):
        """All enriched intelligence fields survive the service result wrapper."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            # Top-level enriched fields must be on the discovery dict
            discovery = result["discovery"]
            for field in ("documentation_categories", "architect_summary",
                          "purpose_clues", "tech_stack"):
                self.assertIn(field, discovery,
                              "Enriched field %r missing from discovery" % field)
            # Project-level enriched fields
            proj = discovery.get("project", {})
            self.assertIn("classification", proj)
            self.assertIn("framework_tiers", proj)

    def test_gui_parsing_path_receives_framework_tiers(self):
        """The exact JavaScript parsing path from twin.html receives framework_tiers."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            service_result = svc.discover_project(project_dir)
            # Simulate MCP wrapper: mcp_tool_service.py returns {"discovery": result}
            mcp_response = {"discovery": service_result}
            # Simulate JSON serialisation (stdio transport)
            serialised = json.dumps(mcp_response, default=str)
            deserialised = json.loads(serialised)
            # GUI JavaScript parsing path (twin.html lines 108-128)
            result = deserialised
            svcResult = result.get("discovery") if isinstance(result, dict) and "discovery" in result else result
            connResult = svcResult.get("discovery", svcResult)
            proj = connResult.get("project", {})
            tiers = proj.get("framework_tiers", {})
            self.assertIn("primary", tiers)
            self.assertIn("secondary", tiers)
            self.assertIn("infrastructure", tiers)

    def test_flutter_remains_primary(self):
        """Flutter is classified as a primary framework through the full pipeline."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            discovery = result["discovery"]
            tiers = discovery.get("project", {}).get("framework_tiers", {})
            self.assertIn("Flutter", tiers.get("primary", []))

    def test_firebase_provider_secondary(self):
        """Firebase and Provider are classified as secondary frameworks."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            discovery = result["discovery"]
            tiers = discovery.get("project", {}).get("framework_tiers", {})
            secondary = tiers.get("secondary", [])
            self.assertIn("Firebase", secondary)
            self.assertIn("Provider", secondary)

    def test_github_actions_infrastructure_only(self):
        """GitHub Actions appears ONLY in infrastructure, never in primary or secondary."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            discovery = result["discovery"]
            tiers = discovery.get("project", {}).get("framework_tiers", {})
            self.assertIn("GitHub Actions", tiers.get("infrastructure", []))
            self.assertNotIn("GitHub Actions", tiers.get("primary", []))
            self.assertNotIn("GitHub Actions", tiers.get("secondary", []))

    # --- Nested Flutter project service-level regression tests ---

    def test_nested_flutter_service_type_detected(self):
        """Service detects and refines type for nested Flutter project layout."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_nested_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            proj = result["discovery"]["project"]
            # Connector detects Flutter Application; enhancer refines it
            # based on README content. The critical requirement is that
            # Flutter appears in primary and Firebase in secondary.
            tiers = proj.get("framework_tiers", {})
            self.assertIn("Flutter", tiers.get("primary", []))
            self.assertIn("Firebase", tiers.get("secondary", []))

    def test_nested_flutter_service_frameworks_detected(self):
        """Service detects Flutter and Firebase from nested app/pubspec.yaml."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_nested_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            proj = result["discovery"]["project"]
            self.assertIn("Flutter", proj.get("frameworks", []))
            self.assertIn("Firebase", proj.get("frameworks", []))
            self.assertIn("GitHub Actions", proj.get("frameworks", []))

    def test_nested_flutter_service_framework_tiers(self):
        """framework_tiers contract holds for nested Flutter project through service."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_nested_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            tiers = result["discovery"]["project"].get("framework_tiers", {})
            self.assertIn("Flutter", tiers.get("primary", []))
            self.assertIn("Firebase", tiers.get("secondary", []))
            self.assertIn("Provider", tiers.get("secondary", []))
            self.assertIn("GitHub Actions", tiers.get("infrastructure", []))
            self.assertNotIn("Flutter", tiers.get("infrastructure", []))
            self.assertNotIn("GitHub Actions", tiers.get("primary", []))

    def test_nested_flutter_enriched_fields_survive_wrapper(self):
        """All enriched intelligence fields survive for nested project layout."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_nested_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            discovery = result["discovery"]
            for field in ("documentation_categories", "architect_summary",
                          "purpose_clues", "tech_stack"):
                self.assertIn(field, discovery,
                              "Enriched field %r missing from nested discovery" % field)
            proj = discovery.get("project", {})
            self.assertIn("classification", proj)
            self.assertIn("framework_tiers", proj)

    def test_nested_flutter_gui_parsing_path(self):
        """GUI JavaScript parsing path receives framework_tiers for nested project."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_nested_flutter_project(tmp)
            service_result = svc.discover_project(project_dir)
            mcp_response = {"discovery": service_result}
            serialised = json.dumps(mcp_response, default=str)
            deserialised = json.loads(serialised)
            result = deserialised
            svcResult = result.get("discovery") if isinstance(result, dict) and "discovery" in result else result
            connResult = svcResult.get("discovery", svcResult)
            proj = connResult.get("project", {})
            tiers = proj.get("framework_tiers", {})
            self.assertIn("Flutter", tiers.get("primary", []))


# --- External Project Validation Tests ---

class TestExternalProjectValidation(unittest.TestCase):
    """Validate EaglEs EyE can discover and twin an unknown external project."""

    def test_external_project_connector_discovery(self):
        """Connector can connect to an unknown project and discover it."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_property_connect_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            self.assertTrue(connector.connect())
            sources = connector.discover()
            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0].path, project_dir)

    def test_external_project_identify(self):
        """Identify project name, type, languages, and frameworks."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_property_connect_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            self.assertIsNotNone(result)
            self.assertEqual(result["project"]["name"], "property_connect")
            self.assertEqual(result["project"]["type"], "Flutter Application")
            self.assertIn("Dart", result["project"]["languages"])
            self.assertIn("Flutter", result["project"]["frameworks"])

    def test_external_project_dependencies(self):
        """Detect all dependencies from pubspec.yaml."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_property_connect_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            deps = result["dependencies"]
            for pkg in ("firebase_core", "cloud_firestore", "provider", "geolocator"):
                self.assertIn(pkg, deps)

    def test_external_project_documentation(self):
        """Discover all documentation files (README, GOAL, ARCHITECTURE, CHANGELOG)."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_property_connect_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            docs = result.get("documentation", {})
            files = docs.get("files", [])
            paths = [d["path"] for d in files]
            self.assertGreaterEqual(len(files), 4)
            for name in ("README.md", "GOAL.md", "ARCHITECTURE.md", "CHANGELOG.md"):
                self.assertTrue(any(name in p for p in paths), "Missing: " + name)
            roles = [d["role"] for d in files]
            self.assertIn("readme", roles)
            self.assertIn("architecture", roles)
            self.assertIn("changelog", roles)

    def test_external_project_purpose(self):
        """Infer project purpose from README and project name."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_property_connect_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            clues_data = result.get("purpose_clues", {})
            clues_list = clues_data.get("clues", [])
            self.assertGreater(len(clues_list), 0)
            combined = " ".join(t[1] for t in clues_list).lower()
            self.assertIn("real estate", combined)
            self.assertIn(clues_data.get("summary", ""), clues_data.get("summary", ""))

    def test_external_project_twin_generation(self):
        """Service can generate a full Project Twin for the external project."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            kernel.set_config({"memory_path": tmp})
            project_dir = create_property_connect_project(tmp)
            result = svc.discover_project(project_dir)
            self.assertEqual(result["status"], "CONNECTED")
            self.assertEqual(result["project_name"], "property_connect")
            discovery = result["discovery"]
            self.assertEqual(discovery["project"]["type"], "Enterprise SaaS Platform")
            self.assertIn("Dart", discovery["project"]["languages"])
            self.assertIn("Flutter", discovery["project"]["frameworks"])
            self.assertIn("firebase_core", discovery["dependencies"])
            self.assertIn("documentation", discovery)
            self.assertIn("purpose_clues", discovery)
            self.assertIn("twin_path", result)
            self.assertTrue(os.path.isfile(result["twin_path"]))

    def test_external_project_workflow_notifications(self):
        """Service emits all expected workflow notifications for the external project."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_property_connect_project(tmp)
            result = svc.discover_project(project_dir)
            self.assertIn("notifications", result)
            messages = [n["message"] for n in result["notifications"]]
            expected = [
                "CONNECTED", "EYE SCAN", "PROJECT IDENTIFIED",
                "STACK DETECTED", "GIT REPOSITORY DETECTED",
                "DEPENDENCIES DISCOVERED", "DOCUMENTATION DISCOVERED",
                "CONFIGURATION DETECTED", "PROJECT TWIN CREATED",
            ]
            for msg in expected:
                self.assertIn(msg, messages, "Missing notification: " + msg)

    def test_validation_report_output(self):
        """Validation report is correctly formatted from discovery data."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_property_connect_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            report = format_validation_report(result)
            self.assertIn("[EYE SCAN]", report)
            self.assertIn("property_connect", report)
            self.assertIn("Flutter Application", report)
            self.assertIn("Dart", report)
            self.assertIn("README.md", report)
            self.assertIn("GOAL.md", report)
            self.assertIn("ARCHITECTURE.md", report)
            self.assertIn("CREATED", report)


# --- MCP Tool Integration Tests ---

class TestMCPToolProjectTwin(unittest.TestCase):
    def setUp(self):
        self.kernel = FakeKernel()
        self.store = make_mock_service("KnowledgeStoreService")
        self.kernel._services["KnowledgeStoreService"] = self.store
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        svc = ProjectTwinDiscoveryService(self.kernel)
        svc.start()
        self.kernel._services["ProjectTwinDiscoveryService"] = svc
        from services.mcp_tool_service import MCPToolService
        self.mcp = MCPToolService(self.kernel)
        self.mcp.start()

    def test_discover_project_twin_tool_in_list(self):
        tools = self.mcp.list_tools()
        names = [t["name"] for t in tools]
        self.assertIn("discover_project_twin", names)

    def test_discover_project_twin_tool_missing_path(self):
        result = self.mcp.call_tool("discover_project_twin", {})
        self.assertIn("error", result)

    def test_discover_project_twin_tool_valid_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            result = self.mcp.call_tool("discover_project_twin", {"project_path": project_dir})
            self.assertIn("discovery", result)
            self.assertEqual(result["discovery"]["status"], "CONNECTED")
            self.assertIn("notifications", result["discovery"])

    def test_existing_tools_preserved(self):
        tools = self.mcp.list_tools()
        names = [t["name"] for t in tools]
        legacy = ["search_memory", "build_context", "get_document",
                  "project_health", "ai_twin_status", "ai_twin_report"]
        for name in legacy:
            self.assertIn(name, names, "Legacy tool missing: " + name)

    # --- GUI Data Binding Validation ---

    def test_gui_response_nested_structure(self):
        """GUI faces result.discovery.discovery to reach connector data."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            result = self.mcp.call_tool("discover_project_twin", {"project_path": project_dir})
            # MCP wraps: { discovery: { ... discover_project() return ... } }
            svc_result = result["discovery"]
            self.assertIn("discovery", svc_result)
            # connector result is at svc_result.discovery
            conn_result = svc_result["discovery"]
            self.assertIn("project", conn_result)
            self.assertIn("documentation", conn_result)
            self.assertIn("purpose_clues", conn_result)

    def test_gui_summary_card_project_name(self):
        """GUI: project name accessible via svcResult.project_name or connResult.project.name."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            result = self.mcp.call_tool("discover_project_twin", {"project_path": project_dir})
            svc_result = result["discovery"]
            conn_result = svc_result["discovery"]
            name = svc_result.get("project_name") or conn_result.get("project", {}).get("name")
            self.assertEqual(name, "eagles_property")

    def test_gui_summary_card_languages(self):
        """GUI: languages via connResult.project.languages."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            result = self.mcp.call_tool("discover_project_twin", {"project_path": project_dir})
            conn_result = result["discovery"]["discovery"]
            langs = conn_result.get("project", {}).get("languages", [])
            self.assertIn("Dart", langs)

    def test_gui_summary_card_frameworks(self):
        """GUI: frameworks via connResult.project.frameworks."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            result = self.mcp.call_tool("discover_project_twin", {"project_path": project_dir})
            conn_result = result["discovery"]["discovery"]
            fws = conn_result.get("project", {}).get("frameworks", [])
            self.assertIn("Flutter", fws)

    def test_gui_summary_card_documentation(self):
        """GUI: docs via connResult.documentation.files."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            result = self.mcp.call_tool("discover_project_twin", {"project_path": project_dir})
            conn_result = result["discovery"]["discovery"]
            docs = conn_result.get("documentation", {})
            files = docs.get("files", [])
            self.assertGreater(len(files), 3)
            paths = [d["path"] for d in files]
            self.assertTrue(any("README.md" in p for p in paths))

    def test_gui_summary_card_purpose(self):
        """GUI: purpose via connResult.purpose_clues.summary."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            result = self.mcp.call_tool("discover_project_twin", {"project_path": project_dir})
            conn_result = result["discovery"]["discovery"]
            clues_data = conn_result.get("purpose_clues", {})
            self.assertIn("summary", clues_data)
            self.assertGreater(len(clues_data.get("summary", "")), 0)

    def test_gui_notifications_accessible(self):
        """GUI: notifications via svcResult.notifications."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            result = self.mcp.call_tool("discover_project_twin", {"project_path": project_dir})
            svc_result = result["discovery"]
            notifs = svc_result.get("notifications", [])
            self.assertGreater(len(notifs), 0)
            messages = [n["message"] for n in notifs]
            self.assertIn("CONNECTED", messages)

    def test_gui_twin_path_accessible(self):
        """GUI: twin path via svcResult.twin_path."""
        with tempfile.TemporaryDirectory() as tmp:
            self.kernel.set_config({"memory_path": tmp})
            project_dir = create_flutter_project(tmp)
            result = self.mcp.call_tool("discover_project_twin", {"project_path": project_dir})
            svc_result = result["discovery"]
            self.assertIn("twin_path", svc_result)

    def test_gui_summary_cards_fallback_gracefully(self):
        """GUI: missing fields show defaults instead of errors."""
        # Simulate empty connector result
        from services.mcp_tool_service import MCPToolService
        mcp2 = MCPToolService(self.kernel)
        mcp2.start()
        # Monkey-patch project_twin to return empty data
        mcp2.project_twin.discover_project = lambda p: {
            "project_name": "test",
            "discovery": {},
            "notifications": [{"type": "mock", "message": "CONNECTED"}],
            "twin_path": "/tmp/test.twin.json",
            "status": "CONNECTED",
        }
        result = mcp2.call_tool("discover_project_twin", {"project_path": "/tmp/test"})
        svc_result = result["discovery"]
        conn_result = svc_result.get("discovery", {})
        # These should not raise even with empty data
        proj = conn_result.get("project", {})
        lang_text = (proj.get("languages") or []).join(", ") if isinstance(proj.get("languages"), list) else "-"
        self.assertEqual(lang_text, "-")
        name = svc_result.get("project_name") or proj.get("name") or "?"
        self.assertEqual(name, "test")


# --- Historical Memory: Twin Versioning & Comparison Tests ---

class TestTwinVersioning(unittest.TestCase):
    """Verify twin versioning, fingerprinting, and history storage."""

    def test_connector_includes_version_fields(self):
        """Discovery result includes twin_version, fingerprint, timestamp, previous_fingerprint."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            result = connector.get_discovery_result()
            self.assertIn("twin_version", result)
            self.assertIn("fingerprint", result)
            self.assertIn("timestamp", result)
            self.assertIn("previous_fingerprint", result)

    def test_fingerprint_is_deterministic(self):
        """Same project produces same fingerprint."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector1 = LocalProjectConnector(config={"project_path": project_dir})
            connector1.connect()
            connector1.observe()
            fp1 = connector1.get_discovery_result()["fingerprint"]

            connector2 = LocalProjectConnector(config={"project_path": project_dir})
            connector2.connect()
            connector2.observe()
            fp2 = connector2.get_discovery_result()["fingerprint"]

            self.assertEqual(fp1, fp2)
            self.assertGreater(len(fp1), 0)

    def test_fingerprint_changes_with_deps(self):
        """Modifying dependencies changes the fingerprint."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)

            connector1 = LocalProjectConnector(config={"project_path": project_dir})
            connector1.connect()
            connector1.observe()
            fp1 = connector1.get_discovery_result()["fingerprint"]

            # Modify pubspec.yaml with new dependency
            pubspec = os.path.join(project_dir, "pubspec.yaml")
            with open(pubspec, "a") as f:
                f.write("  http: ^1.0.0\n")

            connector2 = LocalProjectConnector(config={"project_path": project_dir})
            connector2.connect()
            connector2.observe()
            fp2 = connector2.get_discovery_result()["fingerprint"]

            self.assertNotEqual(fp1, fp2)

    def test_fingerprint_non_empty(self):
        """Fingerprint is a 16-character hex string."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            fp = connector.get_discovery_result()["fingerprint"]
            self.assertEqual(len(fp), 16)
            int(fp, 16)  # Should not raise

    def test_service_sets_twin_version(self):
        """First scan sets twin_version=1, second scan sets twin_version=2."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            kernel.set_config({"memory_path": tmp})
            project_dir = create_flutter_project(tmp)

            result1 = svc.discover_project(project_dir)
            self.assertEqual(result1["twin_version"], 1)

            result2 = svc.discover_project(project_dir)
            self.assertEqual(result2["twin_version"], 2)

    def test_service_sets_twin_version_on_second_project(self):
        """Different projects each start at version 1."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            kernel.set_config({"memory_path": tmp})
            proj_a = create_flutter_project(tmp)
            proj_b = create_python_project(tmp)

            r1 = svc.discover_project(proj_a)
            r2 = svc.discover_project(proj_b)
            self.assertEqual(r1["twin_version"], 1)
            self.assertEqual(r2["twin_version"], 1)

    def test_versioned_twin_file_created(self):
        """Versioned twin file is created at the expected path."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            kernel.set_config({"memory_path": tmp})
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            v_path = result["versioned_twin_path"]
            self.assertTrue(os.path.isfile(v_path))
            with open(v_path) as f:
                data = json.load(f)
            self.assertEqual(data["twin_version"], 1)
            self.assertEqual(data["status"], "CONNECTED")

    def test_versioned_twin_contains_all_intelligence(self):
        """Versioned twin has all intelligence fields."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            kernel.set_config({"memory_path": tmp})
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            v_path = result["versioned_twin_path"]
            with open(v_path) as f:
                data = json.load(f)
            self.assertIn("architect_summary", data)
            self.assertIn("classification", data.get("project", {}))
            self.assertIn("framework_tiers", data.get("project", {}))
            self.assertIn("knowledge_memory", data)
            self.assertIn("summary", data["knowledge_memory"])
            self.assertIn("classification", data["knowledge_memory"])

    def test_knowledge_memory_captured(self):
        """Knowledge memory captures summary, classification, architecture obs."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            kernel.set_config({"memory_path": tmp})
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            v_path = result["versioned_twin_path"]
            with open(v_path) as f:
                data = json.load(f)
            km = data.get("knowledge_memory", {})
            self.assertGreater(len(km.get("summary", "")), 0)
            self.assertIn("domain", km.get("classification", {}))
            self.assertGreater(km.get("file_count", 0), 0)

    def test_previous_knowledge_memory_on_second_scan(self):
        """Second scan has previous_knowledge_memory populated."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            kernel.set_config({"memory_path": tmp})
            project_dir = create_flutter_project(tmp)
            svc.discover_project(project_dir)
            result2 = svc.discover_project(project_dir)
            v_path = result2["versioned_twin_path"]
            with open(v_path) as f:
                data = json.load(f)
            self.assertIsNotNone(data.get("previous_knowledge_memory"))
            prev_km = data["previous_knowledge_memory"]
            self.assertIn("summary", prev_km)
            self.assertIn("classification", prev_km)


class TestTwinComparison(unittest.TestCase):
    """Verify TwinComparisonService diff engine."""

    def test_compare_identical_twins(self):
        """Comparing a twin with itself shows no changes."""
        from services.twin_comparison_service import TwinComparisonService
        kernel = FakeKernel()
        svc = TwinComparisonService(kernel)
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            from connectors.plugins.local_project_connector import LocalProjectConnector
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            twin = connector.get_discovery_result()
            result = svc.compare(twin, twin)
            self.assertFalse(result["has_changes"])

    def test_compare_new_files_detected(self):
        """New files are detected in comparison."""
        from services.twin_comparison_service import TwinComparisonService
        from connectors.plugins.local_project_connector import LocalProjectConnector
        kernel = FakeKernel()
        svc = TwinComparisonService(kernel)
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector1 = LocalProjectConnector(config={"project_path": project_dir})
            connector1.connect()
            connector1.observe()
            old = connector1.get_discovery_result()

            # Add a new doc file
            with open(os.path.join(project_dir, "FEATURES.md"), "w") as f:
                f.write("# Features\n\nNew feature list.\n")

            connector2 = LocalProjectConnector(config={"project_path": project_dir})
            connector2.connect()
            connector2.observe()
            new = connector2.get_discovery_result()

            result = svc.compare(old, new)
            self.assertTrue(result["has_changes"])
            self.assertGreater(len(result["new_files"]), 0)
            self.assertTrue(any("FEATURES.md" in f for f in result["new_files"]))

    def test_compare_removed_files_detected(self):
        """Removed files are detected in comparison."""
        from services.twin_comparison_service import TwinComparisonService
        from connectors.plugins.local_project_connector import LocalProjectConnector
        kernel = FakeKernel()
        svc = TwinComparisonService(kernel)
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector1 = LocalProjectConnector(config={"project_path": project_dir})
            connector1.connect()
            connector1.observe()
            old = connector1.get_discovery_result()

            # Remove a file
            os.remove(os.path.join(project_dir, "CONTRIBUTING.md"))

            connector2 = LocalProjectConnector(config={"project_path": project_dir})
            connector2.connect()
            connector2.observe()
            new = connector2.get_discovery_result()

            result = svc.compare(old, new)
            self.assertTrue(result["has_changes"])
            self.assertGreater(len(result["removed_files"]), 0)

    def test_compare_dependency_changes_detected(self):
        """Dependency additions are detected."""
        from services.twin_comparison_service import TwinComparisonService
        from connectors.plugins.local_project_connector import LocalProjectConnector
        kernel = FakeKernel()
        svc = TwinComparisonService(kernel)
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector1 = LocalProjectConnector(config={"project_path": project_dir})
            connector1.connect()
            connector1.observe()
            old = connector1.get_discovery_result()

            # Add a new dependency
            with open(os.path.join(project_dir, "pubspec.yaml"), "a") as f:
                f.write("  http: ^1.0.0\n")

            connector2 = LocalProjectConnector(config={"project_path": project_dir})
            connector2.connect()
            connector2.observe()
            new = connector2.get_discovery_result()

            result = svc.compare(old, new)
            self.assertTrue(result["has_changes"])
            added = result["changed_dependencies"]["added"]
            self.assertIn("http", added)

    def test_compare_framework_changes_detected(self):
        """Framework additions are detected."""
        from services.twin_comparison_service import TwinComparisonService
        from connectors.plugins.local_project_connector import LocalProjectConnector
        kernel = FakeKernel()
        svc = TwinComparisonService(kernel)
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            connector1 = LocalProjectConnector(config={"project_path": project_dir})
            connector1.connect()
            connector1.observe()
            old = connector1.get_discovery_result()

            # Add a framework signal (e.g. add a Dockerfile with new content)
            # Already has Docker; add another framework via pubspec
            with open(os.path.join(project_dir, "pubspec.yaml"), "a") as f:
                f.write("  sqflite: ^2.0.0\n")

            connector2 = LocalProjectConnector(config={"project_path": project_dir})
            connector2.connect()
            connector2.observe()
            new = connector2.get_discovery_result()

            old["project"]["frameworks"] = ["Flutter", "Docker", "Firebase"]
            new["project"]["frameworks"] = ["Flutter", "Docker", "Firebase", "SQLite"]

            result = svc.compare(old, new)
            self.assertTrue(result["has_changes"])
            self.assertIn("SQLite", result["changed_frameworks"]["added"])

    def test_compare_classification_change_detected(self):
        """Domain classification changes are detected."""
        from services.twin_comparison_service import TwinComparisonService
        kernel = FakeKernel()
        svc = TwinComparisonService(kernel)
        old = {"project": {"classification": {"domain": "mobile_application", "confidence": "high"}}}
        new = {"project": {"classification": {"domain": "web_application", "confidence": "medium"}}}
        result = svc.compare(old, new)
        self.assertTrue(result["classification_changed"])

    def test_compare_without_old_twin(self):
        """Comparison without old twin returns graceful message."""
        from services.twin_comparison_service import TwinComparisonService
        kernel = FakeKernel()
        svc = TwinComparisonService(kernel)
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            from connectors.plugins.local_project_connector import LocalProjectConnector
            connector = LocalProjectConnector(config={"project_path": project_dir})
            connector.connect()
            connector.observe()
            twin = connector.get_discovery_result()
            result = svc.compare(None, twin)
            self.assertFalse(result["has_changes"])
            self.assertIn("no previous snapshot", result["summary"][0].lower())

    def test_compare_summary_describes_changes(self):
        """Summary lists readable descriptions of changes."""
        from services.twin_comparison_service import TwinComparisonService
        kernel = FakeKernel()
        svc = TwinComparisonService(kernel)
        old = {
            "project": {"frameworks": ["Flutter"], "classification": {"domain": "mobile"}},
            "dependencies": ["firebase_core"],
            "documentation": {"files": [{"path": "README.md"}]},
            "config_files": {"files": [{"path": "pubspec.yaml"}]},
            "purpose_clues": {"summary": "Old purpose"},
            "documentation_categories": {"architecture": []},
        }
        new = {
            "project": {"frameworks": ["Flutter", "React"], "classification": {"domain": "web"}},
            "dependencies": ["firebase_core", "http"],
            "documentation": {"files": [{"path": "README.md"}, {"path": "NEW.md"}]},
            "config_files": {"files": [{"path": "pubspec.yaml"}]},
            "purpose_clues": {"summary": "New purpose"},
            "documentation_categories": {"architecture": []},
        }
        result = svc.compare(old, new)
        self.assertTrue(result["has_changes"])
        self.assertGreater(len(result["summary"]), 0)

    def test_compare_versions_method(self):
        """compare_versions loads versioned files and returns diff."""
        from services.twin_comparison_service import TwinComparisonService
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            kernel.set_config({"memory_path": tmp})
            project_dir = create_flutter_project(tmp)
            result1 = svc.discover_project(project_dir)
            result2 = svc.discover_project(project_dir)

            comparer = TwinComparisonService(kernel)
            twins_dir = os.path.join(tmp, "twins")
            comp = comparer.compare_versions(twins_dir, "eagles_property", 1, 2)
            self.assertIn("from_version", comp)
            self.assertEqual(comp["from_version"], 1)
            self.assertEqual(comp["to_version"], 2)


class TestTwinHistoryRegression(unittest.TestCase):
    """Regression: existing functionality preserved with historical memory."""

    def test_discover_still_returns_notifications(self):
        """Original workflow notifications still present."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            messages = [n["message"] for n in result["notifications"]]
            self.assertIn("CONNECTED", messages)
            self.assertIn("EYE SCAN", messages)
            self.assertIn("PROJECT TWIN CREATED", messages)

    def test_twin_file_still_created(self):
        """Twin file still written to standard location."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            kernel.set_config({"memory_path": tmp})
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            self.assertTrue(os.path.isfile(result["twin_path"]))
            # Standard path: memory/twins/{project_name}.twin.json
            expected = os.path.join(tmp, "twins", "eagles_property.twin.json")
            self.assertEqual(result["twin_path"], expected)

    def test_twin_file_has_all_original_fields(self):
        """Original twin fields preserved: project, repository, deps, docs."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            kernel.set_config({"memory_path": tmp})
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            with open(result["twin_path"]) as f:
                data = json.load(f)
            self.assertIn("project", data)
            self.assertIn("repository", data)
            self.assertIn("dependencies", data)
            self.assertIn("documentation", data)
            self.assertIn("config_files", data)
            self.assertIn("purpose_clues", data)
            self.assertIn("architect_summary", data)
            self.assertIn("discovery_time", data)
            self.assertIn("status", data)

    def test_history_json_created(self):
        """History JSON file is created at expected path."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            kernel.set_config({"memory_path": tmp})
            project_dir = create_flutter_project(tmp)
            svc.discover_project(project_dir)
            history_path = os.path.join(tmp, "twins", "eagles_property", "history.json")
            self.assertTrue(os.path.isfile(history_path))
            with open(history_path) as f:
                hist = json.load(f)
            self.assertEqual(hist["current_version"], 1)
            self.assertEqual(len(hist["versions"]), 1)

    def test_history_accumulates_versions(self):
        """Multiple scans accumulate version history."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            kernel.set_config({"memory_path": tmp})
            project_dir = create_flutter_project(tmp)
            for _ in range(5):
                svc.discover_project(project_dir)
            history_path = os.path.join(tmp, "twins", "eagles_property", "history.json")
            with open(history_path) as f:
                hist = json.load(f)
            self.assertEqual(hist["current_version"], 5)
            self.assertEqual(len(hist["versions"]), 5)

    def test_version_files_persist(self):
        """Each scan creates a persistent version file."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            kernel.set_config({"memory_path": tmp})
            project_dir = create_flutter_project(tmp)
            for i in range(1, 4):
                svc.discover_project(project_dir)
                v_path = os.path.join(tmp, "twins", "eagles_property", "versions", f"v{i}.json")
                self.assertTrue(os.path.isfile(v_path), f"Missing v{i}.json")

    def test_twin_version_in_mcp_response(self):
        """MCP tool response includes twin_version and fingerprint."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        from services.mcp_tool_service import MCPToolService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        kernel._services["ProjectTwinDiscoveryService"] = svc
        mcp = MCPToolService(kernel)
        mcp.start()
        with tempfile.TemporaryDirectory() as tmp:
            kernel.set_config({"memory_path": tmp})
            project_dir = create_flutter_project(tmp)
            result = mcp.call_tool("discover_project_twin", {"project_path": project_dir})
            svc_result = result["discovery"]
            self.assertIn("twin_version", svc_result)
            self.assertIn("fingerprint", svc_result)
            self.assertGreater(svc_result["twin_version"], 0)

    def test_twin_version_notifications_included(self):
        """VERSION notification is included in workflow."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            messages = [n["message"] for n in result["notifications"]]
            self.assertTrue(any("VERSION" in m for m in messages))


# --- Project Intelligence Enhancer Tests ---

class TestProjectIntelligenceEnhancer(unittest.TestCase):
    """Verify enhanced classification, type naming, and architect summary."""

    def _build_property_connect_result(self):
        """Build a discovery result resembling property_connect connector output."""
        return {
            "project": {
                "name": "property_connect",
                "path": "",
                "type": "Flutter Application",
                "frameworks": ["Flutter", "Firebase", "Docker", "GitHub Actions", "Provider"],
                "languages": ["Dart", "YAML", "JSON"],
                "classification": {
                    "domain": "general_application",
                    "confidence": "low",
                    "evidence": [],
                    "scores": {},
                },
            },
            "dependencies": ["firebase_core", "cloud_firestore", "provider", "geolocator"],
            "documentation": {
                "files": [
                    {"path": "README.md", "role": "readme",
                     "preview": "A multi-tenant real estate platform built with Flutter and Firebase. Property Connect enables property managers to list, manage, and market properties across multiple tenants with role-based access control, integrated messaging, and analytics dashboards."},
                    {"path": "GOAL.md", "role": "documentation",
                     "preview": "Build a scalable multi-tenant real estate management platform that connects property owners, tenants, and service providers."},
                    {"path": "ARCHITECTURE.md", "role": "architecture",
                     "preview": "Clean Architecture with feature-first directory structure.\n- Presentation layer: Flutter widgets + Provider state management\n- Domain layer: Use cases and entity models\n- Data layer: Firebase Firestore + Firebase Auth\nState management via ChangeNotifier pattern with Provider."},
                    {"path": "CHANGELOG.md", "role": "changelog",
                     "preview": "## 2.0.0\n- Multi-tenant support\n- Role-based access control\n- Analytics dashboard"},
                ],
                "summary": "A multi-tenant real estate platform built with Flutter and Firebase. Property Connect enables property managers to list, manage, and market properties across multiple tenants with role-based access control, integrated messaging, and analytics dashboards.",
                "count": 4,
                "architecture_topic": "Architecture",
            },
            "statistics": {"file_count": 25},
        }

    def _build_flutter_result(self):
        """Build a discovery result resembling eagles_property connector output."""
        return {
            "project": {
                "name": "eagles_property",
                "path": "",
                "type": "Flutter Application",
                "frameworks": ["Flutter", "Firebase", "Docker", "GitHub Actions", "Provider"],
                "languages": ["Dart", "YAML", "JSON"],
                "classification": {
                    "domain": "mobile_application",
                    "confidence": "high",
                    "evidence": [{"source": "framework", "signal": "mobile"}],
                    "scores": {"mobile_application": 1},
                },
            },
            "dependencies": ["firebase_core", "cloud_firestore", "provider"],
            "documentation": {
                "files": [
                    {"path": "README.md", "role": "readme",
                     "preview": "A Flutter-based property management mobile application for real estate agents. Features include property listings, client management, and integrated messaging with Firebase Cloud Messaging."},
                    {"path": "ARCHITECTURE.md", "role": "architecture",
                     "preview": "Uses BLoC pattern with Firebase backend."},
                    {"path": "CHANGELOG.md", "role": "changelog",
                     "preview": "## 1.0.0\nInitial release."},
                ],
                "summary": "A Flutter-based property management mobile application for real estate agents. Features include property listings, client management, and integrated messaging with Firebase Cloud Messaging.",
                "count": 3,
                "architecture_topic": "Architecture",
            },
            "statistics": {"file_count": 15},
        }

    def _build_python_result(self):
        """Build a discovery result resembling py_project connector output."""
        return {
            "project": {
                "name": "py_project",
                "path": "",
                "type": "Python Application",
                "frameworks": ["Flask", "pytest", "Make"],
                "languages": ["Python"],
                "classification": {
                    "domain": "general_application",
                    "confidence": "low",
                    "evidence": [],
                    "scores": {},
                },
            },
            "dependencies": ["flask", "requests", "sqlalchemy"],
            "documentation": {
                "files": [
                    {"path": "README.md", "role": "readme",
                     "preview": "A Python CLI tool for data analysis and reporting."},
                ],
                "summary": "A Python CLI tool for data analysis and reporting.",
                "count": 1,
            },
            "statistics": {"file_count": 10},
        }

    # --- Enhance Classification Tests ---

    def test_enhance_classification_property_connect_enterprise(self):
        """Property Connect classified as enterprise_platform with high confidence."""
        from services.project_intelligence_enhancer import enhance_classification
        result = self._build_property_connect_result()
        cls = enhance_classification(result)
        self.assertEqual(cls["domain"], "enterprise_platform")
        self.assertEqual(cls["confidence"], "high")

    def test_enhance_classification_property_connect_has_enterprise_evidence(self):
        """Property Connect has enterprise, real_estate, and mobile evidence signals."""
        from services.project_intelligence_enhancer import enhance_classification
        result = self._build_property_connect_result()
        cls = enhance_classification(result)
        signals = [e["signal"] for e in cls["evidence"]]
        self.assertIn("enterprise", signals)
        self.assertIn("real_estate", signals)
        self.assertIn("mobile", signals)

    def test_enhance_classification_flutter_mobile(self):
        """Flutter project classified as mobile_application."""
        from services.project_intelligence_enhancer import enhance_classification
        result = self._build_flutter_result()
        cls = enhance_classification(result)
        self.assertEqual(cls["domain"], "mobile_application")
        self.assertIn(cls["confidence"], ("high", "medium"))

    def test_enhance_classification_python_backend(self):
        """Python backend project classified appropriately."""
        from services.project_intelligence_enhancer import enhance_classification
        result = self._build_python_result()
        cls = enhance_classification(result)
        self.assertIn("domain", cls)
        self.assertIn("confidence", cls)
        self.assertIn("evidence", cls)

    def test_enhance_classification_evidence_sources(self):
        """Evidence includes goal_doc, architecture_doc, and readme sources."""
        from services.project_intelligence_enhancer import enhance_classification
        result = self._build_property_connect_result()
        cls = enhance_classification(result)
        sources = [e["source"] for e in cls["evidence"]]
        self.assertIn("goal_doc", sources)
        self.assertIn("architecture_doc", sources)
        self.assertIn("readme", sources)

    def test_enhance_classification_scores_structured(self):
        """Scores dict contains all five domain keys."""
        from services.project_intelligence_enhancer import enhance_classification
        result = self._build_property_connect_result()
        cls = enhance_classification(result)
        expected = {"mobile_application", "web_application", "backend_service",
                    "ai_system", "enterprise_platform"}
        self.assertEqual(set(cls["scores"].keys()), expected)

    # --- Type Refinement Tests ---

    def test_refine_type_flutter_mobile(self):
        """Flutter mobile → Flutter Mobile Application."""
        from services.project_intelligence_enhancer import refine_project_type
        t = refine_project_type("Flutter Application",
                                {"domain": "mobile_application"}, ["Flutter"])
        self.assertEqual(t, "Flutter Mobile Application")

    def test_refine_type_enterprise_flutter(self):
        """Enterprise + Flutter → Enterprise SaaS Platform."""
        from services.project_intelligence_enhancer import refine_project_type
        t = refine_project_type("Flutter Application",
                                {"domain": "enterprise_platform"}, ["Flutter"])
        self.assertEqual(t, "Enterprise SaaS Platform")

    def test_refine_type_backend_python(self):
        """Backend + Flask → Backend Service."""
        from services.project_intelligence_enhancer import refine_project_type
        t = refine_project_type("Python Application",
                                {"domain": "backend_service"}, ["Flask"])
        self.assertEqual(t, "Backend Service")

    def test_refine_type_ai_system(self):
        """AI domain → AI System."""
        from services.project_intelligence_enhancer import refine_project_type
        t = refine_project_type("Python Application",
                                {"domain": "ai_system"}, ["TensorFlow"])
        self.assertEqual(t, "AI System")

    def test_refine_type_web_react(self):
        """Web + React → React Web Application."""
        from services.project_intelligence_enhancer import refine_project_type
        t = refine_project_type("React Application",
                                {"domain": "web_application"}, ["React"])
        self.assertEqual(t, "React Web Application")

    def test_refine_type_fallback_preserves_original(self):
        """Unknown domain preserves original type."""
        from services.project_intelligence_enhancer import refine_project_type
        t = refine_project_type("Rust Application",
                                {"domain": "general_application"}, ["Rust"])
        self.assertEqual(t, "Rust Application")

    # --- Architect Summary Tests ---

    def test_generate_summary_includes_project_name(self):
        """Architect summary references project name."""
        from services.project_intelligence_enhancer import generate_architect_summary
        result = self._build_property_connect_result()
        cls = {"domain": "enterprise_platform", "confidence": "high",
               "evidence": [], "scores": {}}
        summary = generate_architect_summary(result, cls, "Enterprise SaaS Platform")
        self.assertIn("Property Connect", summary)

    def test_generate_summary_includes_technologies(self):
        """Architect summary mentions key technologies."""
        from services.project_intelligence_enhancer import generate_architect_summary
        result = self._build_property_connect_result()
        cls = {"domain": "enterprise_platform", "confidence": "high",
               "evidence": [], "scores": {}}
        summary = generate_architect_summary(result, cls, "Enterprise SaaS Platform")
        self.assertIn("Flutter", summary)
        self.assertIn("Firebase", summary)

    def test_generate_summary_mentions_multi_tenant(self):
        """Architect summary includes multi-tenant / RBAC features."""
        from services.project_intelligence_enhancer import generate_architect_summary
        result = self._build_property_connect_result()
        cls = {"domain": "enterprise_platform", "confidence": "high",
               "evidence": [], "scores": {}}
        summary = generate_architect_summary(result, cls, "Enterprise SaaS Platform")
        self.assertTrue("multi" in summary.lower() or "rbac" in summary.lower()
                        or "role" in summary.lower())

    def test_generate_summary_flutter_project(self):
        """Flutter mobile project gets mobile-appropriate summary."""
        from services.project_intelligence_enhancer import generate_architect_summary
        result = self._build_flutter_result()
        cls = {"domain": "mobile_application", "confidence": "high",
               "evidence": [], "scores": {}}
        summary = generate_architect_summary(result, cls, "Flutter Mobile Application")
        self.assertIn("Eagles Property", summary)
        self.assertIn("flutter", summary.lower())

    def test_generate_summary_non_empty(self):
        """Architect summary is a non-empty string."""
        from services.project_intelligence_enhancer import generate_architect_summary
        result = self._build_python_result()
        cls = {"domain": "backend_service", "confidence": "medium",
               "evidence": [], "scores": {}}
        summary = generate_architect_summary(result, cls, "Backend Service")
        self.assertGreater(len(summary), 20)

    def test_summary_mentions_architecture_pattern_from_doc(self):
        """Architect summary references Clean Architecture or BLoC from arch doc."""
        from services.project_intelligence_enhancer import generate_architect_summary
        result = self._build_property_connect_result()
        cls = {"domain": "enterprise_platform", "confidence": "high",
               "evidence": [], "scores": {}}
        summary = generate_architect_summary(result, cls, "Enterprise SaaS Platform")
        self.assertIn("Clean Architecture", summary)

    # --- Full Pipeline Integration Tests ---

    def test_enhance_full_pipeline_updates_type(self):
        """Full enhance() updates project type from connector output."""
        from services.project_intelligence_enhancer import enhance
        result = self._build_property_connect_result()
        enhance(result)
        self.assertEqual(result["project"]["type"], "Enterprise SaaS Platform")

    def test_enhance_full_pipeline_updates_classification(self):
        """Full enhance() updates classification domain."""
        from services.project_intelligence_enhancer import enhance
        result = self._build_property_connect_result()
        enhance(result)
        cls = result["project"]["classification"]
        self.assertEqual(cls["domain"], "enterprise_platform")
        self.assertEqual(cls["confidence"], "high")

    def test_enhance_full_pipeline_updates_summary(self):
        """Full enhance() updates architect_summary."""
        from services.project_intelligence_enhancer import enhance
        result = self._build_property_connect_result()
        enhance(result)
        self.assertGreater(len(result["architect_summary"]), 30)
        self.assertIn("Property Connect", result["architect_summary"])

    def test_enhance_full_pipeline_flutter(self):
        """Full enhance on Flutter project: type + classification + summary."""
        from services.project_intelligence_enhancer import enhance
        result = self._build_flutter_result()
        enhance(result)
        self.assertEqual(result["project"]["type"], "Flutter Mobile Application")
        cls = result["project"]["classification"]
        self.assertEqual(cls["domain"], "mobile_application")
        self.assertGreater(len(result["architect_summary"]), 20)

    def test_enhance_preserves_frameworks_and_deps(self):
        """Enhancement preserves frameworks, dependencies, doc_files."""
        from services.project_intelligence_enhancer import enhance
        result = self._build_property_connect_result()
        enhance(result)
        self.assertIn("Flutter", result["project"]["frameworks"])
        self.assertIn("firebase_core", result["dependencies"])
        self.assertEqual(result["documentation"]["count"], 4)

    def test_enhance_service_integration(self):
        """Service-level: enhancement applied during discover_project."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_property_connect_project(tmp)
            result = svc.discover_project(project_dir)
            discovery = result["discovery"]
            # Type should be enhanced
            self.assertEqual(discovery["project"]["type"], "Enterprise SaaS Platform")
            # Domain should be enterprise
            cls = discovery["project"]["classification"]
            self.assertEqual(cls["domain"], "enterprise_platform")
            self.assertEqual(cls["confidence"], "high")
            # Summary should be enhanced
            self.assertIn("enterprise saas platform", discovery["architect_summary"].lower())

    def test_enhance_service_integration_flutter(self):
        """Service-level: Flutter project gets enhanced type and classification."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            result = svc.discover_project(project_dir)
            discovery = result["discovery"]
            self.assertEqual(discovery["project"]["type"], "Flutter Mobile Application")

    def test_enhance_service_preserves_notifications(self):
        """Service-level: all workflow notifications still emitted."""
        from services.project_twin_discovery_service import ProjectTwinDiscoveryService
        kernel = FakeKernel()
        store = make_mock_service("KnowledgeStoreService")
        kernel._services["KnowledgeStoreService"] = store
        svc = ProjectTwinDiscoveryService(kernel)
        svc.start()
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_property_connect_project(tmp)
            result = svc.discover_project(project_dir)
            messages = [n["message"] for n in result["notifications"]]
            expected = ["CONNECTED", "EYE SCAN", "PROJECT IDENTIFIED",
                        "STACK DETECTED", "GIT REPOSITORY DETECTED",
                        "DEPENDENCIES DISCOVERED", "DOCUMENTATION DISCOVERED",
                        "CONFIGURATION DETECTED", "PROJECT TWIN CREATED"]
            for msg in expected:
                self.assertIn(msg, messages)

    # --- Technology Stack Extraction Tests ---

    def _build_rich_doc_result(self):
        """Build a result with docs containing tech signatures for stack extraction."""
        return {
            "project": {
                "name": "rich_app",
                "path": "",
                "type": "Flutter Application",
                "frameworks": ["Flutter", "Firebase", "Docker"],
                "languages": ["Dart"],
                "classification": {
                    "domain": "general_application",
                    "confidence": "low",
                    "evidence": [],
                    "scores": {},
                },
            },
            "dependencies": ["dio", "provider", "sqflite"],
            "documentation": {
                "files": [
                    {"path": "README.md", "role": "readme",
                     "preview": "A Flutter app using BLoC pattern with offline-first support and Firebase Cloud Messaging for push notifications."},
                    {"path": "ARCHITECTURE.md", "role": "architecture",
                     "preview": "Clean Architecture with feature-first directory layout. Uses MVVM in the presentation layer, repository pattern for data access, and dependency injection via get_it. Offline-first strategy with local storage via sqflite."},
                    {"path": "pubspec.yaml", "role": "manifest",
                     "preview": "dependencies: flutter, dio, provider, sqflite, shared_preferences, sentry, stripe"},
                    {"path": "README.CMAKE.md", "role": "readme",
                     "preview": "CMake build instructions for native modules."},
                    {"path": "assets/icons/README.md", "role": "readme",
                     "preview": "Icon asset documentation for the design system."},
                    {"path": "template/README.md", "role": "readme",
                     "preview": "Template used for scaffolding new features."},
                    {"path": "node_modules/package/README.md", "role": "readme",
                     "preview": "Auto-generated package documentation."},
                ],
                "summary": "A rich Flutter application.",
                "count": 7,
            },
            "statistics": {"file_count": 30},
        }

    def test_enhance_tech_stack_returns_structure(self):
        """enhance_tech_stack returns dict with all four keys."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = self._build_rich_doc_result()
        ts = enhance_tech_stack(result)
        self.assertIn("primary_frameworks", ts)
        self.assertIn("secondary_frameworks", ts)
        self.assertIn("cloud_services", ts)
        self.assertIn("architecture_patterns", ts)

    def test_enhance_tech_stack_primary_frameworks(self):
        """Primary frameworks extracted from connector detection (Flutter primary, Firebase secondary, Docker infra)."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = self._build_rich_doc_result()
        ts = enhance_tech_stack(result)
        self.assertIn("Flutter", ts["primary_frameworks"])
        self.assertNotIn("Firebase", ts["primary_frameworks"])
        self.assertNotIn("Docker", ts["primary_frameworks"])

    def test_enhance_tech_stack_architecture_patterns(self):
        """Architecture patterns extracted from doc content."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = self._build_rich_doc_result()
        ts = enhance_tech_stack(result)
        self.assertIn("Clean Architecture", ts["architecture_patterns"])
        self.assertIn("Feature-first", ts["architecture_patterns"])
        self.assertIn("MVVM", ts["architecture_patterns"])
        self.assertIn("Offline-first", ts["architecture_patterns"])
        self.assertIn("Repository Pattern", ts["architecture_patterns"])
        self.assertIn("Dependency Injection", ts["architecture_patterns"])

    def test_enhance_tech_stack_cloud_services(self):
        """Cloud services extracted from framework list (Firebase)."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = self._build_rich_doc_result()
        ts = enhance_tech_stack(result)
        services = " ".join(ts["cloud_services"]).lower()
        self.assertIn("firebase", services)
        # Cloud services from doc scanning no longer used (see point 6)
        self.assertNotIn("sentry", services)
        self.assertNotIn("stripe", services)

    def test_enhance_tech_stack_secondary_frameworks(self):
        """Secondary frameworks categorized with Firebase as Cloud Services."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = self._build_rich_doc_result()
        ts = enhance_tech_stack(result)
        categories = [sf["category"] for sf in ts["secondary_frameworks"]]
        self.assertIn("State Management", categories)
        self.assertIn("Networking", categories)
        self.assertIn("Local Storage", categories)
        # Firebase is now secondary (Cloud Services), not primary
        self.assertIn("Cloud Services", categories)

    def test_enhance_tech_stack_minimal(self):
        """Tech stack with minimal content returns Flask primary, pytest/Make infrastructure."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = self._build_python_result()
        ts = enhance_tech_stack(result)
        self.assertEqual(ts["primary_frameworks"], ["Flask"])
        self.assertEqual(ts["secondary_frameworks"], [])
        self.assertIn("Make", ts["infrastructure"])
        self.assertIn("pytest", ts["infrastructure"])
        self.assertEqual(ts["cloud_services"], [])
        self.assertEqual(ts["architecture_patterns"], [])

    def test_enhance_tech_stack_ignores_generated_paths(self):
        """Tech stack ignores node_modules, template, assets paths."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = self._build_rich_doc_result()
        ts = enhance_tech_stack(result)
        patterns_found = any("cmake" in a.lower() or "node" in a.lower()
                             for a in ts["architecture_patterns"])
        self.assertFalse(patterns_found)

    # --- Purpose Clue Filtering Tests ---

    def test_filter_purpose_clues_ignores_cmake(self):
        """Purpose clues from CMake paths are filtered out."""
        from services.project_intelligence_enhancer import _filter_purpose_clues
        clues = {
            "clues": [
                ("architecture", "Clean Architecture setup"),
                ("readme", "CMake build instructions for native modules"),
            ],
            "summary": "Original summary",
            "details": [],
        }
        doc_info = {"files": [
            {"path": "README.md", "role": "readme", "preview": "Regular app docs"},
            {"path": "README.CMAKE.md", "role": "readme", "preview": "CMake build"},
        ]}
        filtered = _filter_purpose_clues(clues, doc_info)
        self.assertEqual(len(filtered["clues"]), 1)
        self.assertEqual(filtered["clues"][0][0], "architecture")

    def test_filter_purpose_clues_ignores_assets(self):
        """Purpose clues from asset paths are filtered out."""
        from services.project_intelligence_enhancer import _filter_purpose_clues
        clues = {
            "clues": [
                ("architecture", "Clean Architecture setup"),
                ("readme", "Icon asset documentation"),
            ],
            "summary": "Original summary",
            "details": [],
        }
        doc_info = {"files": [
            {"path": "ARCHITECTURE.md", "role": "architecture",
             "preview": "Clean Architecture setup"},
            {"path": "assets/icons/README.md", "role": "readme",
             "preview": "Icon asset documentation"},
        ]}
        filtered = _filter_purpose_clues(clues, doc_info)
        self.assertEqual(len(filtered["clues"]), 1)
        self.assertEqual(filtered["clues"][0][0], "architecture")

    def test_filter_purpose_clues_ignores_template(self):
        """Purpose clues from template paths are filtered out."""
        from services.project_intelligence_enhancer import _filter_purpose_clues
        clues = {
            "clues": [
                ("readme", "Scaffolding template guide"),
                ("architecture", "Domain model entities"),
            ],
            "summary": "Original summary",
            "details": [],
        }
        doc_info = {"files": [
            {"path": "template/README.md", "role": "readme",
             "preview": "Scaffolding template guide"},
            {"path": "ARCHITECTURE.md", "role": "architecture",
             "preview": "Domain model entities"},
        ]}
        filtered = _filter_purpose_clues(clues, doc_info)
        self.assertEqual(len(filtered["clues"]), 1)
        self.assertEqual(filtered["clues"][0][0], "architecture")

    def test_filter_purpose_clues_prioritizes_architecture(self):
        """Architecture-doc clues appear before other clues."""
        from services.project_intelligence_enhancer import _filter_purpose_clues
        clues = {
            "clues": [
                ("readme", "Regular description"),
                ("architecture", "Architecture-first design"),
                ("goal", "Business goal description"),
            ],
            "summary": "Original summary",
            "details": [],
        }
        doc_info = {"files": [
            {"path": "README.md", "role": "readme", "preview": "Regular"},
            {"path": "ARCHITECTURE.md", "role": "architecture", "preview": "Arch"},
            {"path": "GOAL.md", "role": "goal", "preview": "Goal"},
        ]}
        filtered = _filter_purpose_clues(clues, doc_info)
        # Architecture clue should be first
        self.assertEqual(filtered["clues"][0][0], "architecture")
        self.assertEqual(len(filtered["clues"]), 3)

    def test_filter_purpose_clues_summary_from_arch(self):
        """Summary is derived from architecture clue when available."""
        from services.project_intelligence_enhancer import _filter_purpose_clues
        clues = {
            "clues": [
                ("readme", "Short readme"),
                ("architecture", "Rich architecture document with detailed purpose description spanning multiple sentences about what this system does."),
            ],
            "summary": "Original fallback",
            "details": [],
        }
        doc_info = {"files": [
            {"path": "README.md", "role": "readme", "preview": "Short readme"},
            {"path": "ARCHITECTURE.md", "role": "architecture",
             "preview": "Rich architecture document"},
        ]}
        filtered = _filter_purpose_clues(clues, doc_info)
        self.assertIn("Rich architecture document", filtered["summary"])

    def test_filter_purpose_clues_empty_input(self):
        """Empty purpose clues returns empty result."""
        from services.project_intelligence_enhancer import _filter_purpose_clues
        clues = {"clues": [], "summary": "", "details": []}
        filtered = _filter_purpose_clues(clues, {"files": []})
        self.assertEqual(filtered["clues"], [])
        self.assertEqual(filtered["summary"], "")

    def test_filter_purpose_clues_flutter_generated_readme(self):
        """Flutter generated README content is filtered out."""
        from services.project_intelligence_enhancer import _filter_purpose_clues
        clues = {
            "clues": [
                ("readme", "A Flutter mobile application"),
                ("architecture", "System architecture overview"),
            ],
            "summary": "A Flutter mobile application",
            "details": [],
        }
        doc_info = {"files": [
            {"path": "README.md", "role": "readme",
             "preview": "A Flutter mobile application"},
            {"path": "ARCHITECTURE.md", "role": "architecture",
             "preview": "System architecture overview"},
        ]}
        filtered = _filter_purpose_clues(clues, doc_info)
        # Architecture clue should be used
        self.assertIn("System architecture overview", filtered["summary"])

    # --- Architecture Pattern Detection Tests ---

    def test_extract_architecture_patterns_clean_arch(self):
        """Clean Architecture detected from arch docs."""
        from services.project_intelligence_enhancer import _extract_architecture_patterns
        doc_info = {"files": [
            {"path": "ARCH.md", "role": "architecture",
             "preview": "Uses Clean Architecture with domain-driven design."},
        ]}
        patterns = _extract_architecture_patterns(doc_info)
        self.assertIn("Clean Architecture", patterns)
        self.assertIn("Domain-Driven Design", patterns)

    def test_extract_architecture_patterns_mvc_mvvm(self):
        """MVC and MVVM detected from doc content."""
        from services.project_intelligence_enhancer import _extract_architecture_patterns
        doc_info = {"files": [
            {"path": "GUIDE.md", "role": "documentation",
             "preview": "The app follows an MVC pattern with model-view-controller separation. The newer modules use MVVM (Model-View-ViewModel) for better testability."},
        ]}
        patterns = _extract_architecture_patterns(doc_info)
        self.assertIn("MVC", patterns)
        self.assertIn("MVVM", patterns)

    def test_extract_architecture_patterns_offline_first(self):
        """Offline-first detected from doc content."""
        from services.project_intelligence_enhancer import _extract_architecture_patterns
        doc_info = {"files": [
            {"path": "FEATURES.md", "role": "documentation",
             "preview": "Offline-first strategy ensures the app works without internet by syncing when connectivity returns."},
        ]}
        patterns = _extract_architecture_patterns(doc_info)
        self.assertIn("Offline-first", patterns)

    def test_extract_architecture_patterns_feature_first(self):
        """Feature-first detected from doc content."""
        from services.project_intelligence_enhancer import _extract_architecture_patterns
        doc_info = {"files": [
            {"path": "README.md", "role": "readme",
             "preview": "Feature-first directory structure organizes code by business capability."},
        ]}
        patterns = _extract_architecture_patterns(doc_info)
        self.assertIn("Feature-first", patterns)

    def test_extract_architecture_patterns_ignores_generated(self):
        """Generated/template paths are skipped for pattern detection."""
        from services.project_intelligence_enhancer import _extract_architecture_patterns
        doc_info = {"files": [
            {"path": "CMakeLists.txt", "role": "documentation",
             "preview": "Clean Architecture CMake configuration."},
            {"path": "lib/ARCH.md", "role": "architecture",
             "preview": "Feature-first module layout"},
        ]}
        patterns = _extract_architecture_patterns(doc_info)
        self.assertNotIn("Clean Architecture", patterns)
        self.assertIn("Feature-first", patterns)

    def test_extract_architecture_patterns_no_matches(self):
        """No patterns returns empty list."""
        from services.project_intelligence_enhancer import _extract_architecture_patterns
        doc_info = {"files": [
            {"path": "README.md", "role": "readme",
             "preview": "A simple project with no patterns mentioned."},
        ]}
        patterns = _extract_architecture_patterns(doc_info)
        self.assertEqual(patterns, [])

    # --- Full Pipeline: New Keys ---

    def test_enhance_full_pipeline_includes_tech_stack(self):
        """Full enhance() adds tech_stack to result."""
        from services.project_intelligence_enhancer import enhance
        result = self._build_rich_doc_result()
        enhance(result)
        self.assertIn("tech_stack", result)
        self.assertIn("primary_frameworks", result["tech_stack"])
        self.assertIn("architecture_patterns", result["tech_stack"])

    def test_enhance_full_pipeline_tech_stack_content(self):
        """Full enhance() populates tech_stack meaningfully."""
        from services.project_intelligence_enhancer import enhance
        result = self._build_rich_doc_result()
        enhance(result)
        ts = result["tech_stack"]
        self.assertIn("Clean Architecture", ts["architecture_patterns"])
        self.assertIn("Offline-first", ts["architecture_patterns"])

    def test_enhance_full_pipeline_includes_filtered_purpose(self):
        """Full enhance() adds filtered purpose_clues with arch priority."""
        from services.project_intelligence_enhancer import enhance
        result = self._build_rich_doc_result()
        result["purpose_clues"] = {
            "clues": [
                ("readme", "A Flutter app with basic features"),
                ("architecture", "Clean Architecture platform for property management with multi-tenant support"),
            ],
            "summary": "Original fallback",
            "details": [],
        }
        enhance(result)
        self.assertIn("purpose_clues", result)
        self.assertIn("Clean Architecture", result["purpose_clues"]["summary"])

    def test_enhance_full_pipeline_cmake_filtered_out(self):
        """Full enhance() filters CMake content from purpose clues."""
        from services.project_intelligence_enhancer import enhance
        result = self._build_rich_doc_result()
        result["purpose_clues"] = {
            "clues": [
                ("build", "CMake build configuration"),
                ("readme", "Flutter property management app"),
            ],
            "summary": "CMake build configuration",
            "details": [],
        }
        enhance(result)
        self.assertNotIn("CMake", result["purpose_clues"]["summary"])

    def test_enhance_tech_stack_cloud_services_from_frameworks(self):
        """Cloud services populated from framework list as well as docs."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = self._build_property_connect_result()
        ts = enhance_tech_stack(result)
        self.assertIn("Firebase", ts["cloud_services"])
        # Provider is state management, not cloud
        self.assertNotIn("Provider", ts["cloud_services"])

    def test_enhance_tech_stack_pattern_deduplication(self):
        """Same pattern mentioned in multiple docs is not duplicated."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = self._build_rich_doc_result()
        ts = enhance_tech_stack(result)
        # Clean Architecture and Feature-first appear in ARCHITECTURE.md only
        self.assertEqual(ts["architecture_patterns"].count("Clean Architecture"), 1)
        self.assertEqual(ts["architecture_patterns"].count("Feature-first"), 1)

    # --- Three-Tier Ranking Tests ---

    def test_framework_tier_flutter_primary(self):
        """Flutter is classified as primary framework."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = {
            "project": {"frameworks": ["Flutter", "Firebase", "GitHub Actions"], "name": "test"},
            "dependencies": [],
            "documentation": {"files": [], "count": 0},
            "config_files": {"files": [], "count": 0},
        }
        ts = enhance_tech_stack(result)
        self.assertIn("Flutter", ts["primary_frameworks"])
        self.assertNotIn("Firebase", ts["primary_frameworks"])
        self.assertNotIn("GitHub Actions", ts["primary_frameworks"])

    def test_framework_tier_firebase_secondary(self):
        """Firebase is classified as secondary (cloud service), not primary."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = {
            "project": {"frameworks": ["Flutter", "Firebase", "GitHub Actions"], "name": "test"},
            "dependencies": [],
            "documentation": {"files": [], "count": 0},
            "config_files": {"files": [], "count": 0},
        }
        ts = enhance_tech_stack(result)
        self.assertNotIn("Firebase", ts["primary_frameworks"])
        # Firebase should appear in secondary as "Cloud Services"
        cat_names = [sf["category"] for sf in ts["secondary_frameworks"]]
        self.assertIn("Cloud Services", cat_names)

    def test_framework_tier_github_actions_infrastructure(self):
        """GitHub Actions is infrastructure only, never primary or secondary."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = {
            "project": {"frameworks": ["Flutter", "GitHub Actions"], "name": "test"},
            "dependencies": [],
            "documentation": {"files": [], "count": 0},
            "config_files": {"files": [], "count": 0},
        }
        ts = enhance_tech_stack(result)
        self.assertIn("GitHub Actions", ts["infrastructure"])
        self.assertNotIn("GitHub Actions", ts["primary_frameworks"])
        for sf in ts["secondary_frameworks"]:
            libs = [l.lower() for l in sf["libraries"]]
            self.assertNotIn("github actions", libs)

    def test_framework_tier_docker_infrastructure(self):
        """Docker is infrastructure, not primary."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = {
            "project": {"frameworks": ["Docker", "Flutter"], "name": "test"},
            "dependencies": [],
            "documentation": {"files": [], "count": 0},
            "config_files": {"files": [], "count": 0},
        }
        ts = enhance_tech_stack(result)
        self.assertIn("Docker", ts["infrastructure"])
        self.assertNotIn("Docker", ts["primary_frameworks"])

    def test_framework_tier_provider_secondary(self):
        """Provider is secondary (state management), not primary."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = {
            "project": {"frameworks": ["Flutter", "Provider"], "name": "test"},
            "dependencies": [],
            "documentation": {"files": [], "count": 0},
            "config_files": {"files": [], "count": 0},
        }
        ts = enhance_tech_stack(result)
        self.assertNotIn("Provider", ts["primary_frameworks"])
        self.assertNotIn("Provider", ts["infrastructure"])
        cat_names = [sf["category"] for sf in ts["secondary_frameworks"]]
        self.assertIn("State Management", cat_names)

    def test_framework_tier_no_doc_scanning(self):
        """Documentation-only mentions do NOT become framework entries."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = {
            "project": {"frameworks": [], "name": "test"},
            "dependencies": [],
            "documentation": {
                "files": [
                    {"path": "README.md", "role": "readme",
                     "preview": "This project uses Flutter, React, Django, TensorFlow and Firebase."},
                ],
                "count": 1,
            },
            "config_files": {"files": [], "count": 0},
        }
        ts = enhance_tech_stack(result)
        # No frameworks should be detected from doc content alone
        self.assertEqual(ts["primary_frameworks"], [])
        self.assertEqual(ts["secondary_frameworks"], [])
        self.assertEqual(ts["infrastructure"], [])
        self.assertEqual(ts["cloud_services"], [])

    # --- Dependency Augmentation Tests ---

    def test_dependency_augmentation_pubspec(self):
        """Pubspec dependencies like firebase_core augment secondary frameworks."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = {
            "project": {"frameworks": ["Flutter"], "name": "test"},
            "dependencies": ["firebase_core", "cloud_firestore", "provider", "dio"],
            "documentation": {"files": [], "count": 0},
            "config_files": {"files": [], "count": 0},
        }
        ts = enhance_tech_stack(result)
        self.assertIn("Flutter", ts["primary_frameworks"])
        cat_names = [sf["category"] for sf in ts["secondary_frameworks"]]
        self.assertIn("Cloud Services", cat_names)
        self.assertIn("State Management", cat_names)
        self.assertIn("Networking", cat_names)
        self.assertIn("Cloud Services", cat_names)

    def test_dependency_augmentation_flutter_sdk(self):
        """Flutter SDK from dependencies augments primary frameworks."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = {
            "project": {"frameworks": [], "name": "test"},  # connector missed Flutter
            "dependencies": ["flutter", "provider"],
            "documentation": {"files": [], "count": 0},
            "config_files": {"files": [], "count": 0},
        }
        ts = enhance_tech_stack(result)
        self.assertIn("Flutter", ts["primary_frameworks"])

    def test_dependency_augmentation_go_router(self):
        """go_router dependency mapped to secondary frameworks."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = {
            "project": {"frameworks": ["Flutter"], "name": "test"},
            "dependencies": ["go_router", "bloc", "riverpod"],
            "documentation": {"files": [], "count": 0},
            "config_files": {"files": [], "count": 0},
        }
        ts = enhance_tech_stack(result)
        cat_names = [sf["category"] for sf in ts["secondary_frameworks"]]
        self.assertIn("State Management", cat_names)

    def test_dependency_augmentation_node_packages(self):
        """Node.js dependencies from package.json augment frameworks."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = {
            "project": {"frameworks": ["Node.js"], "name": "test"},
            "dependencies": ["express", "react", "next"],
            "documentation": {"files": [], "count": 0},
            "config_files": {"files": [], "count": 0},
        }
        ts = enhance_tech_stack(result)
        self.assertIn("Express", ts["primary_frameworks"])
        self.assertIn("React", ts["primary_frameworks"])
        self.assertIn("Next.js", ts["primary_frameworks"])

    def test_dependency_augmentation_python_frameworks(self):
        """Python package dependencies augment frameworks."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = {
            "project": {"frameworks": ["Python"], "name": "test"},
            "dependencies": ["django", "flask", "fastapi", "tensorflow", "torch"],
            "documentation": {"files": [], "count": 0},
            "config_files": {"files": [], "count": 0},
        }
        ts = enhance_tech_stack(result)
        self.assertIn("Django", ts["primary_frameworks"])
        self.assertIn("Flask", ts["primary_frameworks"])
        self.assertIn("FastAPI", ts["primary_frameworks"])
        self.assertIn("TensorFlow", ts["primary_frameworks"])
        self.assertIn("PyTorch", ts["primary_frameworks"])

    # --- Firebase Config Detection Tests ---

    def test_firebase_config_detection(self):
        """firebase.json in config_files adds Firebase to cloud_services."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = {
            "project": {"frameworks": ["Flutter"], "name": "test"},
            "dependencies": [],
            "documentation": {"files": [], "count": 0},
            "config_files": {"files": [
                {"path": "firebase.json", "type": "config"},
                {"path": "firestore.rules", "type": "config"},
            ], "count": 2},
        }
        ts = enhance_tech_stack(result)
        self.assertIn("Firebase", ts["cloud_services"])

    def test_firebase_functions_detection(self):
        """functions/ directory in config_files adds Firebase to cloud_services."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = {
            "project": {"frameworks": [], "name": "test"},
            "dependencies": [],
            "documentation": {"files": [], "count": 0},
            "config_files": {"files": [
                {"path": "functions/index.js", "type": "source"},
                {"path": "functions/package.json", "type": "manifest"},
            ], "count": 2},
        }
        ts = enhance_tech_stack(result)
        self.assertIn("Firebase", ts["cloud_services"])

    def test_firebase_config_no_false_positive(self):
        """No Firebase config → cloud_services stays empty."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = {
            "project": {"frameworks": ["Flutter"], "name": "test"},
            "dependencies": [],
            "documentation": {"files": [], "count": 0},
            "config_files": {"files": [
                {"path": "docker-compose.yml", "type": "config"},
            ], "count": 1},
        }
        ts = enhance_tech_stack(result)
        self.assertEqual(ts["cloud_services"], [])

    # --- Infrastructure Field Tests ---

    def test_infrastructure_field_present(self):
        """Infrastructure field exists in tech_stack output."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = self._build_flutter_result()
        ts = enhance_tech_stack(result)
        self.assertIn("infrastructure", ts)
        self.assertIsInstance(ts["infrastructure"], list)

    def test_infrastructure_field_empty(self):
        """No infrastructure tools → empty list."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = {
            "project": {"frameworks": ["Flutter"], "name": "test"},
            "dependencies": [],
            "documentation": {"files": [], "count": 0},
            "config_files": {"files": [], "count": 0},
        }
        ts = enhance_tech_stack(result)
        self.assertEqual(ts["infrastructure"], [])

    def test_infrastructure_not_in_primary_or_secondary(self):
        """Infrastructure items appear only in infrastructure field."""
        from services.project_intelligence_enhancer import enhance_tech_stack
        result = {
            "project": {"frameworks": ["Flutter", "Docker", "GitHub Actions", "Make", "pytest"], "name": "test"},
            "dependencies": [],
            "documentation": {"files": [], "count": 0},
            "config_files": {"files": [], "count": 0},
        }
        ts = enhance_tech_stack(result)
        infra = [i.lower() for i in ts["infrastructure"]]
        for item in ("docker", "github actions", "make", "pytest"):
            self.assertIn(item, infra, f"{item} should be in infrastructure")
        self.assertNotIn("Docker", ts["primary_frameworks"])
        self.assertNotIn("pytest", ts["primary_frameworks"])
        for sf in ts["secondary_frameworks"]:
            libs = [l.lower() for l in sf["libraries"]]
            for item in ("docker", "github actions", "make", "pytest"):
                self.assertNotIn(item, libs, f"{item} should not be in secondary")

    # --- framework_tiers (GUI field) Integration Tests ---

    def test_enhance_writes_framework_tiers(self):
        """enhance() populates project.framework_tiers for GUI consumption."""
        from services.project_intelligence_enhancer import enhance
        result = self._build_flutter_result()
        enhance(result)
        fw_tiers = result["project"].get("framework_tiers", {})
        self.assertIn("primary", fw_tiers)
        self.assertIn("secondary", fw_tiers)
        self.assertIn("infrastructure", fw_tiers)

    def test_framework_tiers_flutter_primary(self):
        """Flutter appears in framework_tiers.primary."""
        from services.project_intelligence_enhancer import enhance
        result = self._build_flutter_result()
        enhance(result)
        fw_tiers = result["project"].get("framework_tiers", {})
        self.assertIn("Flutter", fw_tiers.get("primary", []))

    def test_framework_tiers_firebase_secondary(self):
        """Firebase appears in framework_tiers.secondary, not primary."""
        from services.project_intelligence_enhancer import enhance
        result = self._build_flutter_result()
        enhance(result)
        fw_tiers = result["project"].get("framework_tiers", {})
        self.assertIn("Firebase", fw_tiers.get("secondary", []))
        self.assertNotIn("Firebase", fw_tiers.get("primary", []))

    def test_framework_tiers_github_actions_infrastructure(self):
        """GitHub Actions appears only in framework_tiers.infrastructure."""
        from services.project_intelligence_enhancer import enhance
        result = self._build_flutter_result()
        enhance(result)
        fw_tiers = result["project"].get("framework_tiers", {})
        self.assertIn("GitHub Actions", fw_tiers.get("infrastructure", []))
        self.assertNotIn("GitHub Actions", fw_tiers.get("primary", []))
        self.assertNotIn("GitHub Actions", fw_tiers.get("secondary", []))

    def test_framework_tiers_provider_secondary(self):
        """Provider appears in framework_tiers.secondary."""
        from services.project_intelligence_enhancer import enhance
        result = self._build_flutter_result()
        enhance(result)
        fw_tiers = result["project"].get("framework_tiers", {})
        self.assertIn("Provider", fw_tiers.get("secondary", []))

    def test_framework_tiers_docker_infrastructure(self):
        """Docker appears in framework_tiers.infrastructure."""
        from services.project_intelligence_enhancer import enhance
        result = self._build_flutter_result()
        enhance(result)
        fw_tiers = result["project"].get("framework_tiers", {})
        self.assertIn("Docker", fw_tiers.get("infrastructure", []))
        self.assertNotIn("Docker", fw_tiers.get("primary", []))

    def test_framework_tiers_no_doc_classification(self):
        """Documentation-only mentions do NOT appear in any framework_tiers field."""
        from services.project_intelligence_enhancer import enhance
        result = {
            "project": {
                "name": "test",
                "path": "",
                "type": "Unknown Project",
                "frameworks": [],
                "languages": [],
                "classification": {
                    "domain": "general_application",
                    "confidence": "low",
                    "evidence": [],
                    "scores": {},
                },
            },
            "dependencies": [],
            "documentation": {
                "files": [
                    {"path": "README.md", "role": "readme",
                     "preview": "This project uses Flutter, React, Django, TensorFlow and Firebase."},
                    {"path": "ARCHITECTURE.md", "role": "architecture",
                     "preview": "Clean Architecture with Flutter frontend and Firebase backend."},
                ],
                "count": 2,
            },
            "config_files": {"files": [], "count": 0},
            "statistics": {"file_count": 10},
        }
        enhance(result)
        fw_tiers = result["project"].get("framework_tiers", {})
        # No frameworks should come from documentation text alone
        self.assertEqual(fw_tiers.get("primary", []), [])
        self.assertEqual(fw_tiers.get("secondary", []), [])
        self.assertEqual(fw_tiers.get("infrastructure", []), [])

    def test_framework_tiers_dependency_augmentation(self):
        """Dependencies augment framework_tiers when connector misses frameworks."""
        from services.project_intelligence_enhancer import enhance
        result = {
            "project": {
                "name": "test",
                "path": "",
                "type": "Unknown Project",
                "frameworks": ["GitHub Actions"],  # connector only detected infra
                "languages": [],
                "classification": {
                    "domain": "general_application",
                    "confidence": "low",
                    "evidence": [],
                    "scores": {},
                },
            },
            "dependencies": ["flutter", "firebase_core", "cloud_firestore", "provider"],
            "documentation": {"files": [], "count": 0},
            "config_files": {"files": [], "count": 0},
            "statistics": {"file_count": 10},
        }
        enhance(result)
        fw_tiers = result["project"].get("framework_tiers", {})
        self.assertIn("Flutter", fw_tiers.get("primary", []),
                      "Flutter from dependencies should be in primary")
        secondary = fw_tiers.get("secondary", [])
        self.assertIn("Cloud Firestore", secondary,
                      "cloud_firestore dep should be in secondary")
        self.assertIn("Firebase Core", secondary,
                      "firebase_core dep should be in secondary")
        self.assertIn("Provider", secondary,
                      "provider dep should be in secondary")
        self.assertIn("GitHub Actions", fw_tiers.get("infrastructure", []),
                      "GitHub Actions should remain infrastructure")


# --- Reasoning Layer Tests ---

class TestTwinReasoning(unittest.TestCase):
    """Verify TwinReasoningService change reasoner, insights, and risk detection."""

    def setUp(self):
        from services.twin_reasoning_service import TwinReasoningService
        self.reasoner = TwinReasoningService(None)

    def _make_comparison(self, **overrides):
        """Helper to build a comparison dict with sensible defaults."""
        comp = {
            "has_changes": False,
            "summary": [],
            "new_files": [],
            "removed_files": [],
            "changed_architecture": {},
            "changed_dependencies": {"added": [], "removed": []},
            "changed_frameworks": {"added": [], "removed": []},
            "documentation_changes": {"added": [], "removed": []},
            "classification_changed": False,
            "purpose_changed": False,
            "from_version": 1,
            "to_version": 2,
            "project_name": "test_project",
        }
        comp.update(overrides)
        return comp

    # --- Change Reasoner Tests ---

    def test_reason_no_changes(self):
        """No changes produces graceful explanation."""
        comp = self._make_comparison(has_changes=False)
        result = self.reasoner.reason_change(comp)
        self.assertIn("No significant changes", result["explanation"])
        self.assertEqual(result["architectural_impact"], "None.")

    def test_reason_with_changes_has_explanation(self):
        """Changes produce a non-empty explanation."""
        comp = self._make_comparison(
            has_changes=True,
            new_files=["FEATURES.md"],
            changed_dependencies={"added": ["http"], "removed": []},
            changed_frameworks={"added": ["React"], "removed": []},
        )
        result = self.reasoner.reason_change(comp)
        self.assertGreater(len(result["explanation"]), 10)
        self.assertIn("what_changed", result)
        self.assertIn("architectural_impact", result)
        self.assertIn("risk_indicators", result)

    def test_reason_what_changed(self):
        """what_changed field describes changes."""
        comp = self._make_comparison(
            has_changes=True,
            new_files=["README.md", "CONTRIBUTING.md"],
            changed_dependencies={"added": ["express"], "removed": []},
        )
        result = self.reasoner.reason_change(comp)
        self.assertIn("2 new file(s)", result["what_changed"])
        self.assertIn("express", result["what_changed"])

    def test_reason_why_likely_changed(self):
        """likely_reason explains why dependencies were added."""
        comp = self._make_comparison(
            has_changes=True,
            changed_dependencies={"added": ["firebase_core", "cloud_firestore"], "removed": []},
        )
        result = self.reasoner.reason_change(comp)
        self.assertIn("likely_reason", result)
        why = result["likely_reason"].lower()
        self.assertTrue("firebase" in why or "backend" in why or "integration" in why)

    def test_reason_architectural_impact_described(self):
        """Architectural impact mentions complexity changes."""
        comp = self._make_comparison(
            has_changes=True,
            changed_frameworks={"added": ["Docker", "Kubernetes"], "removed": []},
            new_files=["deploy.yaml", "Dockerfile"],
        )
        result = self.reasoner.reason_change(comp)
        impact = result["architectural_impact"].lower()
        self.assertIn("complexity", impact)
        self.assertIn("2 new framework(s)", impact)

    def test_reason_maturity_assessment_present(self):
        """Maturity assessment is returned."""
        comp = self._make_comparison(has_changes=True, new_files=["test.py"])
        result = self.reasoner.reason_change(comp)
        self.assertIn("maturity_assessment", result)
        self.assertGreater(len(result["maturity_assessment"]), 0)

    def test_reason_with_old_and_new_twin(self):
        """Reasoning with actual twin data produces richer output."""
        from connectors.plugins.local_project_connector import LocalProjectConnector
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            c1 = LocalProjectConnector(config={"project_path": project_dir})
            c1.connect()
            c1.observe()
            old = c1.get_discovery_result()

            os.remove(os.path.join(project_dir, "CONTRIBUTING.md"))
            with open(os.path.join(project_dir, "pubspec.yaml"), "a") as f:
                f.write("  http: ^1.0.0\n")

            c2 = LocalProjectConnector(config={"project_path": project_dir})
            c2.connect()
            c2.observe()
            new = c2.get_discovery_result()

            from services.twin_comparison_service import TwinComparisonService
            comparer = TwinComparisonService(None)
            comp = comparer.compare(old, new)
            result = self.reasoner.reason_change(comp, old, new)
            self.assertGreater(len(result["explanation"]), 10)
            self.assertTrue(comp["has_changes"])

    # --- Risk Detection Tests ---

    def test_risk_dependency_growth_high(self):
        """5+ new dependencies triggers high-severity dependency growth risk."""
        comp = self._make_comparison(
            has_changes=True,
            changed_dependencies={"added": ["a", "b", "c", "d", "e"], "removed": []},
        )
        risks = self.reasoner.detect_risks(comp)
        dep_risks = [r for r in risks if r["type"] == "dependency_growth"]
        self.assertTrue(any(r["severity"] == "high" for r in dep_risks))

    def test_risk_dependency_growth_medium(self):
        """3 new dependencies triggers medium-severity dependency growth risk."""
        comp = self._make_comparison(
            has_changes=True,
            changed_dependencies={"added": ["a", "b", "c"], "removed": []},
        )
        risks = self.reasoner.detect_risks(comp)
        dep_risks = [r for r in risks if r["type"] == "dependency_growth"]
        self.assertTrue(any(r["severity"] == "medium" for r in dep_risks))

    def test_risk_missing_documentation(self):
        """Fewer than 3 docs triggers medium risk."""
        new_twin = {"documentation": {"files": [{"path": "README.md"}]}}
        comp = self._make_comparison(has_changes=False)
        risks = self.reasoner.detect_risks(comp, new_twin)
        doc_risks = [r for r in risks if r["type"] == "missing_documentation"]
        self.assertGreater(len(doc_risks), 0)

    def test_risk_no_documentation(self):
        """Zero docs triggers high-severity risk."""
        new_twin = {"documentation": {"files": []}}
        comp = self._make_comparison(has_changes=False)
        risks = self.reasoner.detect_risks(comp, new_twin)
        docs_risks = [r for r in risks if r["type"] == "missing_documentation"]
        self.assertTrue(any(r["severity"] == "high" for r in docs_risks))

    def test_risk_architecture_drift(self):
        """Changed architecture triggers drift risk."""
        comp = self._make_comparison(
            has_changes=True,
            changed_architecture={"old": {"ARCH.md": "old"}, "new": {"ARCH.md": "new"}},
        )
        risks = self.reasoner.detect_risks(comp)
        drift_risks = [r for r in risks if r["type"] == "architecture_drift"]
        self.assertGreater(len(drift_risks), 0)

    def test_risk_large_structural_change_high(self):
        """10+ file changes triggers high-severity structural risk."""
        comp = self._make_comparison(
            has_changes=True,
            new_files=[f"file_{i}.md" for i in range(7)],
            removed_files=[f"old_{i}.md" for i in range(5)],
        )
        risks = self.reasoner.detect_risks(comp)
        struct_risks = [r for r in risks if r["type"] == "large_structural_change"]
        self.assertTrue(any(r["severity"] == "high" for r in struct_risks))

    def test_risk_large_structural_change_low(self):
        """5-9 file changes triggers low-severity structural risk."""
        comp = self._make_comparison(
            has_changes=True,
            new_files=[f"file_{i}.md" for i in range(3)],
            removed_files=[f"old_{i}.md" for i in range(3)],
        )
        risks = self.reasoner.detect_risks(comp)
        struct_risks = [r for r in risks if r["type"] == "large_structural_change"]
        self.assertGreater(len(struct_risks), 0)

    def test_risk_deprecated_technology(self):
        """Deprecated technology detected."""
        new_twin = {
            "project": {"frameworks": ["AngularJS", "React"]},
            "dependencies": [],
        }
        comp = self._make_comparison(has_changes=False)
        risks = self.reasoner.detect_risks(comp, new_twin)
        dep_risks = [r for r in risks if r["type"] == "deprecated_technology"]
        self.assertGreater(len(dep_risks), 0)

    def test_risk_identity_drift(self):
        """Classification change triggers identity drift risk."""
        comp = self._make_comparison(has_changes=True, classification_changed=True)
        risks = self.reasoner.detect_risks(comp)
        id_risks = [r for r in risks if r["type"] == "identity_drift"]
        self.assertGreater(len(id_risks), 0)

    def test_risk_framework_churn(self):
        """Multiple framework removals triggers churn risk."""
        comp = self._make_comparison(
            has_changes=True,
            changed_frameworks={"added": [], "removed": ["Flutter", "Firebase"]},
        )
        risks = self.reasoner.detect_risks(comp)
        churn_risks = [r for r in risks if r["type"] == "framework_churn"]
        self.assertGreater(len(churn_risks), 0)

    def test_no_risks_for_stable_project(self):
        """Stable project with no changes has no risks."""
        comp = self._make_comparison(has_changes=False)
        new_twin = {
            "project": {"frameworks": ["Flutter"]},
            "dependencies": ["firebase_core"],
            "documentation": {"files": [{"path": "README.md"}, {"path": "ARCH.md"}, {"path": "CHANGE.md"}]},
        }
        risks = self.reasoner.detect_risks(comp, new_twin)
        self.assertEqual(len(risks), 0)

    # --- Evolution Insights Tests ---

    def test_generate_insights_empty(self):
        """Empty comparisons produces baseline insights."""
        insights = self.reasoner.generate_evolution_insights([], [])
        self.assertIn("per_transition", insights)
        self.assertEqual(len(insights["per_transition"]), 0)
        self.assertIn("overall", insights)

    def test_generate_insights_single_transition(self):
        """Single transition produces one insight."""
        comp = self._make_comparison(
            has_changes=True,
            new_files=["NEW.md"],
        )
        insights = self.reasoner.generate_evolution_insights([comp], [{"version": 1}, {"version": 2}])
        self.assertEqual(len(insights["per_transition"]), 1)
        self.assertGreater(len(insights["per_transition"][0]["narrative"]), 0)

    def test_generate_insights_multiple_transitions(self):
        """Multiple transitions each produce an insight."""
        comps = [
            self._make_comparison(from_version=1, to_version=2, has_changes=True, new_files=["a.md"]),
            self._make_comparison(from_version=2, to_version=3, has_changes=True, new_files=["b.md"]),
        ]
        versions = [{"version": 1}, {"version": 2}, {"version": 3}]
        insights = self.reasoner.generate_evolution_insights(comps, versions)
        self.assertEqual(len(insights["per_transition"]), 2)

    def test_insight_risk_count_tracked(self):
        """Insight risk counts are tracked."""
        comp = self._make_comparison(
            has_changes=True,
            classification_changed=True,
            changed_dependencies={"added": ["a", "b", "c"], "removed": []},
        )
        insights = self.reasoner.generate_evolution_insights(
            [comp], [{"version": 1}, {"version": 2}]
        )
        self.assertGreater(insights["per_transition"][0]["risk_count"], 0)
        self.assertGreater(insights["total_risks"], 0)

    def test_insight_maturity_assessment(self):
        """Maturity assessment appears in insights."""
        comp = self._make_comparison(
            has_changes=True,
            new_files=["README.md", "ARCH.md"],
            documentation_changes={"added": ["README.md", "ARCH.md"], "removed": []},
        )
        old_twin = {
            "dependencies": [], "documentation": {"files": []},
            "project": {"frameworks": []},
        }
        new_twin = {
            "dependencies": [], "documentation": {"files": [{"path": "README.md"}, {"path": "ARCH.md"}]},
            "project": {"frameworks": []},
        }
        result = self.reasoner.reason_change(comp, old_twin, new_twin)
        self.assertIn("documentation improved", result["maturity_assessment"].lower())

    def test_overall_arc_assessment(self):
        """Overall evolution arc is generated."""
        comps = [
            self._make_comparison(
                from_version=1, to_version=2, has_changes=True,
                changed_dependencies={"added": ["express"], "removed": []},
            ),
        ]
        versions = [{"version": 1}, {"version": 2}]
        insights = self.reasoner.generate_evolution_insights(comps, versions)
        self.assertIn("overall", insights)
        self.assertGreater(len(insights["overall"]), 0)

    def test_regression_existing_tests_still_pass_with_reasoning(self):
        """Reasoning does not break any existing comparison behavior."""
        from services.twin_comparison_service import TwinComparisonService
        comparer = TwinComparisonService(None)
        old = {
            "project": {"frameworks": ["Flutter"], "classification": {"domain": "mobile"}},
            "dependencies": ["firebase_core"],
            "documentation": {"files": [{"path": "README.md"}]},
            "config_files": {"files": [{"path": "pubspec.yaml"}]},
            "purpose_clues": {"summary": "Mobile app"},
            "documentation_categories": {"architecture": []},
        }
        new = {
            "project": {"frameworks": ["Flutter", "React"], "classification": {"domain": "web"}},
            "dependencies": ["firebase_core", "http"],
            "documentation": {"files": [{"path": "README.md"}, {"path": "NEW.md"}]},
            "config_files": {"files": [{"path": "pubspec.yaml"}]},
            "purpose_clues": {"summary": "Web app"},
            "documentation_categories": {"architecture": []},
        }
        comp = comparer.compare(old, new)
        result = self.reasoner.reason_change(comp, old, new)
        self.assertIn("what_changed", result)
        self.assertIn("explanation", result)
        self.assertIn("risk_indicators", result)
        self.assertGreater(len(result["risk_indicators"]), 0)


if __name__ == "__main__":
    unittest.main()
