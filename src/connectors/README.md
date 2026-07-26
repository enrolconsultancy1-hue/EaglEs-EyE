# Connector Framework — Developer Guide

EaglEs EyE's Connector Framework is the only approved mechanism for external
integrations. Every connector must use this framework — no connector may bypass
it.

## Quick Start

```python
from connectors.sdk import register_connector_cls
from connectors.registry import ConnectorRegistry
from connectors.connector import Connector

class MyConnector(Connector):
    id = "my_connector"
    name = "My Connector"
    version = "1.0.0"
    vendor = "My Company"
    description = "Connects to my service"
    capabilities = ["api", "documents"]
    permissions = ["read", "observe"]

    def connect(self):
        # Establish connection
        return True

    def disconnect(self):
        # Tear down connection
        return True

    def discover(self):
        return []

    def observe(self):
        return []

    def collect(self):
        return []

registry = ConnectorRegistry()
register_connector_cls(MyConnector, registry)
```

## Connector Manifest

Connectors declare metadata in a manifest file (`connector.yaml` or
`connector.json`):

```yaml
connector_id: my_connector
name: My Connector
version: 1.0.0
vendor: My Company
capabilities:
  - api
  - documents
permissions:
  - read
  - observe
min_eye_version: 2.2.0
entry_point: my_package.my_module
```

Manifests are placed in `connectors/plugins/` for automatic discovery at
startup.

## Standard Interface

Every connector exposes these methods:

| Method | Purpose |
|--------|---------|
| `connect()` | Establish connection to the target system |
| `disconnect()` | Tear down the connection |
| `start()` | Initialize and begin operation |
| `stop()` | Halt operation |
| `discover()` | Enumerate available sources |
| `observe()` | Collect observations from the target |
| `collect()` | Gather evidence from observations |
| `normalize()` | Convert raw data to canonical format |
| `emit()` | Submit evidence to the pipeline |
| `health()` | Report connector health |
| `heartbeat()` | Send keepalive signal |
| `status()` | Return full connector status |

## Normalization Pipeline

Every connector follows this pipeline:

```
Observe
  ↓
Collect
  ↓
Normalize
  ↓
Validate
  ↓
Emit
  ↓
Knowledge Graph
  ↓
Reasoning
```

No connector may inject data directly into the knowledge graph or reasoning
systems.

## Evidence Model

The canonical evidence format includes:

- Observation — raw observation from a source
- Evidence — normalized, validated observation ready for the pipeline
- Artifact — associated file, document, or data payload
- Source — origin system or location
- Identity — user, agent, or system identifier
- Timestamp — time of observation with source tracking
- Confidence — certainty score with method attribution
- RawPayload — unprocessed data
- NormalizedPayload — pipeline-ready structured data
- TraceInformation — pipeline provenance
- CitationInformation — evidence source references

## Capabilities

Standard capabilities: filesystem, git, tasks, commits, issues, documents,
chat, email, calendar, mcp, api, database, terminal, logs, artifacts,
knowledge.

## Permissions

Standard permissions: read, write, observe, execute, reason, mirror, sync.

## Connector States

Each connector transitions through: disconnected, connected, starting, running,
paused, error, stopped. State transitions are validated; invalid transitions
raise ConnectorStateError.

## Health Monitoring

Connectors report health metrics including state, last heartbeat, last
observation, error history, uptime, and started-at timestamp.

## Dynamic Loading

Drop a connector manifest (`connector.yaml`) and its Python module into
`connectors/plugins/`. The framework discovers, validates, loads, and registers
it automatically at startup — no kernel code changes required.
