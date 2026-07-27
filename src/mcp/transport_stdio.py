"""MCP stdio transport — line-delimited JSON-RPC 2.0 over stdin/stdout."""

import sys
import json

# Capture real stdout at import time.  The MCP server redirects
# sys.stdout → sys.stderr so that EventBus.publish() and other
# print() calls don't corrupt the JSON-RPC protocol pipe.
_PROTOCOL_STDOUT = sys.stdout


def read_message():
    line = sys.stdin.readline()
    if not line:
        return None
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError as e:
        return {"error": {"code": -32700, "message": "Parse error: " + str(e)}}


def write_message(msg):
    stream = sys.stdout
    if stream is sys.stderr:
        stream = _PROTOCOL_STDOUT  # MCP server redirected stdout → stderr
    stream.write(json.dumps(msg) + "\n")
    stream.flush()
