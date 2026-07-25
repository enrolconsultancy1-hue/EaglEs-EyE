"""Lightweight tool registry with schema metadata for MCP tool exposure."""

import inspect


class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, name, fn, input_schema, description=""):
        self._tools[name] = {
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "fn": fn,
        }

    def list_tools(self):
        return [
            {"name": t["name"], "description": t["description"], "inputSchema": t["input_schema"]}
            for t in self._tools.values()
        ]

    def call_tool(self, name, arguments):
        tool = self._tools.get(name)
        if not tool:
            return {"error": "Unknown tool: " + str(name), "code": -32601}
        try:
            result = tool["fn"](**(arguments or {}))
            return result
        except TypeError as e:
            return {"error": "Invalid arguments: " + str(e), "code": -32602}
        except Exception as e:
            return {"error": str(e), "code": -32603}
