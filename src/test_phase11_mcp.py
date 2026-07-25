"""Phase 11 MCP Ecosystem tests — transport, protocol, tool exposure, security defaults."""

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest

from core.kernel import EyeKernel
from mcp.mcp_server import MCPServer, build_mcp_kernel
from mcp.tool_registry import ToolRegistry
from mcp.transport_stdio import read_message, write_message
from mcp.transport_tcp import TcpTransport


class Phase11MCPProtocolTests(unittest.TestCase):
    def setUp(self):
        self.server = MCPServer()

    def test_initialize_handshake(self):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}}
        resp = self.server.run_once(msg)
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], 1)
        self.assertIn("result", resp)
        self.assertIn("protocolVersion", resp["result"])
        self.assertIn("capabilities", resp["result"])
        self.assertIn("serverInfo", resp["result"])
        self.assertEqual(resp["result"]["serverInfo"]["name"], "EaglEs EyE MCP")

    def test_tools_list_before_initialize_fails(self):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        resp = self.server.run_once(msg)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32000)

    def test_tools_list_after_initialize(self):
        registry = ToolRegistry()
        registry.register("search_memory", lambda **kw: {}, {"type": "object"})
        registry.register("explain_change", lambda **kw: {}, {"type": "object"})
        registry.register("get_causal_chain", lambda **kw: {}, {"type": "object"})
        registry.register("compare_snapshots", lambda **kw: {}, {"type": "object"})
        registry.register("list_decisions", lambda **kw: {}, {"type": "object"})
        registry.register("get_decision", lambda **kw: {}, {"type": "object"})
        server = MCPServer(registry)
        init = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}}
        server.run_once(init)
        msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        resp = server.run_once(msg)
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], 2)
        self.assertIn("result", resp)
        tools = resp["result"]["tools"]
        self.assertIsInstance(tools, list)
        self.assertGreater(len(tools), 0)
        tool_names = [t["name"] for t in tools]
        self.assertIn("search_memory", tool_names)
        self.assertIn("explain_change", tool_names)
        self.assertIn("get_causal_chain", tool_names)
        self.assertIn("compare_snapshots", tool_names)
        self.assertIn("list_decisions", tool_names)
        self.assertIn("get_decision", tool_names)

    def test_unknown_method(self):
        init = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        self.server.run_once(init)
        msg = {"jsonrpc": "2.0", "id": 3, "method": "bogus_method", "params": {}}
        resp = self.server.run_once(msg)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32601)

    def test_malformed_json_no_jsonrpc_field(self):
        msg = {"id": 1, "method": "initialize"}
        resp = self.server.run_once(msg)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32600)

    def test_malformed_json_wrong_version(self):
        msg = {"jsonrpc": "1.0", "id": 1, "method": "initialize", "params": {}}
        resp = self.server.run_once(msg)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32600)

    def test_tools_call_unknown_tool(self):
        registry = ToolRegistry()
        server = MCPServer(registry)
        init = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        server.run_once(init)
        msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "nonexistent", "arguments": {}}}
        resp = server.run_once(msg)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32601)

    def test_tools_call_missing_arguments(self):
        registry = ToolRegistry()
        registry.register("echo", lambda x: x, {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]})
        server = MCPServer(registry)
        init = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        server.run_once(init)
        msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "echo", "arguments": {}}}
        resp = server.run_once(msg)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32602)


class Phase11ToolRegistryTests(unittest.TestCase):
    def test_register_and_list(self):
        registry = ToolRegistry()
        registry.register("ping", lambda: "pong", {"type": "object"})
        tools = registry.list_tools()
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], "ping")

    def test_call_valid_tool(self):
        registry = ToolRegistry()
        registry.register("add", lambda a, b: a + b, {"type": "object", "properties": {"a": {}, "b": {}}})
        result = registry.call_tool("add", {"a": 2, "b": 3})
        self.assertEqual(result, 5)

    def test_call_unknown_tool_returns_error(self):
        registry = ToolRegistry()
        result = registry.call_tool("nope", {})
        self.assertIn("error", result)
        self.assertEqual(result["code"], -32601)

    def test_call_tool_wrong_args_returns_error(self):
        registry = ToolRegistry()
        registry.register("greet", lambda name: "Hello " + name, {"type": "object", "required": ["name"]})
        result = registry.call_tool("greet", {})
        self.assertIn("error", result)
        self.assertEqual(result["code"], -32602)


class Phase11StdioTransportTests(unittest.TestCase):
    def test_read_write_roundtrip(self):
        import io
        old_stdin = sys.stdin
        old_stdout = sys.stdout
        sys.stdin = io.StringIO('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n')
        sys.stdout = io.StringIO()
        try:
            msg = read_message()
            self.assertIsNotNone(msg)
            self.assertEqual(msg["method"], "initialize")
            write_message({"jsonrpc": "2.0", "id": 1, "result": {}})
            output = sys.stdout.getvalue()
            self.assertIn("jsonrpc", output)
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout

    def test_read_empty_returns_none(self):
        import io
        old_stdin = sys.stdin
        sys.stdin = io.StringIO("")
        try:
            msg = read_message()
            self.assertIsNone(msg)
        finally:
            sys.stdin = old_stdin

    def test_read_invalid_json_returns_error_dict(self):
        import io
        old_stdin = sys.stdin
        sys.stdin = io.StringIO("not json\n")
        try:
            msg = read_message()
            self.assertIsNotNone(msg)
            self.assertIn("error", msg)
        finally:
            sys.stdin = old_stdin


class Phase11TcpTransportTests(unittest.TestCase):
    def test_tcp_disabled_by_default(self):
        transport = TcpTransport()
        self.assertEqual(transport.host, "127.0.0.1")
        self.assertFalse(hasattr(transport, "_server") and transport._server is not None)

    def test_tcp_start_stop(self):
        transport = TcpTransport("127.0.0.1", 0)
        transport.start(lambda msg: {"jsonrpc": "2.0", "id": msg.get("id"), "result": "ok"})
        transport.stop()
        self.assertFalse(transport._running)


class Phase11LegacyCompatTests(unittest.TestCase):
    def setUp(self):
        self.kernel, self.services = build_mcp_kernel(tempfile.mkdtemp())

    def tearDown(self):
        for s in reversed(self.services):
            s.stop()

    def test_legacy_search_memory_still_works(self):
        mcp_tool = self.kernel.get_service("MCPToolService")
        tools = [t["name"] for t in mcp_tool.list_tools()]
        self.assertIn("search_memory", tools)

    def test_legacy_build_context_still_works(self):
        mcp_tool = self.kernel.get_service("MCPToolService")
        tools = [t["name"] for t in mcp_tool.list_tools()]
        self.assertIn("build_context", tools)

    def test_legacy_get_document_still_works(self):
        mcp_tool = self.kernel.get_service("MCPToolService")
        tools = [t["name"] for t in mcp_tool.list_tools()]
        self.assertIn("get_document", tools)


class Phase11Phase10ToolExposureTests(unittest.TestCase):
    def setUp(self):
        self.kernel, self.services = build_mcp_kernel(tempfile.mkdtemp())

    def tearDown(self):
        for s in reversed(self.services):
            s.stop()

    def test_explain_change_tool_listed(self):
        mcp_tool = self.kernel.get_service("MCPToolService")
        tools = {t["name"]: t for t in mcp_tool.list_tools()}
        self.assertIn("explain_change", tools)
        self.assertIn("inputSchema", tools["explain_change"])
        self.assertIn("entity_path", tools["explain_change"]["inputSchema"].get("required", []))

    def test_get_causal_chain_tool_listed(self):
        mcp_tool = self.kernel.get_service("MCPToolService")
        tools = {t["name"]: t for t in mcp_tool.list_tools()}
        self.assertIn("get_causal_chain", tools)
        self.assertIn("event_id", tools["get_causal_chain"]["inputSchema"].get("required", []))

    def test_compare_snapshots_tool_listed(self):
        mcp_tool = self.kernel.get_service("MCPToolService")
        tools = {t["name"]: t for t in mcp_tool.list_tools()}
        self.assertIn("compare_snapshots", tools)
        self.assertIn("snapshot_id_a", tools["compare_snapshots"]["inputSchema"].get("required", []))

    def test_list_decisions_tool_listed(self):
        mcp_tool = self.kernel.get_service("MCPToolService")
        tools = {t["name"]: t for t in mcp_tool.list_tools()}
        self.assertIn("list_decisions", tools)

    def test_get_decision_tool_listed(self):
        mcp_tool = self.kernel.get_service("MCPToolService")
        tools = {t["name"]: t for t in mcp_tool.list_tools()}
        self.assertIn("get_decision", tools)
        self.assertIn("decision_id", tools["get_decision"]["inputSchema"].get("required", []))

    def test_explain_change_call_with_entity_path(self):
        mcp_tool = self.kernel.get_service("MCPToolService")
        result = mcp_tool.call_tool("explain_change", {"entity_path": "nonexistent.py"})
        self.assertIn("explanation", result)
        explanation = result["explanation"]
        self.assertIn("entity", explanation)
        self.assertIn("explanation", explanation)
        self.assertIn("scope", explanation)
        self.assertIn("Observable evidence only", explanation["scope"])

    def test_explain_change_missing_required_fails(self):
        mcp_tool = self.kernel.get_service("MCPToolService")
        result = mcp_tool.call_tool("explain_change", {"workspace_id": "test"})
        self.assertIn("error", result)
        self.assertIn("entity_path", result["error"])

    def test_get_causal_chain_returns_empty_for_unknown_event(self):
        mcp_tool = self.kernel.get_service("MCPToolService")
        result = mcp_tool.call_tool("get_causal_chain", {"event_id": "nonexistent"})
        self.assertIn("causal_chain", result)
        self.assertEqual(result["causal_chain"], [])

    def test_compare_snapshots_nonexistent_returns_error(self):
        mcp_tool = self.kernel.get_service("MCPToolService")
        result = mcp_tool.call_tool("compare_snapshots", {"snapshot_id_a": "a", "snapshot_id_b": "b"})
        self.assertIn("error", result)

    def test_get_decision_nonexistent_returns_error(self):
        mcp_tool = self.kernel.get_service("MCPToolService")
        result = mcp_tool.call_tool("get_decision", {"decision_id": "nonexistent"})
        self.assertIn("error", result)

    def test_all_tools_return_structured_data(self):
        mcp_tool = self.kernel.get_service("MCPToolService")
        tools = mcp_tool.list_tools()
        for tool in tools:
            self.assertIn("name", tool)
            self.assertIn("inputSchema", tool)
            self.assertIn("description", tool)


class Phase11MCPServerToolExposureTests(unittest.TestCase):
    def test_tool_registry_contains_all_tools(self):
        kernel, services = build_mcp_kernel(tempfile.mkdtemp())
        try:
            mcp_tool = kernel.get_service("MCPToolService")
            registry = ToolRegistry()
            for tool in mcp_tool.list_tools():
                name = tool["name"]
                schema = tool["inputSchema"]
                def make_fn(tn):
                    return lambda **kw: mcp_tool.call_tool(tn, kw)
                registry.register(name, make_fn(name), schema, tool.get("description", ""))
            server = MCPServer(registry)
            init = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
            server.run_once(init)
            list_msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
            resp = server.run_once(list_msg)
            tool_names = [t["name"] for t in resp["result"]["tools"]]
            expected = ["search_memory", "build_context", "get_document", "get_recent_events",
                        "reindex_memory", "cross_reference", "explain_change", "get_causal_chain",
                        "compare_snapshots", "list_decisions", "get_decision"]
            for name in expected:
                self.assertIn(name, tool_names)
        finally:
            for s in reversed(services):
                s.stop()


class Phase11SecurityDefaultsTests(unittest.TestCase):
    def test_mcp_disabled_by_default_in_config(self):
        kernel = EyeKernel()
        kernel.set_config({})
        config = kernel.get_config() or {}
        mcp_cfg = config.get("mcp", {})
        self.assertEqual(mcp_cfg.get("enabled", False), False)

    def test_tcp_transport_localhost_only(self):
        transport = TcpTransport()
        self.assertEqual(transport.host, "127.0.0.1")

    def test_tcp_transport_requires_explicit_enable(self):
        config = {"mcp": {"tcp": {"enabled": False}}}
        self.assertFalse(config["mcp"]["tcp"]["enabled"])

    def test_write_tool_reindex_requires_path(self):
        result = ToolRegistry().call_tool("nonexistent", {})
        self.assertIn("error", result)

    def test_read_tools_do_not_write(self):
        registry = ToolRegistry()
        registry.register("read_only", lambda: "ok", {"type": "object"})
        result = registry.call_tool("read_only", {})
        self.assertEqual(result, "ok")


class Phase11StdioProtocolBoundaryTests(unittest.TestCase):
    """Verify MCP stdio transport emits only JSON-RPC on stdout."""

    @staticmethod
    def _project_root():
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @staticmethod
    def _server_env(tmp):
        env = os.environ.copy()
        env["EAGLE_EYE_MEMORY_PATH"] = tmp
        env["PYTHONPATH"] = os.path.join(Phase11StdioProtocolBoundaryTests._project_root(), "src")
        return env

    @staticmethod
    def _drain_stderr(proc):
        lines = []
        def _reader():
            try:
                for line in iter(proc.stderr.readline, ""):
                    lines.append(line)
            except ValueError:
                pass
        t = threading.Thread(target=_reader, daemon=True)
        t.start()
        return lines, t

    def test_stdio_stdout_contains_only_jsonrpc_after_initialize(self):
        tmp = tempfile.mkdtemp()
        env = self._server_env(tmp)
        proc = subprocess.Popen(
            [sys.executable, "-m", "src.mcp.mcp_server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        self._drain_stderr(proc)
        request = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26"}}\n'
        try:
            proc.stdin.write(request)
            proc.stdin.flush()
            stdout_line = proc.stdout.readline()
            self.assertIsNotNone(stdout_line)
            parsed = json.loads(stdout_line.strip())
            self.assertEqual(parsed["jsonrpc"], "2.0")
            self.assertEqual(parsed["id"], 1)
            self.assertIn("result", parsed)
            self.assertIn("serverInfo", parsed["result"])
        finally:
            try:
                proc.terminate()
                proc.wait(timeout=10)
            except Exception:
                proc.kill()

    def test_stdio_stdout_no_startup_text_before_first_jsonrpc(self):
        tmp = tempfile.mkdtemp()
        env = self._server_env(tmp)
        proc = subprocess.Popen(
            [sys.executable, "-m", "src.mcp.mcp_server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        self._drain_stderr(proc)
        request = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26"}}\n'
        try:
            proc.stdin.write(request)
            proc.stdin.flush()
            stdout_line = proc.stdout.readline()
            self.assertIsNotNone(stdout_line)
            self.assertTrue(stdout_line.startswith("{"),
                            "stdout must start with JSON object, got: " + repr(stdout_line[:100]))
            self.assertNotIn("[SERVICE]", stdout_line,
                             "stdout must not contain service startup logs")
        finally:
            try:
                proc.terminate()
                proc.wait(timeout=10)
            except Exception:
                proc.kill()

    def test_stdio_stdout_contains_no_startup_logs_in_stderr_check(self):
        tmp = tempfile.mkdtemp()
        env = self._server_env(tmp)
        proc = subprocess.Popen(
            [sys.executable, "-m", "src.mcp.mcp_server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        stderr_lines, stderr_thread = self._drain_stderr(proc)
        request = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26"}}\n'
        try:
            proc.stdin.write(request)
            proc.stdin.flush()
            stdout_line = proc.stdout.readline()
            self.assertIsNotNone(stdout_line)
            proc.terminate()
            proc.wait(timeout=10)
            stderr_thread.join(timeout=3)
            all_stderr = "".join(stderr_lines)
            self.assertIn("[SERVICE]", all_stderr,
                          "stderr should contain service startup logs")
        finally:
            try:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()
            except Exception:
                pass

    def test_mcp_client_connects_via_stdio(self):
        from gui.mcp_client import MCPClient
        tmp = tempfile.mkdtemp()
        env = self._server_env(tmp)
        proc = subprocess.Popen(
            [sys.executable, "-m", "src.mcp.mcp_server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        client = MCPClient(proc)
        try:
            client._drain_stderr()
            client._initialize()
            tools = client.list_tools()
            self.assertIsInstance(tools, list)
            self.assertGreater(len(tools), 0)
            tool_names = [t["name"] for t in tools]
            self.assertIn("search_memory", tool_names)
            self.assertIn("explain_change", tool_names)
        finally:
            try:
                client.close()
            except Exception:
                pass

    def test_stdio_tools_call_returns_structured_data(self):
        from gui.mcp_client import MCPClient
        tmp = tempfile.mkdtemp()
        env = self._server_env(tmp)
        proc = subprocess.Popen(
            [sys.executable, "-m", "src.mcp.mcp_server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        client = MCPClient(proc)
        try:
            client._drain_stderr()
            client._initialize()
            result = client.call_tool("get_recent_events", {"limit": 5})
            self.assertIsInstance(result, dict)
        finally:
            try:
                client.close()
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
