import time
from typing import Optional

from connectors.connector import Connector
from connectors.manifest import ConnectorManifest
from connectors.models import (
    Observation, Evidence, Source, RawPayload, NormalizedPayload,
    Artifact, TraceInformation, Timestamp,
)
from connectors.exceptions import ConnectorCapabilityError, ConnectorPermissionError


class ConnectorSDK:
    @staticmethod
    def create_observation(connector: Connector, type_: str,
                           source: Source, raw: RawPayload,
                           metadata: dict = None) -> Observation:
        return Observation.create(
            type_=type_, source=source, raw=raw, metadata=metadata,
        )

    @staticmethod
    def create_evidence(connector: Connector,
                        observation: Observation,
                        normalized: NormalizedPayload,
                        artifacts: list = None,
                        trace: TraceInformation = None) -> Evidence:
        if trace is None:
            trace = TraceInformation(
                connector_id=connector.id,
                connector_version=connector.version,
                pipeline=["observe", "collect", "normalize", "emit"],
                duration_ms=0.0,
            )
        return Evidence.create(
            observation=observation,
            normalized=normalized,
            trace=trace,
            artifacts=artifacts,
        )

    @staticmethod
    def run_pipeline(connector: Connector) -> list[Evidence]:
        all_evidence = []
        observations = connector.observe()
        for obs in observations:
            collected = connector.collect() if hasattr(connector, 'collect') else []
            items = collected if collected else [obs]
            for item in items:
                raw = item if isinstance(item, RawPayload) else getattr(item, 'raw', RawPayload.from_dict({}))
                normalized = connector.normalize(raw)
                observation = obs if isinstance(item, RawPayload) else item
                if not isinstance(observation, Observation):
                    observation = Observation.create(
                        type_="generic", source=Source.create("unknown"),
                        raw=raw,
                    )
                trace = TraceInformation(
                    connector_id=connector.id,
                    connector_version=connector.version,
                    pipeline=["observe", "collect", "normalize", "emit"],
                    duration_ms=0.0,
                )
                evidence = Evidence.create(
                    observation=observation, normalized=normalized, trace=trace,
                )
                if connector.validate_evidence(evidence):
                    connector.emit(evidence)
                    all_evidence.append(evidence)
        return all_evidence

    @staticmethod
    def require_capability(connector: Connector, capability: str):
        if capability not in connector.capabilities:
            raise ConnectorCapabilityError(
                f"Connector '{connector.id}' does not support capability: {capability}"
            )

    @staticmethod
    def require_permission(connector: Connector, permission: str):
        if permission not in connector.permissions:
            raise ConnectorPermissionError(
                f"Connector '{connector.id}' does not have permission: {permission}"
            )


def register_connector_cls(connector_cls, registry, config: dict = None,
                           manifest: ConnectorManifest = None) -> str:
    instance = connector_cls(config=config)
    return registry.register(instance, manifest=manifest)
