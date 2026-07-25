"""Mission Control entry point — boots kernel, MCP server, and desktop GUI."""

import os
import sys
import threading
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gui.mcp_client import MCPClient
from gui.server import run_gui_server


def start_mcp_server_process(memory_path=None):
    args = [sys.executable, "-m", "mcp.mcp_server"]
    if memory_path:
        env = os.environ.copy()
        env["EAGLE_EYE_MEMORY_PATH"] = memory_path
        proc_env = env
    else:
        proc_env = os.environ.copy()
    return MCPClient.connect_stdio(args)


def main():
    memory_path = os.environ.get("EAGLE_EYE_MEMORY_PATH")
    if not memory_path:
        memory_path = tempfile.mkdtemp(prefix="eye_gui_")
    client = start_mcp_server_process(memory_path)
    host = os.environ.get("GUI_HOST", "127.0.0.1")
    port = int(os.environ.get("GUI_PORT", "9103"))
    open_browser = os.environ.get("GUI_OPEN_BROWSER", "1") == "1"
    try:
        run_gui_server(host=host, port=port, mcp_client=client, open_browser=open_browser)
    finally:
        client.close()


if __name__ == "__main__":
    main()
