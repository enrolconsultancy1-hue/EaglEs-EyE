from connectors.connector import Connector
from connectors.health import ConnectorState
from connectors.models import (
    Source, RawPayload, Observation, Evidence, NormalizedPayload,
    Artifact, TraceInformation,
)
from connectors.observation_discovery import (
    ObservationSurface, ObservationDiscoveryEngine, SurfaceQuality,
    EvidenceQuality, LatencyClass, Completeness, Reliability,
)


class MockConnector(Connector):
    id = "mock"
    name = "Mock Connector"
    version = "1.0.0"
    vendor = "EaglEs EyE"
    description = "Reference connector for testing and development"
    capabilities = ["api", "knowledge"]
    permissions = ["read", "observe", "reason"]

    def __init__(self, config=None):
        super().__init__(config)
        self._observation_count = 0
        self._fail_connect = self.config.get("fail_connect", False)
        self._fail_observe = self.config.get("fail_observe", False)
        self._return_empty = self.config.get("return_empty", False)

    def connect(self) -> bool:
        if self._fail_connect:
            self._health.record_error("Connection refused (mock)")
            return False
        self._health.state = ConnectorState.CONNECTED
        return True

    def disconnect(self) -> bool:
        self._health.state = ConnectorState.DISCONNECTED
        return True

    def discover(self) -> list:
        return [
            Source.create(type_="mock", path="/mock/source/1"),
            Source.create(type_="mock", path="/mock/source/2"),
        ]

    def observe(self) -> list:
        if self._fail_observe:
            self._health.record_error("Observation failed (mock)")
            return []
        if self._return_empty:
            return []
        self._observation_count += 1
        raw = RawPayload.from_text(
            f"mock observation #{self._observation_count}"
        )
        source = Source.create(type_="mock", path="/mock/observation")
        observation = Observation.create(
            type_="mock_event", source=source, raw=raw,
        )
        return [observation]

    def collect(self) -> list:
        evidence_list = []
        observations = self.observe()
        for obs in observations:
            normalized = self.normalize(obs.raw)
            artifact = Artifact.create(
                type_="mock_artifact",
                content=obs.raw.data if hasattr(obs.raw, 'data') else str(obs.raw),
            )
            trace = TraceInformation(
                connector_id=self.id,
                connector_version=self.version,
                pipeline=["observe", "collect", "normalize", "emit"],
                duration_ms=0.0,
            )
            evidence = Evidence.create(
                observation=obs, normalized=normalized, trace=trace,
                artifacts=[artifact],
            )
            evidence_list.append(evidence)
        return evidence_list

    def normalize(self, raw: RawPayload):
        return NormalizedPayload.structured({
            "mock_data": raw.data,
            "connector": self.id,
        })

    def discover_observation_surfaces(self) -> list:
        return [ObservationSurface.OTHER]

    def rank_observation_surfaces(self) -> list:
        engine = ObservationDiscoveryEngine()
        surfaces = self.discover_observation_surfaces()
        qualities = {
            ObservationSurface.OTHER: SurfaceQuality(
                surface=ObservationSurface.OTHER,
                quality=EvidenceQuality.MEDIUM,
                latency=LatencyClass.BATCH,
                completeness=Completeness.PARTIAL,
                reliability=Reliability.MEDIUM,
                supports_incremental_sync=False,
                authentication_required="none",
                description="Mock test data source",
            ),
        }
        return engine.rank_surfaces(surfaces, qualities)

    def select_observation_pipeline(self) -> list:
        engine = ObservationDiscoveryEngine()
        ranked = self.rank_observation_surfaces()
        return engine.select_pipeline(ranked)
