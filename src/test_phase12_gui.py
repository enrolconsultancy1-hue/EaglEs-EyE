"""Phase 12 GUI tests — MCP client, server, and dashboard rendering."""

import json
import os
import sys
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gui.mcp_client import MCPClient
from gui.server import GUIRequestHandler, run_gui_server


class FakeMCPProcess:
    """Simulates an MCP server subprocess for testing."""
    def __init__(self):
        self.stdin = MagicMock()
        self.stdout = MagicMock()
        self._responses = []

    def add_response(self, data):
        self._responses.append(json.dumps(data) + "\n")

    def terminate(self):
        pass

    def wait(self, timeout=None):
        pass

    def kill(self):
        pass


class Phase12MCPClientTests(unittest.TestCase):
    def test_connect_and_initialize(self):
        proc = FakeMCPProcess()
        proc.stdout.readline.side_effect = [
            '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-03-26","capabilities":{"tools":{}},"serverInfo":{"name":"EaglEs EyE MCP","version":"1.1.0"}}}\n'
        ]
        client = MCPClient(proc)
        client._initialize()
        self.assertTrue(client._proc is not None)

    def test_list_tools(self):
        proc = FakeMCPProcess()
        proc.stdout.readline.side_effect = [
            '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-03-26","capabilities":{"tools":{}},"serverInfo":{"name":"EaglEs EyE MCP","version":"1.1.0"}}}\n',
            '{"jsonrpc":"2.0","id":2,"result":{"content":[{"type":"text","text":"{\\"tools\\":[{\\"name\\":\\"search_memory\\"}]}"}]}}\n'
        ]
        client = MCPClient(proc)
        client._initialize()
        tools = client.list_tools()
        self.assertIsInstance(tools, list)
        self.assertGreaterEqual(len(tools), 1)

    def test_call_tool(self):
        proc = FakeMCPProcess()
        result_text = json.dumps({"results": [{"id": 1, "content": "test"}]})
        proc.stdout.readline.side_effect = [
            '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-03-26","capabilities":{"tools":{}},"serverInfo":{"name":"EaglEs EyE MCP","version":"1.1.0"}}}\n',
            '{"jsonrpc":"2.0","id":2,"result":{"content":[{"type":"text","text":' + json.dumps(result_text) + '}]}}\n'
        ]
        client = MCPClient(proc)
        client._initialize()
        result = client.call_tool("search_memory", {"query": "test"})
        self.assertIn("results", result)
        self.assertEqual(result["results"][0]["id"], 1)

    def test_call_tool_error_raises(self):
        proc = FakeMCPProcess()
        proc.stdout.readline.side_effect = [
            '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-03-26","capabilities":{"tools":{}},"serverInfo":{"name":"EaglEs EyE MCP","version":"1.1.0"}}}\n',
            '{"jsonrpc":"2.0","id":2,"error":{"code":-32601,"message":"Unknown tool: bogus"}}\n'
        ]
        client = MCPClient(proc)
        client._initialize()
        with self.assertRaises(RuntimeError):
            client.call_tool("bogus", {})

    def test_context_manager(self):
        proc = FakeMCPProcess()
        proc.stdout.readline.side_effect = [
            '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-03-26","capabilities":{"tools":{}},"serverInfo":{"name":"EaglEs EyE MCP","version":"1.1.0"}}}\n'
        ]
        with MCPClient(proc) as client:
            self.assertIsNotNone(client)

    def test_close_handles_timeout(self):
        proc = FakeMCPProcess()
        proc.stdout.readline.side_effect = [
            '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-03-26","capabilities":{"tools":{}},"serverInfo":{"name":"EaglEs EyE MCP","version":"1.1.0"}}}\n'
        ]
        client = MCPClient(proc)
        client._initialize()
        client.close()
        self.assertIsNone(client._proc)


class Phase12ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.templates_dir = os.path.join(os.path.dirname(__file__), "..", "gui", "templates")
        self.static_dir = os.path.join(os.path.dirname(__file__), "..", "gui", "static")
        self.handler = GUIRequestHandler
        self.orig_mcp = GUIRequestHandler.mcp
        self.mock_client = MagicMock()
        GUIRequestHandler.mcp = self.mock_client

    def tearDown(self):
        GUIRequestHandler.mcp = self.orig_mcp
        self.temp.cleanup()

    def test_dashboard_template_exists(self):
        path = os.path.join(self.templates_dir, "dashboard.html")
        self.assertTrue(os.path.isfile(path))

    def test_timeline_template_exists(self):
        path = os.path.join(self.templates_dir, "timeline.html")
        self.assertTrue(os.path.isfile(path))

    def test_twin_template_exists(self):
        path = os.path.join(self.templates_dir, "twin.html")
        self.assertTrue(os.path.isfile(path))

    def test_search_template_exists(self):
        path = os.path.join(self.templates_dir, "search.html")
        self.assertTrue(os.path.isfile(path))

    def test_graph_template_exists(self):
        path = os.path.join(self.templates_dir, "graph.html")
        self.assertTrue(os.path.isfile(path))

    def test_explain_template_exists(self):
        path = os.path.join(self.templates_dir, "explain.html")
        self.assertTrue(os.path.isfile(path))

    def test_metrics_template_exists(self):
        path = os.path.join(self.templates_dir, "metrics.html")
        self.assertTrue(os.path.isfile(path))

    def test_style_css_exists(self):
        path = os.path.join(self.static_dir, "style.css")
        self.assertTrue(os.path.isfile(path))

    def test_dashboard_content_has_nav(self):
        path = os.path.join(self.templates_dir, "dashboard.html")
        content = open(path).read()
        self.assertIn("Mission Control", content)
        self.assertIn("Dashboard", content)
        self.assertIn("Timeline", content)
        self.assertIn("Explain", content)
        self.assertIn("Graph", content)

    def test_explain_template_contains_layers(self):
        path = os.path.join(self.templates_dir, "explain.html")
        content = open(path).read()
        self.assertIn("Observed Facts", content)
        self.assertIn("Derived Relationships", content)
        self.assertIn("Evidence-Backed Explanation", content)
        self.assertIn("No hidden reasoning", content)

    def test_mcp_client_exists(self):
        from gui.mcp_client import MCPClient
        self.assertIsNotNone(MCPClient)

    def test_server_imports(self):
        from gui.server import run_gui_server, GUIRequestHandler
        self.assertIsNotNone(run_gui_server)
        self.assertIsNotNone(GUIRequestHandler)


class Phase12AppTests(unittest.TestCase):
    def test_app_imports(self):
        from gui.app import main, start_mcp_server_process
        self.assertIsNotNone(main)

    def test_mcp_client_connect_stdio_raises_on_bad_command(self):
        with self.assertRaises(FileNotFoundError):
            MCPClient.connect_stdio(["nonexistent_command_xyz"])


class Phase12LargeWorkspacePerformanceTests(unittest.TestCase):
    def test_fast_processing_of_large_event_list(self):
        import time
        proc = FakeMCPProcess()
        large_result = json.dumps({"results": [{"id": i, "path": "/path/to/file_%d.py" % i, "event_type": "FILE_MODIFIED", "timestamp": "2026-07-25T12:00:00"} for i in range(1000)]})
        proc.stdout.readline.side_effect = [
            '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-03-26","capabilities":{"tools":{}},"serverInfo":{"name":"EaglEs EyE MCP","version":"1.1.0"}}}\n',
            '{"jsonrpc":"2.0","id":2,"result":{"content":[{"type":"text","text":' + json.dumps(large_result) + '}]}}\n'
        ]
        client = MCPClient(proc)
        client._initialize()
        start = time.time()
        result = client.call_tool("search_memory", {"query": "test"})
        elapsed = time.time() - start
        self.assertEqual(len(result["results"]), 1000)
        self.assertLess(elapsed, 2.0, "Processing 1000 results should take < 2 seconds")


if __name__ == "__main__":
    unittest.main()
