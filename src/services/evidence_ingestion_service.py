"""EvidenceIngestionService — transforms connector Evidence into KnowledgeStore records.

This service subscribes to the EvidenceBus and converts connector Evidence objects
into events, observations, and relationships in the KnowledgeStore. It is the
bridge that completes the connector evidence pipeline:

Connector → Observe → Collect → Normalize → EvidenceBus → Ingestion → Knowledge Store
"""

import time
import json

from services.service import Service


class EvidenceIngestionService(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self._store = None
        self._connector = None
        self._evidence_bus = None
        self._ingested_count = 0

    def start(self):
        super().start()
        self._store = self.kernel.get_service("KnowledgeStoreService")
        if not self._store:
            raise RuntimeError("EvidenceIngestionService requires KnowledgeStoreService.")
        self._connector = self.kernel.get_service("ConnectorService")
        if not self._connector:
            raise RuntimeError("EvidenceIngestionService requires ConnectorService.")
        manager = self._connector.get_manager()
        if manager:
            self._evidence_bus = EvidenceBusShim(manager)
            self._evidence_bus.subscribe(self._on_evidence)
        print("[EVIDENCE INGESTION] Ready.")

    def stop(self):
        if self._evidence_bus:
            self._evidence_bus.unsubscribe(self._on_evidence)
        super().stop()

    def _on_evidence(self, connector_id, evidence_list):
        for evidence in evidence_list:
            self._ingest_evidence(connector_id, evidence)

    def _ingest_evidence(self, connector_id, evidence):
        event_type = f"CONNECTOR_EVIDENCE:{connector_id}"
        path = getattr(evidence, "observation_id", "") or connector_id
        payload = self._evidence_to_payload(connector_id, evidence)
        self._store.record_event(event_type, path, payload)
        self._ingested_count += 1

    def ingest(self, connector_id, evidence_list):
        self._on_evidence(connector_id, evidence_list)
        return {"ingested": len(evidence_list), "total": self._ingested_count}

    @staticmethod
    def _evidence_to_payload(connector_id, evidence):
        payload = {
            "connector_id": connector_id,
            "evidence_id": getattr(evidence, "id", ""),
            "observation_id": getattr(evidence, "observation_id", ""),
            "confidence_score": getattr(evidence.confidence, "score", 1.0) if hasattr(evidence, "confidence") else 1.0,
            "trace": {
                "connector_version": getattr(evidence.trace, "connector_version", "") if hasattr(evidence, "trace") else "",
                "pipeline": getattr(evidence.trace, "pipeline", []) if hasattr(evidence, "trace") else [],
            } if hasattr(evidence, "trace") else {},
            "ingested_at": time.time(),
        }
        if hasattr(evidence, "normalized") and hasattr(evidence.normalized, "data"):
            payload["normalized_data"] = evidence.normalized.data
        if hasattr(evidence, "artifacts") and evidence.artifacts:
            payload["artifact_count"] = len(evidence.artifacts)
        if hasattr(evidence, "relationships") and evidence.relationships:
            payload["relationship_count"] = len(evidence.relationships)
        return payload

    def get_stats(self):
        return {"ingested_count": self._ingested_count}


class EvidenceBusShim:
    """Shim that bridges ConnectorManager events to the ingestion callback pattern."""

    def __init__(self, manager):
        self._manager = manager
        self._callbacks = []

    def subscribe(self, callback):
        self._callbacks.append(callback)

    def unsubscribe(self, callback):
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify(self, connector_id, evidence_list):
        for cb in self._callbacks:
            try:
                cb(connector_id, evidence_list)
            except Exception:
                pass
