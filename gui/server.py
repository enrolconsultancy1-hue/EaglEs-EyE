"""GUI web server — serves Mission Control dashboard UI and proxies MCP API calls."""

import json
import os
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from gui.mcp_client import MCPClient


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
