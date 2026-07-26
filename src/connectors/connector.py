import time
from abc import ABC, abstractmethod
from typing import Optional

from connectors.health import ConnectorState, ConnectorHealth
from connectors.models import (
    Observation, Evidence, Source, RawPayload, NormalizedPayload,
    TraceInformation, CitationInformation, Artifact,
)
from connectors.exceptions import ConnectorStateError


class Connector(ABC):
    id: str = ""
    name: str = ""
    version: str = "0.1.0"
    vendor: str = ""
    description: str = ""
    capabilities: list = []
    permissions: list = []
    manifest = None

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self._health = ConnectorHealth()
        self._event_bus = None

    # --- Lifecycle ---

    @abstractmethod
    def connect(self) -> bool:
        ...

    @abstractmethod
    def disconnect(self) -> bool:
        ...

    def start(self) -> bool:
        if not self._health.state.can_transition_to(ConnectorState.STARTING):
            raise ConnectorStateError(
                f"Cannot start from state {self._health.state.value}"
            )
        self._health.state = ConnectorState.STARTING
        if not self.connect():
            self._health.state = ConnectorState.ERROR
            return False
        self._health.start()
        self._publish_event("CONNECTOR_STARTED")
        return True

    def stop(self) -> bool:
        if not self._health.state.can_transition_to(ConnectorState.STOPPED):
            return False
        self.disconnect()
        self._health.stop()
        self._publish_event("CONNECTOR_STOPPED")
        return True

    # --- Universal Observation Policy ---

    @abstractmethod
    def discover_observation_surfaces(self) -> list:
        ...

    @abstractmethod
    def rank_observation_surfaces(self) -> list:
        ...

    @abstractmethod
    def select_observation_pipeline(self) -> list:
        ...

    def get_active_surfaces(self) -> list:
        return self.select_observation_pipeline()

    def build_observation_pipeline(self) -> list:
        ranked = self.rank_observation_surfaces()
        return self.select_observation_pipeline()

    # --- Data pipeline ---

    @abstractmethod
    def discover(self) -> list:
        ...

    @abstractmethod
    def observe(self) -> list:
        ...

    @abstractmethod
    def collect(self) -> list:
        ...

    def normalize(self, raw: RawPayload) -> NormalizedPayload:
        return NormalizedPayload.structured({"raw": raw.data})

    def validate_evidence(self, evidence: Evidence) -> bool:
        return bool(evidence.id and evidence.observation_id)

    def emit(self, evidence: Evidence) -> bool:
        if not self.validate_evidence(evidence):
            return False
        self._health.record_observation()
        self._publish_event("CONNECTOR_EVIDENCE", evidence)
        return True

    # --- Health ---

    def health(self) -> ConnectorHealth:
        return self._health

    def heartbeat(self) -> bool:
        self._health.record_heartbeat()
        return True

    def status(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "vendor": self.vendor,
            "state": self._health.state.value,
            "capabilities": list(self.capabilities),
            "permissions": list(self.permissions),
            "health": self._health.to_dict(),
        }

    # --- Internal ---

    def _publish_event(self, event_type: str, payload=None):
        if self._event_bus:
            from connectors.events import ConnectorEventData
            data = ConnectorEventData(
                connector_id=self.id,
                event_type=event_type,
                payload=payload,
            )
            self._event_bus.publish(event_type, data)
