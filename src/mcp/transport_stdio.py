"""MCP stdio transport — line-delimited JSON-RPC 2.0 over stdin/stdout."""

import sys
import json


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
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()
