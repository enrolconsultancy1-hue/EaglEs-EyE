"""GUI web server — serves Mission Control dashboard UI and proxies MCP API calls."""

import json
import os
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from gui.mcp_client import MCPClient


# Lazy import of reasoning to avoid circular deps at module level
_reasoner_instance = None

def _get_reasoner():
    global _reasoner_instance
    if _reasoner_instance is None:
        from services.twin_reasoning_service import TwinReasoningService
        _reasoner_instance = TwinReasoningService(None)
    return _reasoner_instance


def _load_twin_evolution(project_path):
    """Load twin evolution data from the project's twin history and versions."""
    import hashlib
    project_name = os.path.basename(os.path.normpath(project_path))
    twins_base = os.path.join("memory", "twins")
    history_path = os.path.join(twins_base, project_name, "history.json")
    if not os.path.isfile(history_path):
        return {"error": f"No twin history found for {project_name}. Discover the project first."}

    with open(history_path, encoding="utf-8") as f:
        history = json.load(f)

    versions = history.get("versions", [])
    versions_dir = os.path.join(twins_base, project_name, "versions")

    # Load all versioned twins
    twin_cache = {}
    for v in versions:
        v_num = v["version"]
        v_path = os.path.join(versions_dir, f"v{v_num}.json")
        if os.path.isfile(v_path):
            with open(v_path, encoding="utf-8") as f:
                twin_cache[v_num] = json.load(f)

    # Build comparisons between consecutive versions
    comparisons = []
    for i in range(1, len(versions)):
        old_twin = twin_cache.get(i)
        new_twin = twin_cache.get(i + 1)
        if new_twin is None:
            continue
        comp = _compare_twin_snapshots(old_twin, new_twin)
        comp["from_version"] = i
        comp["to_version"] = i + 1
        comparisons.append(comp)

    # Build reasoning for each comparison
    reasoner = _get_reasoner()
    insights = reasoner.generate_evolution_insights(comparisons, versions)

    return {
        "project_name": project_name,
        "versions": versions,
        "comparisons": comparisons,
        "insights": insights,
    }


def _compare_twin_snapshots(old_twin, new_twin):
    """Minimal twin comparison for the server endpoint."""
    result = {
        "has_changes": False,
        "summary": [],
        "new_files": [],
        "removed_files": [],
        "changed_dependencies": {"added": [], "removed": []},
        "changed_frameworks": {"added": [], "removed": []},
        "documentation_changes": {"added": [], "removed": []},
        "classification_changed": False,
        "purpose_changed": False,
    }
    if old_twin is None:
        result["summary"].append("Initial scan")
        return result

    def _extract_paths(twin):
        paths = set()
        for doc in twin.get("documentation", {}).get("files", []):
            p = doc.get("path", "")
            if p: paths.add(p)
        for cfg in twin.get("config_files", {}).get("files", []):
            p = cfg.get("path", "")
            if p: paths.add(p)
        return paths

    old_files = _extract_paths(old_twin)
    new_files = _extract_paths(new_twin)
    result["new_files"] = sorted(new_files - old_files)
    result["removed_files"] = sorted(old_files - new_files)
    if result["new_files"]:
        result["summary"].append(f"{len(result['new_files'])} new file(s)")
    if result["removed_files"]:
        result["summary"].append(f"{len(result['removed_files'])} removed file(s)")

    old_deps = set(old_twin.get("dependencies", []))
    new_deps = set(new_twin.get("dependencies", []))
    result["changed_dependencies"]["added"] = sorted(new_deps - old_deps)
    result["changed_dependencies"]["removed"] = sorted(old_deps - new_deps)
    if result["changed_dependencies"]["added"]:
        result["summary"].append("New dependencies")
    if result["changed_dependencies"]["removed"]:
        result["summary"].append("Removed dependencies")

    old_fws = set(old_twin.get("project", {}).get("frameworks", []))
    new_fws = set(new_twin.get("project", {}).get("frameworks", []))
    result["changed_frameworks"]["added"] = sorted(new_fws - old_fws)
    result["changed_frameworks"]["removed"] = sorted(old_fws - new_fws)
    if result["changed_frameworks"]["added"]:
        result["summary"].append("New frameworks")
    if result["changed_frameworks"]["removed"]:
        result["summary"].append("Removed frameworks")

    old_cls = old_twin.get("project", {}).get("classification", {})
    new_cls = new_twin.get("project", {}).get("classification", {})
    if old_cls.get("domain") != new_cls.get("domain"):
        result["classification_changed"] = True
        result["summary"].append("Domain classification changed")

    old_purpose = old_twin.get("purpose_clues", {}).get("summary", "")
    new_purpose = new_twin.get("purpose_clues", {}).get("summary", "")
    if old_purpose != new_purpose:
        result["purpose_changed"] = True
        result["summary"].append("Project purpose changed")

    old_arch = old_twin.get("documentation_categories", {}).get("architecture", [])
    new_arch = new_twin.get("documentation_categories", {}).get("architecture", [])
    if old_arch != new_arch:
        result["summary"].append("Architecture documentation changed")

    result["has_changes"] = bool(
        result["new_files"] or result["removed_files"]
        or result["changed_dependencies"]["added"] or result["changed_dependencies"]["removed"]
        or result["changed_frameworks"]["added"] or result["changed_frameworks"]["removed"]
        or result["classification_changed"] or result["purpose_changed"]
    )
    return result


TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}


class GUIRequestHandler(BaseHTTPRequestHandler):
    mcp = None

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path.startswith("/api/"):
            self._handle_api(parsed)
        elif path == "/":
            self._serve_template("dashboard.html")
        else:
            name = path.lstrip("/")
            template_path = os.path.join(TEMPLATES_DIR, name)
            if os.path.isfile(template_path):
                self._serve_template(name)
            else:
                static_path = os.path.join(STATIC_DIR, name)
                if os.path.isfile(static_path):
                    self._serve_static(static_path)
                else:
                    self.send_error(404, "Not found")

    def do_POST(self):
        if self.path == "/api/call":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self._json_response({"error": "Invalid JSON"}, 400)
                return
            tool = data.get("tool", "")
            arguments = data.get("arguments", {})
            try:
                result = self.mcp.call_tool(tool, arguments)
                self._json_response(result)
            except RuntimeError as e:
                self._json_response({"error": str(e)}, 500)
            except Exception as e:
                self._json_response({"error": "Unexpected error: %s" % e}, 500)
        else:
            self.send_error(404)

    def _handle_api(self, parsed):
        qs = parse_qs(parsed.query)
        if parsed.path == "/api/tools":
            tools = self.mcp.list_tools()
            self._json_response({"tools": tools})
        elif parsed.path == "/api/dashboard":
            recent = self.mcp.call_tool("get_recent_events", {"limit": 20})
            self._json_response({"recent_events": recent.get("events", [])})
        elif parsed.path == "/api/mcp_logs":
            logs = self.mcp.get_stderr_logs()
            self._json_response({"logs": logs})
        elif parsed.path == "/api/twin_evolution":
            project_path = qs.get("project_path", [""])[0]
            if not project_path:
                self._json_response({"error": "Missing project_path parameter"}, 400)
                return
            data = _load_twin_evolution(project_path)
            self._json_response(data)
        else:
            self.send_error(404)

    def _serve_template(self, name):
        path = os.path.join(TEMPLATES_DIR, name)
        if not os.path.isfile(path):
            self.send_error(404)
            return
        content = open(path, "rb").read()
        self.send_response(200)
        ext = os.path.splitext(name)[1]
        self.send_header("Content-Type", MIME_TYPES.get(ext, "text/html"))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _serve_static(self, path):
        content = open(path, "rb").read()
        self.send_response(200)
        ext = os.path.splitext(path)[1]
        self.send_header("Content-Type", MIME_TYPES.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _json_response(self, data, status=200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def run_gui_server(host="127.0.0.1", port=9103, mcp_client=None, open_browser=True):
    GUIRequestHandler.mcp = mcp_client
    server = HTTPServer((host, port), GUIRequestHandler)
    print("[GUI] Mission Control ready at http://%s:%d" % (host, port))
    if open_browser:
        webbrowser.open("http://%s:%d" % (host, port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    client = MCPClient.connect_stdio()
    try:
        run_gui_server(mcp_client=client)
    finally:
        client.close()
