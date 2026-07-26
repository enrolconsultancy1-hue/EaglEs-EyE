import time
import enum
from dataclasses import dataclass, field
from typing import Optional


class ConnectorState(enum.Enum):
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"

    def is_active(self) -> bool:
        return self in (ConnectorState.RUNNING, ConnectorState.CONNECTED)

    def can_transition_to(self, target: "ConnectorState") -> bool:
        valid = {
            ConnectorState.DISCONNECTED: {ConnectorState.CONNECTED, ConnectorState.STARTING, ConnectorState.STOPPED},
            ConnectorState.CONNECTED: {ConnectorState.DISCONNECTED, ConnectorState.RUNNING, ConnectorState.STARTING},
            ConnectorState.STARTING: {ConnectorState.RUNNING, ConnectorState.ERROR, ConnectorState.STOPPED},
            ConnectorState.RUNNING: {ConnectorState.PAUSED, ConnectorState.STOPPED, ConnectorState.ERROR, ConnectorState.DISCONNECTED},
            ConnectorState.PAUSED: {ConnectorState.RUNNING, ConnectorState.STOPPED, ConnectorState.DISCONNECTED},
            ConnectorState.ERROR: {ConnectorState.DISCONNECTED, ConnectorState.STOPPED, ConnectorState.STARTING},
            ConnectorState.STOPPED: {ConnectorState.DISCONNECTED, ConnectorState.STARTING},
        }
        return target in valid.get(self, set())


@dataclass
class ConnectorHealth:
    state: ConnectorState = ConnectorState.DISCONNECTED
    last_heartbeat: float = 0.0
    last_observation: float = 0.0
    errors: list = field(default_factory=list)
    uptime: float = 0.0
    started_at: Optional[float] = None

    def record_heartbeat(self):
        self.last_heartbeat = time.time()
        if self.state == ConnectorState.DISCONNECTED:
            self.state = ConnectorState.CONNECTED

    def record_observation(self):
        self.last_observation = time.time()

    def record_error(self, error: str):
        self.errors.append(error)
        self.state = ConnectorState.ERROR

    def start(self):
        self.started_at = time.time()
        self.state = ConnectorState.RUNNING
        self.record_heartbeat()

    def stop(self):
        if self.started_at:
            self.uptime += time.time() - self.started_at
        self.started_at = None
        self.state = ConnectorState.STOPPED

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "last_heartbeat": self.last_heartbeat,
            "last_observation": self.last_observation,
            "errors": self.errors[-5:] if self.errors else [],
            "uptime": self.uptime + (time.time() - self.started_at if self.started_at else 0),
            "started_at": self.started_at,
        }
