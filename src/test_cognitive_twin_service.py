"""Cognitive Twin Service — Phase 7 tests.

Tests cognitive summary creation, project question answering,
architecture reasoning, maturity detection, and GUI integration.
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


def make_flutter_twin_data():
    """Create a realistic Flutter project twin dict for testing."""
    return {
        "project": {
            "name": "eagles_property",
            "type": "Flutter Mobile Application",
            "languages": ["Dart", "JavaScript", "YAML"],
            "frameworks": ["Flutter", "Firebase", "Docker", "GitHub Actions", "Provider"],
            "path": "/tmp/eagles_property",
            "classification": {
                "domain": "mobile_application",
                "confidence": "high",
                "evidence": [
                    {"source": "project_type", "signal": "mobile"},
                    {"source": "framework", "signal": "mobile"},
                    {"source": "readme", "signal": "enterprise"},
                ],
                "scores": {"mobile_application": 8, "enterprise_platform": 4, "web_application": 0},
            },
            "framework_tiers": {
                "primary": ["Flutter"],
                "secondary": ["Firebase", "Provider"],
                "infrastructure": ["Docker", "GitHub Actions"],
            },
        },
        "architect_summary": "Eagles Property is a Flutter Mobile Application for property management. It uses Firebase services, containerization (Docker), and the Provider Pattern.",
        "purpose_clues": {
            "summary": "A Flutter-based property management mobile application for real estate agents.",
            "clues": [
                ("readme", "property management mobile application for real estate agents"),
                ("architecture", "Uses BLoC pattern with Firebase backend"),
            ],
            "details": [{"source": "readme", "text": "property management mobile application"}],
        },
        "documentation": {
            "count": 5,
            "summary": "A Flutter-based property management mobile application for real estate agents. Features include property listings, client management, and integrated messaging.",
            "files": [
                {"path": "README.md", "role": "readme", "preview": "A Flutter-based property management mobile application for real estate agents."},
                {"path": "ARCHITECTURE.md", "role": "architecture", "preview": "Uses BLoC pattern with Firebase backend."},
                {"path": "CHANGELOG.md", "role": "changelog", "preview": "## 1.0.0\nInitial release."},
                {"path": "CONTRIBUTING.md", "role": "contributing", "preview": "Please read the guidelines."},
                {"path": "GOAL.md", "role": "goal", "preview": "Build a property management platform."},
            ],
        },
        "documentation_categories": {
            "architecture": [
                {"path": "ARCHITECTURE.md", "preview": "Uses BLoC pattern with Firebase backend."},
            ],
            "product": [
                {"path": "README.md", "preview": "A Flutter-based property management mobile application."},
                {"path": "GOAL.md", "preview": "Build a property management platform."},
            ],
            "build": [
                {"path": "CHANGELOG.md", "preview": "## 1.0.0\nInitial release."},
            ],
        },
        "config_files": {
            "count": 3,
            "ci_types": ["github_actions"],
            "files": [
                {"path": ".github/workflows/ci.yaml", "purpose": "ci"},
                {"path": "Dockerfile", "purpose": "docker"},
                {"path": "analysis_options.yaml", "purpose": "configuration"},
            ],
        },
        "dependencies": ["flutter", "firebase_core", "cloud_firestore", "provider", "firebase_auth"],
        "statistics": {"file_count": 42},
        "repository": {"detected": True, "type": "git"},
        "tech_stack": {
            "primary_frameworks": ["Flutter"],
            "secondary_frameworks": [{"category": "Cloud Services", "libraries": ["Firebase"]}],
            "infrastructure": ["Docker", "GitHub Actions"],
            "cloud_services": ["Firebase"],
            "architecture_patterns": ["BLoC Pattern", "Provider Pattern"],
        },
        "fingerprint": "abc123",
        "twin_version": 1,
        "previous_fingerprint": "",
        "discovery_time": "2026-07-28T00:00:00Z",
        "timestamp": "2026-07-28T00:00:00Z",
        "status": "CONNECTED",
    }


def make_minimal_twin_data():
    """Create a minimal project twin with sparse data."""
    return {
        "project": {
            "name": "minimal_app",
            "type": "Application",
            "languages": ["Python"],
            "frameworks": [],
            "path": "/tmp/minimal_app",
            "classification": {
                "domain": "general_application",
                "confidence": "low",
                "evidence": [],
                "scores": {"general_application": 0},
            },
            "framework_tiers": {
                "primary": [],
                "secondary": [],
                "infrastructure": [],
            },
        },
        "architect_summary": "",
        "purpose_clues": {"summary": "", "clues": [], "details": []},
        "documentation": {"count": 1, "summary": "", "files": []},
        "documentation_categories": {"architecture": [], "product": [], "build": []},
        "config_files": {"count": 0, "ci_types": [], "files": []},
        "dependencies": [],
        "statistics": {"file_count": 3},
        "repository": {"detected": False},
        "tech_stack": {
            "primary_frameworks": [],
            "secondary_frameworks": [],
            "infrastructure": [],
            "cloud_services": [],
            "architecture_patterns": [],
        },
        "fingerprint": "minimal789",
        "twin_version": 1,
        "previous_fingerprint": "",
        "discovery_time": "2026-07-28T00:00:00Z",
        "timestamp": "2026-07-28T00:00:00Z",
        "status": "CONNECTED",
    }


def make_enterprise_twin_data():
    """Create a twin with enterprise domain and deprecated tech signals."""
    return {
        "project": {
            "name": "legacy_enterprise",
            "type": "Enterprise SaaS Platform",
            "languages": ["JavaScript", "HTML", "CSS"],
            "frameworks": ["AngularJS", "jQuery", "Docker"],
            "path": "/tmp/legacy_enterprise",
            "classification": {
                "domain": "enterprise_platform",
                "confidence": "high",
                "evidence": [
                    {"source": "readme", "signal": "enterprise"},
                    {"source": "framework", "signal": "enterprise"},
                ],
                "scores": {"enterprise_platform": 7, "web_application": 3},
            },
            "framework_tiers": {
                "primary": ["AngularJS"],
                "secondary": ["jQuery"],
                "infrastructure": ["Docker"],
            },
        },
        "architect_summary": "Legacy Enterprise is an Enterprise SaaS Platform. It uses Docker.",
        "purpose_clues": {
            "summary": "An enterprise SaaS platform for business management.",
            "clues": [("readme", "enterprise SaaS platform for business management")],
            "details": [{"source": "readme", "text": "enterprise SaaS platform"}],
        },
        "documentation": {
            "count": 2,
            "summary": "An enterprise SaaS platform.",
            "files": [
                {"path": "README.md", "role": "readme", "preview": "An enterprise SaaS platform for business management."},
            ],
        },
        "documentation_categories": {
            "architecture": [],
            "product": [{"path": "README.md", "preview": "An enterprise SaaS platform."}],
            "build": [],
        },
        "config_files": {"count": 0, "ci_types": [], "files": []},
        "dependencies": ["angular", "jquery", "lodash", "express", "moment", "grunt"],
        "statistics": {"file_count": 85},
        "repository": {"detected": True, "type": "git"},
        "tech_stack": {
            "primary_frameworks": ["AngularJS"],
            "secondary_frameworks": [],
            "infrastructure": ["Docker"],
            "cloud_services": [],
            "architecture_patterns": [],
        },
        "fingerprint": "legacy456",
        "twin_version": 1,
        "previous_fingerprint": "",
        "discovery_time": "2026-07-28T00:00:00Z",
        "timestamp": "2026-07-28T00:00:00Z",
        "status": "CONNECTED",
    }


class TestCognitiveTwinService(unittest.TestCase):

    def setUp(self):
        self.kernel = FakeKernel()
        self.store = make_mock_service("KnowledgeStoreService")
        self.kernel._services["KnowledgeStoreService"] = self.store

    def _make_service(self):
        from services.cognitive_twin_service import CognitiveTwinService
        svc = CognitiveTwinService(self.kernel)
        svc.start()
        return svc

    # --- 1. Cognitive Summary Creation ---

    def test_cognitive_summary_creation_flutter(self):
        """Cognitive summary is generated for a Flutter project twin."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        cognition = svc.load_twin(twin)
        self.assertNotIn("error", cognition)
        self.assertIn("purpose", cognition)
        self.assertIn("domain", cognition)
        self.assertIn("architecture", cognition)
        self.assertIn("maturity", cognition)
        self.assertIn("key_components", cognition)
        self.assertIn("risks", cognition)
        self.assertIn("recommendations", cognition)
        self.assertIn("code_summary", cognition)

    def test_cognitive_summary_creation_minimal(self):
        """Cognitive summary is generated even for minimal twin."""
        svc = self._make_service()
        twin = make_minimal_twin_data()
        cognition = svc.load_twin(twin)
        self.assertNotIn("error", cognition)
        self.assertIn("purpose", cognition)
        self.assertIn("maturity", cognition)
        self.assertIn("code_summary", cognition)

    def test_cognitive_summary_has_all_eight_dimensions(self):
        """All eight cognitive dimensions are present in the output (7 original + code_summary)."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        cognition = svc.load_twin(twin)
        expected = {"purpose", "domain", "architecture", "maturity", "key_components", "risks", "recommendations", "code_summary"}
        self.assertEqual(expected, set(cognition.keys()))

    # --- 2. Domain Analysis ---

    def test_domain_analysis_mobile(self):
        """Flutter twin is classified as mobile_application."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        cognition = svc.load_twin(twin)
        domain = cognition["domain"]
        self.assertEqual(domain["domain"], "mobile_application")
        self.assertIn("Mobile", domain["label"])

    def test_domain_analysis_enterprise(self):
        """Enterprise twin is classified as enterprise_platform."""
        svc = self._make_service()
        twin = make_enterprise_twin_data()
        cognition = svc.load_twin(twin)
        domain = cognition["domain"]
        self.assertEqual(domain["domain"], "enterprise_platform")
        self.assertIn("Enterprise", domain["label"])

    def test_domain_analysis_confidence_present(self):
        """Domain analysis includes confidence level."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        cognition = svc.load_twin(twin)
        self.assertIn("confidence", cognition["domain"])
        self.assertEqual(cognition["domain"]["confidence"], "high")

    # --- 3. Purpose Analysis ---

    def test_purpose_analysis_present(self):
        """Purpose analysis extracts summary from twin."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        cognition = svc.load_twin(twin)
        purpose = cognition["purpose"]
        self.assertTrue(purpose["has_summary"])
        self.assertIn("property management", purpose["summary"].lower())

    def test_purpose_analysis_minimal(self):
        """Purpose analysis works with minimal twin data."""
        svc = self._make_service()
        twin = make_minimal_twin_data()
        cognition = svc.load_twin(twin)
        purpose = cognition["purpose"]
        self.assertFalse(purpose["has_summary"])

    # --- 4. Architecture Reasoning ---

    def test_architecture_patterns_detected(self):
        """Architecture patterns are extracted from twin."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        cognition = svc.load_twin(twin)
        arch = cognition["architecture"]
        self.assertGreater(arch["pattern_count"], 0)
        self.assertIn("Provider Pattern", arch["patterns"])

    def test_architecture_domain_patterns_matched(self):
        """Domain-specific architecture patterns are matched."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        cognition = svc.load_twin(twin)
        arch = cognition["architecture"]
        self.assertIn("domain_matched_patterns", arch)
        # Provider Pattern is expected for mobile_application
        self.assertIn("Provider Pattern", arch.get("domain_matched_patterns", []))

    def test_architecture_no_patterns_minimal(self):
        """Architecture analysis handles no patterns gracefully."""
        svc = self._make_service()
        twin = make_minimal_twin_data()
        cognition = svc.load_twin(twin)
        arch = cognition["architecture"]
        self.assertEqual(arch["pattern_count"], 0)
        self.assertEqual(arch["patterns"], [])

    # --- 5. Maturity Detection ---

    def test_maturity_flutter_established(self):
        """Flutter project with docs and git has established or better maturity."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        cognition = svc.load_twin(twin)
        maturity = cognition["maturity"]
        self.assertIn(maturity["level"], ("established", "mature"))
        self.assertGreaterEqual(maturity["score"], 0.4)

    def test_maturity_minimal_is_early(self):
        """Minimal project with few docs and no git is early stage."""
        svc = self._make_service()
        twin = make_minimal_twin_data()
        cognition = svc.load_twin(twin)
        maturity = cognition["maturity"]
        self.assertEqual(maturity["level"], "early")

    def test_maturity_has_version_control_signal(self):
        """Maturity signal shows version control when git is detected."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        cognition = svc.load_twin(twin)
        signals = [s["signal"] for s in cognition["maturity"]["signals"]]
        self.assertIn("version_control_detected", signals)

    # --- 6. Risk Detection ---

    def test_risks_detected_for_minimal(self):
        """Minimal project twin triggers multiple risk signals."""
        svc = self._make_service()
        twin = make_minimal_twin_data()
        cognition = svc.load_twin(twin)
        risks = cognition["risks"]
        self.assertGreater(risks["risk_count"], 0)
        self.assertGreater(risks["high_severity_count"], 0)

    def test_risks_legacy_tech_detected(self):
        """Enterprise twin with AngularJS/jQuery triggers legacy tech risks."""
        svc = self._make_service()
        twin = make_enterprise_twin_data()
        cognition = svc.load_twin(twin)
        risks = cognition["risks"]["risks"]
        risk_details = " ".join(r["risk"] for r in risks)
        self.assertIn("angularjs", risk_details.lower())
        self.assertIn("jquery", risk_details.lower())

    def test_risks_sorted_by_severity(self):
        """Risks are sorted with highest severity first."""
        svc = self._make_service()
        twin = make_enterprise_twin_data()
        cognition = svc.load_twin(twin)
        risks = cognition["risks"]["risks"]
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        for i in range(len(risks) - 1):
            self.assertLessEqual(
                severity_order.get(risks[i]["severity"], 99),
                severity_order.get(risks[i + 1]["severity"], 99),
            )

    # --- 7. Recommendations ---

    def test_recommendations_generated_for_minimal(self):
        """Minimal project generates recommendations for improvement."""
        svc = self._make_service()
        twin = make_minimal_twin_data()
        cognition = svc.load_twin(twin)
        recs = cognition["recommendations"]
        self.assertGreater(recs["recommendation_count"], 0)
        self.assertGreater(recs["high_priority_count"], 0)

    def test_recommendations_no_ci_for_enterprise(self):
        """Enterprise twin without CI config gets CI recommendation."""
        svc = self._make_service()
        twin = make_enterprise_twin_data()
        cognition = svc.load_twin(twin)
        recs = cognition["recommendations"]["recommendations"]
        rec_texts = [r["recommendation"] for r in recs]
        found = any("CI/CD" in r for r in rec_texts)
        self.assertTrue(found)

    def test_recommendations_sorted_by_priority(self):
        """Recommendations are sorted with highest priority first."""
        svc = self._make_service()
        twin = make_minimal_twin_data()
        cognition = svc.load_twin(twin)
        recs = cognition["recommendations"]["recommendations"]
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        for i in range(len(recs) - 1):
            self.assertLessEqual(
                priority_order.get(recs[i].get("priority", "medium"), 99),
                priority_order.get(recs[i + 1].get("priority", "medium"), 99),
            )

    # --- 8. Question Answering ---

    def test_ask_overview(self):
        """ask() returns an overview for 'Explain this project'."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        svc.load_twin(twin)
        result = svc.ask("Explain this project")
        self.assertIn("answer", result)
        self.assertIn("evidence", result)
        self.assertIn("confidence", result)
        self.assertGreater(len(result["answer"]), 20)

    def test_ask_purpose(self):
        """ask() returns purpose for 'What is the purpose'."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        svc.load_twin(twin)
        result = svc.ask("What is the purpose of this project")
        self.assertIn("answer", result)
        self.assertIn("property management", result["answer"].lower())

    def test_ask_domain(self):
        """ask() returns domain classification."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        svc.load_twin(twin)
        result = svc.ask("What domain is this")
        self.assertIn("mobile", result["answer"].lower())

    def test_ask_architecture(self):
        """ask() returns architecture information."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        svc.load_twin(twin)
        result = svc.ask("Tell me about the architecture")
        self.assertIn("Provider", result["answer"])

    def test_ask_maturity(self):
        """ask() returns maturity assessment."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        svc.load_twin(twin)
        result = svc.ask("How mature is this project")
        self.assertIn("answer", result)

    def test_ask_risks(self):
        """ask() returns risk analysis."""
        svc = self._make_service()
        twin = make_enterprise_twin_data()
        svc.load_twin(twin)
        result = svc.ask("What are the risks")
        self.assertIn("angularjs", result["answer"].lower())

    def test_ask_recommendations(self):
        """ask() returns recommendations."""
        svc = self._make_service()
        twin = make_minimal_twin_data()
        svc.load_twin(twin)
        result = svc.ask("What do you recommend")
        self.assertIn("recommendation", result["answer"].lower())

    def test_ask_tech_stack(self):
        """ask() returns technology stack information."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        svc.load_twin(twin)
        result = svc.ask("What tech stack is used")
        self.assertIn("Dart", result["answer"])
        self.assertIn("Flutter", result["answer"])

    def test_ask_no_twin_loaded(self):
        """ask() returns helpful message when no twin loaded."""
        svc = self._make_service()
        result = svc.ask("Explain this project")
        self.assertIn("No project twin loaded", result["answer"])

    def test_ask_unknown_question(self):
        """ask() provides guidance for unrecognized questions."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        svc.load_twin(twin)
        result = svc.ask("What color is the sky")
        self.assertIn("answer", result)

    def test_ask_confidence_high(self):
        """ask() returns 'high' confidence for well-known questions."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        svc.load_twin(twin)
        result = svc.ask("Explain this project")
        self.assertEqual(result["confidence"], "high")

    # --- 9. Key Components ---

    def test_key_components_identified(self):
        """Key components are identified from documentation categories."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        cognition = svc.load_twin(twin)
        comps = cognition["key_components"]
        self.assertGreater(comps["component_count"], 0)
        self.assertTrue(comps["has_documentation"])

    # --- 9b. Code Summary ---

    def test_code_summary_in_cognition(self):
        """code_summary dimension exists in cognition with default values."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        cognition = svc.load_twin(twin)
        code = cognition["code_summary"]
        self.assertIn("languages", code)
        self.assertIn("components", code)
        self.assertIn("architecture_layers", code)
        self.assertIn("complexity", code)

    def test_code_summary_empty_when_no_code_intel(self):
        """code_summary returns empty structure when no code_intel service."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        cognition = svc.load_twin(twin)
        code = cognition["code_summary"]
        self.assertIsInstance(code.get("languages"), list)

    # --- 10. Key Components Infrastructure ---

    def test_key_components_infrastructure(self):
        """Infrastructure components are detected from config files."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        cognition = svc.load_twin(twin)
        comps = cognition["key_components"]
        self.assertTrue(comps["has_infrastructure"])
        names = [c["name"] for c in comps["components"]]
        self.assertTrue(any("CI/CD" in n for n in names))
        self.assertTrue(any("Containerization" in n for n in names))

    # --- 10. Load from path ---

    def test_load_twin_from_path(self):
        """Loading twin from JSON file path works."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "twin.json")
            with open(path, "w") as f:
                json.dump(twin, f)
            result = svc.load_twin_from_path(path)
            self.assertNotIn("error", result)
            self.assertIn("purpose", result)

    def test_load_twin_from_path_not_found(self):
        """Loading from nonexistent path returns error."""
        svc = self._make_service()
        result = svc.load_twin_from_path("/nonexistent/path.json")
        self.assertIn("error", result)

    # --- 11. Has twin check ---

    def test_has_twin_false_initially(self):
        """has_twin() returns False when no twin loaded."""
        svc = self._make_service()
        self.assertFalse(svc.has_twin())

    def test_has_twin_true_after_load(self):
        """has_twin() returns True after loading a twin."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        svc.load_twin(twin)
        self.assertTrue(svc.has_twin())

    def test_has_twin_by_fingerprint(self):
        """has_twin(fingerprint) checks specific twin."""
        svc = self._make_service()
        twin = make_flutter_twin_data()
        svc.load_twin(twin)
        self.assertTrue(svc.has_twin("abc123"))
        self.assertFalse(svc.has_twin("nonexistent"))


class TestCognitiveTwinGUI(unittest.TestCase):
    """GUI-level cognitive response tests using HTTP handler pattern."""

    def setUp(self):
        self.kernel = FakeKernel()
        self.store = make_mock_service("KnowledgeStoreService")
        self.kernel._services["KnowledgeStoreService"] = self.store

    def test_gui_cognitive_response_structure(self):
        """Cognitive answer matches expected JSON structure for GUI consumption."""
        from services.cognitive_twin_service import CognitiveTwinService
        svc = CognitiveTwinService(self.kernel)
        svc.start()
        twin = make_flutter_twin_data()
        svc.load_twin(twin)

        result = svc.ask("Explain this project")
        # GUI expects: answer (string), evidence (list), confidence (string)
        self.assertIsInstance(result.get("answer"), str)
        self.assertIsInstance(result.get("evidence"), list)
        self.assertIsInstance(result.get("confidence"), str)
        self.assertIn(result["confidence"], ("high", "medium", "low", "none"))

    def test_gui_cognitive_evidence_has_type_and_source(self):
        """Each evidence item has type, source, and detail fields."""
        from services.cognitive_twin_service import CognitiveTwinService
        svc = CognitiveTwinService(self.kernel)
        svc.start()
        twin = make_flutter_twin_data()
        svc.load_twin(twin)

        result = svc.ask("Explain this project")
        for item in result.get("evidence", []):
            self.assertIn("type", item)
            self.assertIn("source", item)
            self.assertIn("detail", item)

    def test_gui_cognitive_mcp_tool_registration(self):
        """Cognitive twin tool is registered in MCPToolService."""
        from services.mcp_tool_service import MCPToolService
        from services.cognitive_twin_service import CognitiveTwinService
        cognitive_twin = CognitiveTwinService(self.kernel)
        cognitive_twin.start()
        self.kernel._services["CognitiveTwinService"] = cognitive_twin
        mcp = MCPToolService(self.kernel)
        mcp.start()
        tools = mcp.list_tools()
        tool_names = [t["name"] for t in tools]
        self.assertIn("cognitive_twin_query", tool_names)

    def test_gui_cognitive_endpoint_pattern(self):
        """Cognitive endpoint returns answer dict as expected by GUI."""
        from services.cognitive_twin_service import CognitiveTwinService
        svc = CognitiveTwinService(self.kernel)
        svc.start()
        twin = make_flutter_twin_data()
        cognition = svc.load_twin(twin)

        # Simulate what the GUI would call
        overview = svc.ask("Explain this project")
        self.assertIsNotNone(overview.get("answer"))
        purpose = svc.ask("What is the purpose")
        self.assertIsNotNone(purpose.get("answer"))
        risks = svc.ask("What are the risks")
        self.assertIsNotNone(risks.get("answer"))
        maturity = svc.ask("How mature is this")
        self.assertIsNotNone(maturity.get("answer"))
        tech = svc.ask("What tech stack")
        self.assertIsNotNone(tech.get("answer"))
        code_q = svc.ask("code intelligence")
        self.assertIsNotNone(code_q.get("answer"))


if __name__ == "__main__":
    unittest.main()
