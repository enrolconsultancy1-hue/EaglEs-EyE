import os
import subprocess

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


class GitConnector(Connector):
    id = "git"
    name = "Git Connector"
    version = "1.0.0"
    vendor = "EaglEs EyE"
    description = "Read-only Git repository observer"
    capabilities = ["git", "commits"]
    permissions = ["read", "observe"]

    def __init__(self, config=None):
        super().__init__(config)
        self._repo_path = self.config.get("repo_path", os.getcwd())
        self._git_cmd = self.config.get("git_command", "git")

    def connect(self) -> bool:
        if not self._is_git_repo():
            self._health.record_error("Not a Git repository")
            return False
        self._health.state = ConnectorState.CONNECTED
        return True

    def disconnect(self) -> bool:
        self._health.state = ConnectorState.DISCONNECTED
        return True

    def discover(self) -> list:
        return [Source.create(type_="git", path=self._repo_path)]

    def observe(self) -> list:
        observations = []
        for cmd_name, args in [
            ("status", ["status", "--porcelain"]),
            ("branch", ["branch", "--show-current"]),
            ("revision", ["rev-parse", "HEAD"]),
            ("log_latest", ["log", "--oneline", "-5"]),
        ]:
            result = self._run_git(args)
            if result is not None:
                raw = RawPayload.from_text(result)
                source = Source.create(type_="git", path=self._repo_path)
                observation = Observation.create(
                    type_=f"git_{cmd_name}",
                    source=source,
                    raw=raw,
                    metadata={"command": cmd_name},
                )
                observations.append(observation)
        return observations

    def collect(self) -> list:
        evidence_list = []
        observations = self.observe()
        for obs in observations:
            normalized = self.normalize(obs.raw)
            trace = TraceInformation(
                connector_id=self.id,
                connector_version=self.version,
                pipeline=["observe", "collect", "normalize", "emit"],
                duration_ms=0.0,
            )
            evidence = Evidence.create(
                observation=obs, normalized=normalized, trace=trace,
            )
            evidence_list.append(evidence)
        return evidence_list

    def normalize(self, raw: RawPayload):
        return NormalizedPayload.structured({
            "git_raw": raw.data,
            "connector": self.id,
        })

    def _is_git_repo(self) -> bool:
        try:
            result = subprocess.run(
                [self._git_cmd, "rev-parse", "--git-dir"],
                cwd=self._repo_path,
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return False

    def discover_observation_surfaces(self) -> list:
        return [ObservationSurface.GIT_REPOSITORY, ObservationSurface.LOCAL_WORKSPACE]

    def rank_observation_surfaces(self) -> list:
        engine = ObservationDiscoveryEngine()
        surfaces = self.discover_observation_surfaces()
        qualities = {
            ObservationSurface.GIT_REPOSITORY: SurfaceQuality(
                surface=ObservationSurface.GIT_REPOSITORY,
                quality=EvidenceQuality.HIGH,
                latency=LatencyClass.REALTIME,
                completeness=Completeness.FULL,
                reliability=Reliability.HIGH,
                supports_incremental_sync=True,
                authentication_required="none",
                description="Local git operations via subprocess",
            ),
            ObservationSurface.LOCAL_WORKSPACE: SurfaceQuality(
                surface=ObservationSurface.LOCAL_WORKSPACE,
                quality=EvidenceQuality.LOW,
                latency=LatencyClass.BATCH,
                completeness=Completeness.MINIMAL,
                reliability=Reliability.MEDIUM,
                supports_incremental_sync=False,
                authentication_required="none",
                description="Raw workspace files outside git metadata",
            ),
        }
        return engine.rank_surfaces(surfaces, qualities)

    def select_observation_pipeline(self) -> list:
        engine = ObservationDiscoveryEngine()
        ranked = self.rank_observation_surfaces()
        return engine.select_pipeline(ranked)

    def _run_git(self, args: list) -> str:
        try:
            result = subprocess.run(
                [self._git_cmd] + args,
                cwd=self._repo_path,
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            pass
        return None
