"""ObservationDiscoveryEngine — reusable surface discovery, ranking, and pipeline selection.

Universal Observation Policy:
Every connector discovers every available authorized observation surface for
the target platform before selecting how to observe it, then automatically
constructs the richest evidence pipeline available.
"""

import enum
from dataclasses import dataclass, field
from typing import Optional


class ObservationSurface(enum.Enum):
    NATIVE_CONNECTOR = "native_connector"
    MCP_SERVER = "mcp_server"
    EXTENSION_SDK = "extension_sdk"
    OFFICIAL_API = "official_api"
    WEBHOOK = "webhook"
    EVENT_STREAM = "event_stream"
    LOCAL_WORKSPACE = "local_workspace"
    GIT_REPOSITORY = "git_repository"
    PROJECT_FILES = "project_files"
    BUILD_ARTIFACTS = "build_artifacts"
    CONFIG_FILES = "config_files"
    LOGS = "logs"
    LOCAL_DATABASE = "local_database"
    OTHER = "other"


SURFACE_PREFERENCE_ORDER = [
    ObservationSurface.NATIVE_CONNECTOR,
    ObservationSurface.MCP_SERVER,
    ObservationSurface.EXTENSION_SDK,
    ObservationSurface.OFFICIAL_API,
    ObservationSurface.WEBHOOK,
    ObservationSurface.EVENT_STREAM,
    ObservationSurface.LOCAL_WORKSPACE,
    ObservationSurface.GIT_REPOSITORY,
    ObservationSurface.PROJECT_FILES,
    ObservationSurface.BUILD_ARTIFACTS,
    ObservationSurface.CONFIG_FILES,
    ObservationSurface.LOGS,
    ObservationSurface.LOCAL_DATABASE,
    ObservationSurface.OTHER,
]


class EvidenceQuality(enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class LatencyClass(enum.Enum):
    REALTIME = "realtime"
    NEAR_REALTIME = "near_realtime"
    BATCH = "batch"


class Completeness(enum.Enum):
    FULL = "full"
    PARTIAL = "partial"
    MINIMAL = "minimal"


class Reliability(enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SurfaceQuality:
    surface: ObservationSurface
    quality: EvidenceQuality
    latency: LatencyClass
    completeness: Completeness
    reliability: Reliability
    supports_incremental_sync: bool
    authentication_required: str
    description: str = ""
    score: float = 0.0

    def __post_init__(self):
        self.score = self._compute_score()

    def _compute_score(self) -> float:
        quality_scores = {EvidenceQuality.HIGH: 100, EvidenceQuality.MEDIUM: 60, EvidenceQuality.LOW: 20}
        latency_scores = {LatencyClass.REALTIME: 30, LatencyClass.NEAR_REALTIME: 15, LatencyClass.BATCH: 0}
        completeness_scores = {Completeness.FULL: 40, Completeness.PARTIAL: 20, Completeness.MINIMAL: 5}
        reliability_scores = {Reliability.HIGH: 30, Reliability.MEDIUM: 15, Reliability.LOW: 5}
        sync_bonus = 20 if self.supports_incremental_sync else 0
        score = (quality_scores.get(self.quality, 0) +
                 latency_scores.get(self.latency, 0) +
                 completeness_scores.get(self.completeness, 0) +
                 reliability_scores.get(self.reliability, 0) +
                 sync_bonus)
        return score


class ObservationDiscoveryEngine:
    def discover_surfaces(self, connector) -> list[ObservationSurface]:
        declared = getattr(connector, "observation_surfaces", None)
        if declared and isinstance(declared, list):
            return [ObservationSurface(s) if isinstance(s, str) else s for s in declared]
        if hasattr(connector, "manifest") and connector.manifest:
            manifest_surfaces = getattr(connector.manifest, "observation_surfaces", None)
            if manifest_surfaces:
                return [ObservationSurface(s) if isinstance(s, str) else s for s in manifest_surfaces]
        return []

    def rank_surfaces(self, surfaces: list, qualities: dict[ObservationSurface, SurfaceQuality]) -> list[tuple[ObservationSurface, SurfaceQuality]]:
        ranked = []
        for surface in surfaces:
            quality = qualities.get(surface)
            if quality:
                ranked.append((surface, quality))
        preference_map = {s: i for i, s in enumerate(SURFACE_PREFERENCE_ORDER)}
        ranked.sort(key=lambda x: (-x[1].score, preference_map.get(x[0], 999)))
        return ranked

    def select_pipeline(self, ranked: list[tuple[ObservationSurface, SurfaceQuality]], max_surfaces: int = 3) -> list[ObservationSurface]:
        if not ranked:
            return []
        selected = [s for s, _ in ranked[:max_surfaces]]
        webhook_types = {ObservationSurface.WEBHOOK, ObservationSurface.EVENT_STREAM}
        api_types = {ObservationSurface.OFFICIAL_API, ObservationSurface.NATIVE_CONNECTOR, ObservationSurface.EXTENSION_SDK, ObservationSurface.MCP_SERVER}
        has_webhook = any(s in webhook_types for s in selected)
        has_api = any(s in api_types for s in selected)
        if has_webhook and has_api:
            return selected
        if not has_webhook and not has_api:
            if len(selected) < max_surfaces:
                remaining = [s for s, _ in ranked if s not in selected]
                if remaining:
                    selected.append(remaining[0])
        return selected
