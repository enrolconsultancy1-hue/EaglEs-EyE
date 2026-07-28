"""Code Intelligence Service — Phase 8 tests.

Tests language detection, source scanning, code graph creation,
code query, MCP registration, and GUI integration.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock


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


def write_sample_project(tmpdir):
    """Write sample source files into tmpdir for testing."""
    # Python file
    py_dir = os.path.join(tmpdir, "src")
    os.makedirs(py_dir)
    with open(os.path.join(py_dir, "main.py"), "w") as f:
        f.write("""
import os
import sys
from services.service import Service

class App:
    def run(self):
        pass

class Config:
    def load(self):
        pass

def startup():
    app = App()
    app.run()
""")
    with open(os.path.join(py_dir, "auth_service.py"), "w") as f:
        f.write("""
import hashlib
from models.user import User

class AuthService:
    def authenticate(self, username, password):
        pass

    def logout(self):
        pass
""")
    with open(os.path.join(py_dir, "user_repository.py"), "w") as f:
        f.write("""
from database.connection import DatabaseConnection

class UserRepository:
    def find_by_id(self, user_id):
        pass

    def save(self, user):
        pass
""")
    # JavaScript file
    with open(os.path.join(tmpdir, "app.js"), "w") as f:
        f.write("""
import React from 'react';
import { useState } from 'react';

class AppComponent {
    render() {
        return null;
    }
}

function helper() {
    return 'help';
}

const greeting = (name) => {
    return 'Hello ' + name;
};
""")
    # TypeScript file
    ts_dir = os.path.join(tmpdir, "ts_src")
    os.makedirs(ts_dir)
    with open(os.path.join(ts_dir, "controller.ts"), "w") as f:
        f.write("""
import { Request, Response } from 'express';
import { UserService } from './user_service';

class UserController {
    handleGet(req: Request, res: Response): void {
        res.send('ok');
    }
}

function parseQuery(): string {
    return '';
}
""")
    # Dart file
    dart_dir = os.path.join(tmpdir, "lib")
    os.makedirs(dart_dir)
    with open(os.path.join(dart_dir, "main.dart"), "w") as f:
        f.write("""
import 'package:flutter/material.dart';
import 'src/app.dart';

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(home: Text('Hello'));
  }
}

void main() {
  runApp(MyApp());
}
""")
    # Java file
    java_dir = os.path.join(tmpdir, "java_src")
    os.makedirs(java_dir)
    with open(os.path.join(java_dir, "UserController.java"), "w") as f:
        f.write("""
import java.util.List;
import org.springframework.web.bind.annotation.*;

public class UserController {
    public List<String> getUsers() {
        return null;
    }
}
""")
    # Go file
    go_dir = os.path.join(tmpdir, "go_src")
    os.makedirs(go_dir)
    with open(os.path.join(go_dir, "server.go"), "w") as f:
        f.write("""
package main

import "fmt"

func main() {
    fmt.Println("Hello")
}

type Server struct {
    port int
}

func (s *Server) Start() {
}
""")
    # C# file
    cs_dir = os.path.join(tmpdir, "cs_src")
    os.makedirs(cs_dir)
    with open(os.path.join(cs_dir, "Handler.cs"), "w") as f:
        f.write("""
using System;
using System.Collections.Generic;

public class RequestHandler {
    public string Handle(string input) {
        return input;
    }
}
""")
    return tmpdir


class TestCodeIntelligenceService(unittest.TestCase):

    def setUp(self):
        self.kernel = FakeKernel()

    def _make_service(self):
        from services.code_intelligence_service import CodeIntelligenceService
        svc = CodeIntelligenceService(self.kernel)
        svc.start()
        return svc

    # --- 1. Language Detection ---

    def test_language_detection(self):
        """Detect Python, JavaScript, TypeScript, Dart, Java, Go, C# files."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            langs = svc.detect_languages(tmp)
            self.assertGreater(len(langs), 0)
            names = [l["name"] for l in langs]
            self.assertIn("Python", names)
            self.assertIn("JavaScript", names)
            self.assertIn("TypeScript", names)
            self.assertIn("Dart", names)
            self.assertIn("Java", names)
            self.assertIn("Go", names)
            self.assertIn("C#", names)

    def test_language_percentages_sum(self):
        """Language percentages sum to ~100%."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            langs = svc.detect_languages(tmp)
            total = sum(l["percentage"] for l in langs)
            self.assertAlmostEqual(total, 100.0, delta=1.0)

    def test_language_empty_project(self):
        """Empty project returns empty language list."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            langs = svc.detect_languages(tmp)
            self.assertEqual(langs, [])

    # --- 2. Python Class Detection ---

    def test_python_class_detection(self):
        """Python classes are correctly extracted."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            scan = svc.scan_sources(tmp)
            classes = [c["name"] for c in scan["all_classes"]]
            self.assertIn("App", classes)
            self.assertIn("Config", classes)
            self.assertIn("AuthService", classes)
            self.assertIn("UserRepository", classes)

    def test_python_function_detection(self):
        """Python functions are correctly extracted."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            scan = svc.scan_sources(tmp)
            fns = [c["name"] for c in scan["all_functions"]]
            self.assertIn("startup", fns)
            self.assertIn("run", fns)
            self.assertIn("load", fns)
            self.assertIn("authenticate", fns)
            self.assertIn("logout", fns)

    def test_function_detection_multi_language(self):
        """Functions are detected across Python, JS, TS, Dart, Java, Go, C#."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            scan = svc.scan_sources(tmp)
            fns = [c["name"] for c in scan["all_functions"]]
            # Python
            self.assertIn("startup", fns)
            # JS
            self.assertIn("helper", fns)
            # TS
            self.assertIn("parseQuery", fns)
            # Java
            self.assertIn("getUsers", fns)
            # Go
            self.assertIn("main", fns)
            self.assertIn("Start", fns)
            # Dart
            self.assertIn("main", fns)  # Dart main function
            # C#
            self.assertIn("Handle", fns)

    def test_dependency_detection(self):
        """Python imports are correctly extracted."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            scan = svc.scan_sources(tmp)
            imports = [i["source"] for i in scan["all_imports"]]
            self.assertIn("os", imports)
            self.assertIn("sys", imports)
            self.assertIn("hashlib", imports)
            # 'from X import' produces X
            self.assertIn("services.service", imports)
            self.assertIn("models.user", imports)
            self.assertIn("database.connection", imports)

    # --- 3. Code Graph ---

    def test_code_graph_creation(self):
        """Code knowledge graph has nodes and edges."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            scan = svc.scan_sources(tmp)
            graph = svc.build_code_graph(scan)
            self.assertIn("nodes", graph)
            self.assertIn("edges", graph)
            self.assertGreater(len(graph["nodes"]), 0)
            self.assertGreater(len(graph["edges"]), 0)
            class_nodes = [n for n in graph["nodes"] if n["type"] == "class"]
            self.assertGreater(len(class_nodes), 0)

    def test_code_graph_has_import_edges(self):
        """Code graph contains import edges between modules."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            scan = svc.scan_sources(tmp)
            graph = svc.build_code_graph(scan)
            import_edges = [e for e in graph["edges"] if e["relation"] == "imports"]
            self.assertGreater(len(import_edges), 0)

    # --- 4. Architecture Detection ---

    def test_architecture_layer_detection(self):
        """Architecture layers detected from naming patterns."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            scan = svc.scan_sources(tmp)
            layers = svc.analyze_code_architecture(scan)
            layer_names = [l["layer"] for l in layers]
            self.assertIn("Service Layer", layer_names)
            self.assertIn("Repository Layer", layer_names)
            self.assertIn("Controller Layer", layer_names)
            self.assertIn("Handler Layer", layer_names)

    # --- 5. Full Analysis ---

    def test_full_analysis(self):
        """analyze_project returns all expected fields."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            result = svc.analyze_project(tmp)
            self.assertIn("languages", result)
            self.assertIn("components", result)
            self.assertIn("architecture_layers", result)
            self.assertIn("complexity", result)
            self.assertIn("entry_points", result)
            self.assertIn("important_files", result)
            self.assertIn("code_graph", result)
            self.assertGreater(len(result["languages"]), 0)

    def test_full_analysis_invalid_path(self):
        """analyze_project with invalid path returns error."""
        svc = self._make_service()
        result = svc.analyze_project("/nonexistent/path")
        self.assertIn("error", result)

    def test_entry_points_detected(self):
        """Entry points like main.py are detected."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            result = svc.analyze_project(tmp)
            self.assertGreater(len(result["entry_points"]), 0)
            self.assertTrue(any("main.py" in e for e in result["entry_points"]))

    # --- 6. Code Query ---

    def test_code_query_classes(self):
        """Query for classes returns class information."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            svc.analyze_project(tmp)
            ans = svc.code_query("What classes exist?")
            self.assertIn("answer", ans)
            self.assertIn("AuthService", ans["answer"])
            self.assertIn("UserRepository", ans["answer"])

    def test_code_query_functions(self):
        """Query for functions returns function information."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            svc.analyze_project(tmp)
            ans = svc.code_query("What functions exist?")
            self.assertIn("answer", ans)
            self.assertIn("startup", ans["answer"])

    def test_code_query_languages(self):
        """Query for languages returns language information."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            svc.analyze_project(tmp)
            ans = svc.code_query("What languages are used?")
            self.assertIn("answer", ans)
            self.assertIn("Python", ans["answer"])

    def test_code_query_imports(self):
        """Query for imports returns dependency information."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            svc.analyze_project(tmp)
            ans = svc.code_query("Show dependencies")
            self.assertIn("answer", ans)
            self.assertIn("import", ans["answer"].lower())

    def test_code_query_architecture(self):
        """Query for architecture layers returns layer information."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            svc.analyze_project(tmp)
            ans = svc.code_query("What architecture layers")
            self.assertIn("Service Layer", ans["answer"])

    def test_code_query_entry_points(self):
        """Query for entry points returns entry point info."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            svc.analyze_project(tmp)
            ans = svc.code_query("What are entry points")
            self.assertIn("answer", ans)
            self.assertIn("main.py", ans["answer"])

    def test_code_query_complexity(self):
        """Query for complexity returns complexity info."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            svc.analyze_project(tmp)
            ans = svc.code_query("What is the complexity")
            self.assertIn("answer", ans)
            self.assertIn("low", ans["answer"].lower())

    def test_code_query_overview(self):
        """Query for overview returns comprehensive info."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            svc.analyze_project(tmp)
            ans = svc.code_query("Explain the code")
            self.assertIn("answer", ans)
            self.assertIn("Code Intelligence", ans["answer"])

    def test_code_query_no_analysis(self):
        """Query without analysis returns helpful message."""
        svc = self._make_service()
        ans = svc.code_query("What classes")
        self.assertIn("No project analyzed", ans["answer"])

    def test_code_query_search(self):
        """Query with keyword search finds relevant code."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            svc.analyze_project(tmp)
            ans = svc.code_query("Where is auth implemented")
            self.assertIn("answer", ans)
            self.assertIn("auth", ans["answer"].lower())

    # --- 7. Code Query Structure ---

    def test_code_query_structure(self):
        """code_query returns answer, evidence, confidence."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            svc.analyze_project(tmp)
            ans = svc.code_query("Overview")
            self.assertIn("answer", ans)
            self.assertIn("evidence", ans)
            self.assertIn("confidence", ans)
            self.assertIsInstance(ans["answer"], str)
            self.assertIsInstance(ans["evidence"], list)
            self.assertIsInstance(ans["confidence"], str)

    def test_code_query_evidence_has_type_source_detail(self):
        """Code query evidence items have type, source, detail."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            svc.analyze_project(tmp)
            ans = svc.code_query("Overview")
            for item in ans["evidence"]:
                self.assertIn("type", item)
                self.assertIn("source", item)
                self.assertIn("detail", item)

    # --- 8. Cache ---

    def test_analysis_cache(self):
        """Analysis results are cached by path."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            r1 = svc.analyze_project(tmp)
            r2 = svc.analyze_project(tmp)
            self.assertIs(r1, r2)  # Same cached object

    def test_clear_cache(self):
        """Cache can be cleared."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            svc.analyze_project(tmp)
            self.assertTrue(svc.has_analysis())
            svc.clear_cache()
            self.assertFalse(svc.has_analysis())

    # --- 9. MCP Registration ---

    def test_mcp_tool_registration_code_intelligence(self):
        """code_intelligence tool is registered in MCPToolService."""
        from services.mcp_tool_service import MCPToolService
        from services.code_intelligence_service import CodeIntelligenceService
        code_intel = CodeIntelligenceService(self.kernel)
        code_intel.start()
        self.kernel._services["CodeIntelligenceService"] = code_intel
        mcp = MCPToolService(self.kernel)
        mcp.start()
        tools = mcp.list_tools()
        tool_names = [t["name"] for t in tools]
        self.assertIn("code_intelligence", tool_names)

    def test_mcp_tool_registration_code_query(self):
        """code_query tool is registered in MCPToolService."""
        from services.mcp_tool_service import MCPToolService
        from services.code_intelligence_service import CodeIntelligenceService
        code_intel = CodeIntelligenceService(self.kernel)
        code_intel.start()
        self.kernel._services["CodeIntelligenceService"] = code_intel
        mcp = MCPToolService(self.kernel)
        mcp.start()
        tools = mcp.list_tools()
        tool_names = [t["name"] for t in tools]
        self.assertIn("code_query", tool_names)

    def test_mcp_code_intelligence_call(self):
        """code_intelligence tool call returns analysis."""
        from services.code_intelligence_service import CodeIntelligenceService
        from services.mcp_tool_service import MCPToolService
        code_intel = CodeIntelligenceService(self.kernel)
        code_intel.start()
        self.kernel._services["CodeIntelligenceService"] = code_intel
        mcp = MCPToolService(self.kernel)
        mcp.start()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            result = mcp.call_tool("code_intelligence", {"project_path": tmp})
            self.assertIn("code_intelligence", result)
            ci = result["code_intelligence"]
            self.assertIn("languages", ci)

    def test_mcp_code_query_call(self):
        """code_query tool call returns answer."""
        from services.code_intelligence_service import CodeIntelligenceService
        from services.mcp_tool_service import MCPToolService
        code_intel = CodeIntelligenceService(self.kernel)
        code_intel.start()
        self.kernel._services["CodeIntelligenceService"] = code_intel
        mcp = MCPToolService(self.kernel)
        mcp.start()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            result = mcp.call_tool("code_query", {"project_path": tmp, "question": "What classes exist?"})
            self.assertIn("answer", result)

    # --- 10. GUI Response Pattern ---

    def test_gui_code_response_structure(self):
        """Code intelligence response matches expected JSON structure for GUI."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            svc.analyze_project(tmp)
            result = svc.code_query("Overview")
            self.assertIsInstance(result.get("answer"), str)
            self.assertIsInstance(result.get("evidence"), list)
            self.assertIsInstance(result.get("confidence"), str)

    def test_gui_full_analysis_structure(self):
        """Full analysis returns structure suitable for GUI cards."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            result = svc.analyze_project(tmp)
            # GUI expects: languages, architecture_layers, important_files, code_graph
            self.assertIsInstance(result.get("languages"), list)
            self.assertIsInstance(result.get("architecture_layers"), list)
            self.assertIsInstance(result.get("important_files"), list)
            self.assertIsInstance(result.get("code_graph"), dict)
            self.assertIn("nodes", result["code_graph"])
            self.assertIn("edges", result["code_graph"])

    def test_gui_evidence_items_have_fields(self):
        """GUI evidence items have expected fields."""
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmp:
            write_sample_project(tmp)
            svc.analyze_project(tmp)
            ans = svc.code_query("Languages")
            for item in ans.get("evidence", []):
                self.assertIn("type", item)
                self.assertIn("source", item)
                self.assertIn("detail", item)

    # --- 11. Cognitive Twin Integration ---

    def test_cognitive_twin_code_summary_dimension(self):
        """Cognitive twin includes code_summary dimension."""
        from services.cognitive_twin_service import CognitiveTwinService
        svc = CognitiveTwinService(self.kernel)
        svc.start()
        # Use minimal twin (no code_intel registered, so code_summary is empty)
        twin_data = {
            "project": {
                "name": "test_proj",
                "type": "Test App",
                "languages": ["Python"],
                "frameworks": [],
                "path": "/tmp/test_proj",
                "classification": {
                    "domain": "general_application",
                    "confidence": "low",
                    "evidence": [],
                    "scores": {},
                },
                "framework_tiers": {},
            },
            "architect_summary": "",
            "purpose_clues": {"summary": "", "clues": [], "details": []},
            "documentation": {"count": 0, "files": []},
            "documentation_categories": {},
            "config_files": {"count": 0, "files": []},
            "dependencies": [],
            "statistics": {"file_count": 0},
            "repository": {"detected": False},
            "tech_stack": {},
            "fingerprint": "test789",
        }
        cognition = svc.load_twin(twin_data)
        self.assertIn("code_summary", cognition)
        self.assertIsInstance(cognition["code_summary"], dict)

    def test_cognitive_twin_code_question(self):
        """Cognitive twin handles code intelligence questions."""
        from services.cognitive_twin_service import CognitiveTwinService
        svc = CognitiveTwinService(self.kernel)
        svc.start()
        twin_data = {
            "project": {
                "name": "test_proj",
                "type": "Test App",
                "languages": ["Python"],
                "frameworks": [],
                "path": "/tmp/test_proj",
                "classification": {
                    "domain": "general_application",
                    "confidence": "low",
                    "evidence": [],
                    "scores": {},
                },
                "framework_tiers": {},
            },
            "architect_summary": "",
            "purpose_clues": {"summary": "", "clues": [], "details": []},
            "documentation": {"count": 0, "files": []},
            "documentation_categories": {},
            "config_files": {"count": 0, "files": []},
            "dependencies": [],
            "statistics": {"file_count": 0},
            "repository": {"detected": False},
            "tech_stack": {},
            "fingerprint": "test789",
        }
        svc.load_twin(twin_data)
        result = svc.ask("code intelligence")
        self.assertIn("answer", result)
        self.assertIn("confidence", result)


if __name__ == "__main__":
    unittest.main()