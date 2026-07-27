"""Tests for GUI MCP response format integrity.

Verifies that every MCP tool returns valid JSON-RPC responses that the
gui/mcp_client.py _send method can parse without error.
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest


class FakeKernel:
    def __init__(self):
        self._services = {}
        self._config = {}

    def get_service(self, name):
        return self._services.get(name)

    def register_service(self, service):
        self._services[service.name] = service
        service.kernel = self

    def set_config(self, config):
        self._config.update(config)

    def get_config(self):
        return self._config


# Re-use the helpers from test_phase19_project_twin
def make_mock_service(name, **attrs):
    from unittest.mock import MagicMock
    svc = MagicMock()
    svc.name = name
    svc.kernel = None
    for k, v in attrs.items():
        setattr(svc, k, v)
    return svc


def create_flutter_project(temp_dir):
    """Create a Flutter project for testing."""
    project_dir = os.path.join(temp_dir, "eagles_property")
    os.makedirs(project_dir)
    os.makedirs(os.path.join(project_dir, "lib"))
    os.makedirs(os.path.join(project_dir, ".git"))
    with open(os.path.join(project_dir, "pubspec.yaml"), "w") as f:
        f.write("name: eagles_property\ndependencies:\n  flutter:\n    sdk: flutter\n  firebase_core: ^2.0.0\n")
    with open(os.path.join(project_dir, "lib", "main.dart"), "w") as f:
        f.write("void main() {}\n")
    return project_dir


class TestMCPResponseDiagnostics(unittest.TestCase):
    """Tests for _diagnose_response helper."""

    def test_empty_response(self):
        from gui.mcp_client import _diagnose_response
        msg = _diagnose_response("", "test_tool")
        self.assertIn("Empty response", msg)

    def test_blank_line(self):
        from gui.mcp_client import _diagnose_response
        msg = _diagnose_response("  \n", "test_tool")
        self.assertIn("Blank line", msg)

    def test_non_json_text(self):
        from gui.mcp_client import _diagnose_response
        msg = _diagnose_response("[EVENT BUS] SOME EVENT SUBSCRIBERS: 0\n", "test_tool")
        self.assertIn("test_tool", msg)
        self.assertIn("EVENT BUS", msg)

    def test_hex_preview_included(self):
        from gui.mcp_client import _diagnose_response
        msg = _diagnose_response("hello\n", "test_tool")
        self.assertIn("68 65 6c 6c 6f", msg)  # hex of "hello"


class TestMCPResponseFormatLive(unittest.TestCase):
    """Starts a real MCP server subprocess and verifies tool response format."""

    @classmethod
    def setUpClass(cls):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.memory_path = tempfile.mkdtemp(prefix="eye_test_mcp_")
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.join(project_root, "src")
        env["EAGLE_EYE_MEMORY_PATH"] = cls.memory_path
        cls.proc = subprocess.Popen(
            [sys.executable, "-m", "src.mcp.mcp_server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        # Drain stderr in background
        cls._stderr_lines = []
        def _reader():
            try:
                for line in iter(cls.proc.stderr.readline, ""):
                    cls._stderr_lines.append(line)
            except ValueError:
                pass
        cls._stderr_thread = threading.Thread(target=_reader, daemon=True)
        cls._stderr_thread.start()

    @classmethod
    def tearDownClass(cls):
        if cls.proc:
            cls.proc.terminate()
            cls.proc.wait(timeout=5)

    def _send(self, method, params=None):
        msg_id = getattr(self, "_next_id", 0) + 1
        self._next_id = msg_id
        req = {"jsonrpc": "2.0", "id": msg_id, "method": method}
        if params:
            req["params"] = params
        self.proc.stdin.write(json.dumps(req) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        self.assertIsNotNone(line, "MCP server closed connection")
        return line

    def test_initialize_returns_valid_json(self):
        line = self._send("initialize", {"protocolVersion": "2025-03-26"})
        data = json.loads(line.strip())
        self.assertEqual(data["jsonrpc"], "2.0")
        self.assertIn("result", data)
        self.assertEqual(data["result"]["protocolVersion"], "2025-03-26")

    def test_tools_list_returns_valid_json(self):
        # Must initialize first
        self._send("initialize", {"protocolVersion": "2025-03-26"})
        line = self._send("tools/list")
        data = json.loads(line.strip())
        self.assertIn("result", data)
        tools = data["result"]["tools"]
        self.assertGreater(len(tools), 40)
        names = [t["name"] for t in tools]
        self.assertIn("discover_project_twin", names)

    def test_discover_project_twin_returns_valid_json(self):
        self._send("initialize", {"protocolVersion": "2025-03-26"})
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            line = self._send("tools/call", {
                "name": "discover_project_twin",
                "arguments": {"project_path": project_dir},
            })
            data = json.loads(line.strip())
            self.assertEqual(data["jsonrpc"], "2.0")
            self.assertIn("result", data)
            content = data["result"]["content"]
            self.assertEqual(len(content), 1)
            self.assertEqual(content[0]["type"], "text")
            inner = json.loads(content[0]["text"])
            self.assertIn("discovery", inner)
            discovery = inner["discovery"]
            self.assertEqual(discovery["status"], "CONNECTED")
            self.assertIn("notifications", discovery)
            messages = [n["message"] for n in discovery["notifications"]]
            self.assertIn("CONNECTED", messages)

    def test_no_eventbus_leaks_to_stdout(self):
        """Verify EventBus publish() messages don't corrupt the protocol stream."""
        self._send("initialize", {"protocolVersion": "2025-03-26"})
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            line = self._send("tools/call", {
                "name": "discover_project_twin",
                "arguments": {"project_path": project_dir},
            })
            # Must start with '{' (JSON-RPC envelope)
            stripped = line.strip()
            self.assertTrue(stripped.startswith("{"),
                            "Response must start with '{', got: %r" % stripped[:100])
            json.loads(stripped)  # must not raise

    def test_mcp_client_wrapper(self):
        """Test through the actual MCPClient class."""
        from gui.mcp_client import MCPClient
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = create_flutter_project(tmp)
            args = [sys.executable, "-m", "src.mcp.mcp_server"]
            env = os.environ.copy()
            env["PYTHONPATH"] = os.path.join(project_root, "src")
            env["EAGLE_EYE_MEMORY_PATH"] = tmp
            client = MCPClient.connect_stdio(args, extra_env={"EAGLE_EYE_MEMORY_PATH": tmp})
            try:
                result = client.call_tool("discover_project_twin", {"project_path": project_dir})
                self.assertIn("discovery", result)
                self.assertEqual(result["discovery"]["status"], "CONNECTED")
            finally:
                client.close()


if __name__ == "__main__":
    unittest.main()
