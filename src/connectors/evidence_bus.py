"""EvidenceBus — bridges connector Emit to the EvidenceIngestionService.

This is the integration point that completes the connector evidence pipeline:
Connector → Observe → Collect → Normalize → EvidenceBus → Ingestion → Knowledge Store.
"""

from connectors.events import CONNECTOR_EVIDENCE, CONNECTOR_OBSERVATION
from connectors.events import ConnectorEventData


class EvidenceBus:
    def __init__(self, event_bus=None):
        self._event_bus = event_bus
        self._subscribers = []

    def set_event_bus(self, event_bus):
        self._event_bus = event_bus

    def publish_evidence(self, connector_id, evidence_list):
        if not evidence_list:
            return
        data = {
            "connector_id": connector_id,
            "evidence_count": len(evidence_list),
            "evidence": evidence_list,
        }
        if self._event_bus:
            event_data = ConnectorEventData(
                connector_id=connector_id,
                event_type=CONNECTOR_EVIDENCE,
                payload=data,
            )
            self._event_bus.publish(CONNECTOR_EVIDENCE, event_data)
        for callback in self._subscribers:
            try:
                callback(connector_id, evidence_list)
            except Exception:
                pass

    def publish_observation(self, connector_id, observation_list):
        if not observation_list:
            return
        data = {
            "connector_id": connector_id,
            "observation_count": len(observation_list),
            "observations": observation_list,
        }
        if self._event_bus:
            event_data = ConnectorEventData(
                connector_id=connector_id,
                event_type=CONNECTOR_OBSERVATION,
                payload=data,
            )
            self._event_bus.publish(CONNECTOR_OBSERVATION, event_data)

    def subscribe(self, callback):
        self._subscribers.append(callback)

    def unsubscribe(self, callback):
        if callback in self._subscribers:
            self._subscribers.remove(callback)
