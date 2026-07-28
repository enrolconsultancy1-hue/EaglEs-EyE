"""MCP JSON-RPC 2.0 client — connects to MCP server via stdio subprocess.

Timeout protection added to prevent the GUI from hanging indefinitely.
When an MCP call exceeds the timeout, the subprocess is killed and a
clear RuntimeError is raised so the GUI can display the failure reason.
"""

import json
import os
import queue
import subprocess
import sys
import threading


_RW_TIMEOUT = 180  # seconds; generous for first-time discovery


def _diagnose_response(raw_line, tool_name=""):
    """Return a human-readable diagnostic for a non-JSON MCP response."""
    if not raw_line:
        return "Empty response (MCP server closed connection)"
    clean = raw_line.strip()
    if not clean:
        return "Blank line received (stripped to empty)"
    preview = clean[:200]
    hex_preview = " ".join("%02x" % ord(c) for c in clean[:40])
    return (
        "Invalid JSON response for tool '%s': %r\n"
        "  First 200 chars: %s\n"
        "  Hex of first 40 chars: %s"
    ) % (tool_name, preview, preview, hex_preview)


class MCPClient:
    def __init__(self, process=None):
        self._proc = process
        self._request_id = 0
        self._stderr_thread = None
        self._stderr_lines = []

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def get_stderr_logs(self, last_n=200):
        """Return the *last_n* lines of MCP server stderr as a single string."""
        return "".join(self._stderr_lines[-last_n:])

    # ------------------------------------------------------------------
    # Life-cycle
    # ------------------------------------------------------------------
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
        stash = self._stderr_lines

        def _reader():
            try:
                for line in iter(self._proc.stderr.readline, ""):
                    stash.append(line)
            except ValueError:
                pass

        self._stderr_thread = threading.Thread(target=_reader, daemon=True)
        self._stderr_thread.start()

    # ------------------------------------------------------------------
    # JSON-RPC send with timeout
    # ------------------------------------------------------------------
    def _next_id(self):
        self._request_id += 1
        return self._request_id

    def _send(self, method, params=None, timeout=_RW_TIMEOUT):
        msg_id = self._next_id()
        request = {"jsonrpc": "2.0", "id": msg_id, "method": method}
        if params is not None:
            request["params"] = params
        self._proc.stdin.write(json.dumps(request) + "\n")
        self._proc.stdin.flush()

        # Read response in a daemon thread so we can timeout
        result_queue = queue.Queue()

        def _reader():
            try:
                line = self._proc.stdout.readline()
                result_queue.put(line)
            except Exception as exc:
                result_queue.put(exc)

        t = threading.Thread(target=_reader, daemon=True)
        t.start()

        try:
            raw = result_queue.get(timeout=timeout)
        except queue.Empty:
            # Timed out — kill the subprocess and raise
            self._proc.kill()
            logs = self.get_stderr_logs(50)
            raise RuntimeError(
                "MCP server did not respond within %d s for '%s'.\n"
                "Last stderr lines:\n%s" % (timeout, method, logs)
            )

        if isinstance(raw, Exception):
            raise RuntimeError("MCP read error for '%s': %s" % (method, raw))

        response = raw
        if not response:
            logs = self.get_stderr_logs(50)
            raise RuntimeError(
                "MCP server closed connection during '%s'.\n"
                "Last stderr lines:\n%s" % (method, logs)
            )
        try:
            data = json.loads(response.strip())
        except json.JSONDecodeError:
            diag = _diagnose_response(response, method)
            print("[MCP CLIENT] " + diag, file=sys.stderr)
            raise RuntimeError(
                "MCP server returned invalid JSON for '%s'. "
                "See server stderr for details." % method
            )
        if "error" in data:
            raise RuntimeError(
                "MCP error (%d): %s" % (data["error"]["code"], data["error"]["message"])
            )
        content = data.get("result", {}).get("content", [])
        for item in content:
            if item.get("type") == "text":
                return json.loads(item["text"])
        return data.get("result")

    def _initialize(self, timeout=60):
        """Short timeout for init — the MCP server builds its kernel here."""
        self._send("initialize", {"protocolVersion": "2025-03-26"}, timeout=timeout)

    def list_tools(self):
        result = self._send("tools/list")
        return result.get("tools", [])

    def call_tool(self, name, arguments=None, timeout=_RW_TIMEOUT):
        return self._send(
            "tools/call",
            {"name": name, "arguments": arguments or {}},
            timeout=timeout,
        )

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
