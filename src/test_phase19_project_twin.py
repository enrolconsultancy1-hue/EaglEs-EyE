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
    os.makedirs(os.path.join(project_dir, ".git"))  # Git repo indicator

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

    # lib/main.dart
    with open(os.path.join(project_dir, "lib", "main.dart"), "w") as f:
        f.write("import 'package:flutter/material.dart';\n")
        f.write("void main() => runApp(App());\n")

    # Additional Dart files
    with open(os.path.join(project_dir, "lib", "app.dart"), "w") as f:
        f.write("class App extends StatelessWidget {}\n")

    # test files
    with open(os.path.join(project_dir, "test", "widget_test.dart"), "w") as f:
        f.write("void main() {}\n")

    # Some other files
    with open(os.path.join(project_dir, "README.md"), "w") as f:
        f.write("# Eagle's Property\n")
    with open(os.path.join(project_dir, ".gitignore"), "w") as f:
        f.write("*.dart_tool\n")
    with open(os.path.join(project_dir, "analysis_options.yaml"), "w") as f:
        f.write("include: package:flutter_lints/flutter.yaml\n")

    return project_dir


def create_python_project(temp_dir):
    """Create a Python project structure for testing."""
    project_dir = os.path.join(temp_dir, "py_project")
    os.makedirs(project_dir)
    os.makedirs(os.path.join(project_dir, "src"))
    os.makedirs(os.path.join(project_dir, "tests"))

    # setup.py
    with open(os.path.join(project_dir, "setup.py"), "w") as f:
        f.write("from setuptools import setup\nsetup(name='py_project')\n")

    # Python files in src
    with open(os.path.join(project_dir, "src", "main.py"), "w") as f:
        f.write("print('hello')\n")
    with open(os.path.join(project_dir, "src", "utils.py"), "w") as f:
        f.write("def helper(): pass\n")

    # requirements.txt
    with open(os.path.join(project_dir, "requirements.txt"), "w") as f:
        f.write("flask==2.0.0\nrequests==2.28.0\n")

    return project_dir


def create_node_project(temp_dir):
    """Create a Node.js project with package.json."""
    project_dir = os.path.join(temp_dir, "node_app")
    os.makedirs(project_dir)
    os.makedirs(os.path.join(project_dir, ".git"))

    with open(os.path.join(project_dir, "package.json"), "w") as f:
        json.dump({
            "name": "node_app",
            "dependencies": {"express": "^4.0.0", "firebase": "^9.0.0"},
            "devDependencies": {"jest": "^29.0.0"},
        }, f)

    with open(os.path.join(project_dir, "index.js"), "w") as f:
        f.write("const express = require('express');\n")

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
            self.assertEqual(result["discovery"]["project"]["type"], "Flutter Application")
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


if __name__ == "__main__":
    unittest.main()
