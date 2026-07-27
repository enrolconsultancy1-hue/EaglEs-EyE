# EaglEs EyE Local Startup Guide

## Requirements

| Requirement | Version |
|---|---|
| **Python** | 3.12+ (tested on 3.14) |
| **Operating System** | Windows, macOS, Linux |
| **Dependencies** | See `requirements.txt` |

## First-Time Setup

```powershell
# 1. Clone the repository
git clone https://github.com/anomalyco/EaglEs-EyE.git
cd EaglEs-EyE

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate the virtual environment
# Windows:
.venv\Scripts\Activate.ps1
# macOS / Linux:
# source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

> **Note:** EaglEs EyE uses only the Python standard library plus `watchdog`.
> No web frameworks (Flask, FastAPI), no databases (beyond SQLite), and no
> external AI APIs are required.

## Starting EaglEs EyE

### GUI Mode (recommended for humans)

```powershell
# From the repository root:
python -m gui.app
```

The GUI automatically:
1. Starts the EyeKernel and all 35 services in a child process
2. Opens your default browser to `http://127.0.0.1:9103`

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `EAGLE_EYE_MEMORY_PATH` | Auto-created temp dir | Where knowledge and twin data persist |
| `GUI_HOST` | `127.0.0.1` | HTTP server bind address |
| `GUI_PORT` | `9103` | HTTP server port |
| `GUI_OPEN_BROWSER` | `1` | Auto-open browser (`0` to disable) |

Example with custom memory path:
```powershell
$env:EAGLE_EYE_MEMORY_PATH = "C:\Users\me\eye-data"
python -m gui.app
```

### MCP Server Mode (for AI agents / CLI)

```powershell
$env:EAGLE_EYE_MEMORY_PATH = "C:\Users\me\eye-data"
python -m src.mcp.mcp_server
```

This runs the JSON-RPC 2.0 MCP server over stdio. Compatible with any
MCP client (Cursor, Claude Desktop, Windsurf, custom scripts).

## Successful Startup Output

When starting in GUI mode you should see output like:

```
[GUI] Mission Control ready at http://127.0.0.1:9103
```

The MCP server subprocess logs to stderr (not visible in the GUI terminal
by default). To see kernel startup logs, start the MCP server directly:

```
[KERNEL] Configuration loaded.
[KERNEL] Registered: KnowledgeStoreService
[SERVICE] KnowledgeStoreService started.
[KNOWLEDGE STORE] Ready: C:\Users\user\eye-data\knowledge.db
[KERNEL] Registered: SymbolIndexerService
[SERVICE] SymbolIndexerService started.
[SYMBOL INDEXER] Ready.
[KERNEL] Registered: KnowledgeGraphService
...
[KERNEL] Registered: ProjectTwinDiscoveryService
[SERVICE] ProjectTwinDiscoveryService started.
[KERNEL] Registered: MCPToolService
[SERVICE] MCPToolService started.
[MCP TOOLS] Ready.
[MCP] Server ready (stdio transport)
```

## Browser Access

Open your browser and navigate to:

```
http://127.0.0.1:9103
```

The Mission Control dashboard loads immediately. Nine navigation tabs are
available at the top:

| Tab | Purpose |
|---|---|
| **Dashboard** | Overview: active workspace, sessions, recent events |
| **Timeline** | Ordered event table with timestamps and citations |
| **AI Twin** | Project twin artifacts, sessions, decisions |
| **Search** | Full-text memory and symbol cross-reference |
| **Semantic** | Vector similarity search (if embeddings enabled) |
| **Graph** | Symbol relationships, dependencies, causal chains |
| **Explain** | Evidence-backed explanation engine |
| **Awareness** | Pattern detection and awareness signals |
| **Metrics** | Event counts, sessions, health, system info |
| **Help** | Getting started, Connect, Scan, Create Twin |

## Shutdown Procedure

### Graceful Shutdown (GUI Mode)

Press `Ctrl+C` in the terminal where `python -m gui.app` is running.
The HTTP server closes and the MCP child process terminates.

### Graceful Shutdown (MCP Server Mode)

Press `Ctrl+C` or send `SIGTERM`. Services stop in reverse registration
order, connections close, and data is flushed.

### Data Safety

All knowledge is stored in SQLite (`knowledge.db`) inside the memory path.
Twin JSON files are written atomically (write to `.tmp`, then `os.replace`).
It is safe to kill the process — no in-flight transaction will corrupt
previously written data.
