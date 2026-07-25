"""MCP JSON-RPC 2.0 client — connects to MCP server via stdio subprocess."""

import json
import os
import subprocess
import sys
import threading


class MCPClient:
    def __init__(self, process=None):
        self._proc = process
        self._request_id = 0
        self._stderr_thread = None

    @classmethod
    def connect_stdio(cls, args=None, extra_env=None):
        if args is None:
            args = [sys.executable, "-m", "src.mcp.mcp_server"]
        env = os.environ.copy()
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env["PYTHONPATH"] = os.path.join(project_root, "src")
        if extra_env:
            env.update(extra_env)
        proc = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        client = cls(proc)
        client._drain_stderr()
        client._initialize()
        return client

    def _drain_stderr(self):
        stderr_lines = []

        def _reader():
            try:
                for line in iter(self._proc.stderr.readline, ""):
                    stderr_lines.append(line)
            except ValueError:
                pass

        self._stderr_thread = threading.Thread(target=_reader, daemon=True)
        self._stderr_thread.start()

    def _next_id(self):
        self._request_id += 1
        return self._request_id

    def _send(self, method, params=None):
        msg_id = self._next_id()
        request = {"jsonrpc": "2.0", "id": msg_id, "method": method}
        if params is not None:
            request["params"] = params
        self._proc.stdin.write(json.dumps(request) + "\n")
        self._proc.stdin.flush()
        response = self._proc.stdout.readline()
        if not response:
            raise ConnectionError("MCP server closed connection")
        data = json.loads(response.strip())
        if "error" in data:
            raise RuntimeError("MCP error (%d): %s" % (data["error"]["code"], data["error"]["message"]))
        content = data.get("result", {}).get("content", [])
        for item in content:
            if item.get("type") == "text":
                return json.loads(item["text"])
        return data.get("result")

    def _initialize(self):
        self._send("initialize", {"protocolVersion": "2025-03-26"})

    def list_tools(self):
        result = self._send("tools/list")
        return result.get("tools", [])

    def call_tool(self, name, arguments=None):
        return self._send("tools/call", {"name": name, "arguments": arguments or {}})

    def close(self):
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
