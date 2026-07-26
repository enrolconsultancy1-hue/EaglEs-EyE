"""GitHub Connector — production-quality read-only connector for GitHub repositories.

Capabilities: repository metadata, branches, commits, pull requests, issues,
releases, tags, contributors, repository events.

Uses the REST Connector base class for pagination, retry, authentication, and
incremental synchronization. No write operations — observation only.
"""

import time
from typing import Optional

from connectors.rest_connector import RESTConnector
from connectors.observation_discovery import (
    ObservationSurface, ObservationDiscoveryEngine, SurfaceQuality,
    EvidenceQuality, LatencyClass, Completeness, Reliability,
)
from connectors.models import (
    Observation, Evidence, Source, RawPayload, NormalizedPayload,
    TraceInformation, Artifact,
)


class GitHubConnector(RESTConnector):
    id: str = "github"
    name: str = "GitHub Connector"
    version: str = "1.0.0"
    vendor: str = "EaglEs EyE"
    description: str = "Read-only GitHub repository observer"
    capabilities: list = ["git", "commits", "issues", "tasks", "api"]
    permissions: list = ["read", "observe"]
    observation_surfaces: list = [ObservationSurface.OFFICIAL_API,
                                   ObservationSurface.GIT_REPOSITORY,
                                   ObservationSurface.WEBHOOK]
    preferred_surface: str = "auto"
    supports_multi_surface: bool = True
    supports_incremental_sync: bool = True
    supports_realtime: bool = False

    def __init__(self, config: Optional[dict] = None):
        config = config or {}
        config.setdefault("base_url", "https://api.github.com")
        config.setdefault("auth", {"provider": "bearer",
                                    "token": config.get("token", "")})
        config.setdefault("retry_base_delay", 1.0)
        config.setdefault("retry_backoff", 2.0)
        config.setdefault("max_retries", 3)
        super().__init__(config)
        self._owner = self.config.get("owner", "")
        self._repo = self.config.get("repo", "")
        self._discovery_engine = ObservationDiscoveryEngine()

    def connect(self) -> bool:
        if not self._owner or not self._repo:
            return False
        result = super().connect()
        if result:
            status, data, _ = self._get(f"/repos/{self._owner}/{self._repo}")
            result = status == 200
            if not result:
                self._metrics.record_failure(self.id, f"GitHub API returned {status}")
        return result

    def disconnect(self) -> bool:
        return True

    def discover(self) -> list:
        sources = []
        api_source = Source(id=f"github:{self._owner}/{self._repo}:api",
                            type="github_api",
                            path=f"https://api.github.com/repos/{self._owner}/{self._repo}",
                            version=self.version)
        sources.append(api_source)
        git_source = Source(id=f"github:{self._owner}/{self._repo}:git",
                            type="git_repository",
                            path=f"https://github.com/{self._owner}/{self._repo}.git",
                            version="")
        sources.append(git_source)
        return sources

    def discover_observation_surfaces(self) -> list:
        return self.observation_surfaces

    def rank_observation_surfaces(self) -> list[tuple]:
        surfaces = self.discover_observation_surfaces()
        qualities = {
            ObservationSurface.OFFICIAL_API: SurfaceQuality(
                surface=ObservationSurface.OFFICIAL_API,
                quality=EvidenceQuality.HIGH,
                latency=LatencyClass.NEAR_REALTIME,
                completeness=Completeness.FULL,
                reliability=Reliability.HIGH,
                supports_incremental_sync=True,
                authentication_required="token",
                description="GitHub REST API v3",
            ),
            ObservationSurface.GIT_REPOSITORY: SurfaceQuality(
                surface=ObservationSurface.GIT_REPOSITORY,
                quality=EvidenceQuality.MEDIUM,
                latency=LatencyClass.BATCH,
                completeness=Completeness.PARTIAL,
                reliability=Reliability.HIGH,
                supports_incremental_sync=True,
                authentication_required="token",
                description="Git clone and local git operations",
            ),
            ObservationSurface.WEBHOOK: SurfaceQuality(
                surface=ObservationSurface.WEBHOOK,
                quality=EvidenceQuality.HIGH,
                latency=LatencyClass.REALTIME,
                completeness=Completeness.PARTIAL,
                reliability=Reliability.MEDIUM,
                supports_incremental_sync=False,
                authentication_required="token",
                description="GitHub webhook events",
            ),
        }
        return self._discovery_engine.rank_surfaces(surfaces, qualities)

    def select_observation_pipeline(self) -> list:
        ranked = self.rank_observation_surfaces()
        return self._discovery_engine.select_pipeline(ranked, max_surfaces=2)

    def get_active_surfaces(self) -> list:
        return self.select_observation_pipeline()

    def observe(self) -> list:
        observations = []
        repo_status, repo_data, _ = self._get(f"/repos/{self._owner}/{self._repo}")
        if repo_status == 200:
            obs = self._make_observation("repository", repo_data)
            observations.append(obs)
        return observations

    def collect(self) -> list:
        evidence_list = []
        repo_obs = self.observe()
        if repo_obs:
            repo_data = repo_obs[0]
            normalized = self.normalize(RawPayload.from_dict(repo_data.raw.data if hasattr(repo_data, 'raw') else {}))
            trace = TraceInformation(connector_id=self.id, connector_version=self.version,
                                     pipeline=["observe", "collect", "normalize", "emit"],
                                     duration_ms=0.0)
            evidence = Evidence.create(observation=repo_obs[0], normalized=normalized, trace=trace)
            if self.validate_evidence(evidence):
                evidence_list.append(evidence)

        branches = self._paginate(f"/repos/{self._owner}/{self._repo}/branches")
        if branches:
            obs = self._make_observation("branches", branches)
            norm = self.normalize(RawPayload.from_dict({"branches": branches}))
            trace = TraceInformation(self.id, self.version, ["collect", "normalize", "emit"], 0.0)
            evidence = Evidence.create(observation=obs, normalized=norm, trace=trace)
            if self.validate_evidence(evidence):
                evidence_list.append(evidence)

        commits = self._paginate(f"/repos/{self._owner}/{self._repo}/commits", params={"per_page": 100})
        if commits:
            obs = self._make_observation("commits", commits)
            norm = self.normalize(RawPayload.from_dict({"commits": commits}))
            trace = TraceInformation(self.id, self.version, ["collect", "normalize", "emit"], 0.0)
            evidence = Evidence.create(observation=obs, normalized=norm, trace=trace)
            if self.validate_evidence(evidence):
                evidence_list.append(evidence)

        prs = self._paginate(f"/repos/{self._owner}/{self._repo}/pulls", params={"state": "all", "per_page": 100})
        if prs:
            obs = self._make_observation("pull_requests", prs)
            norm = self.normalize(RawPayload.from_dict({"pull_requests": prs}))
            trace = TraceInformation(self.id, self.version, ["collect", "normalize", "emit"], 0.0)
            evidence = Evidence.create(observation=obs, normalized=norm, trace=trace)
            if self.validate_evidence(evidence):
                evidence_list.append(evidence)

        issues = self._paginate(f"/repos/{self._owner}/{self._repo}/issues", params={"state": "all", "per_page": 100})
        if issues:
            obs = self._make_observation("issues", issues)
            norm = self.normalize(RawPayload.from_dict({"issues": issues}))
            trace = TraceInformation(self.id, self.version, ["collect", "normalize", "emit"], 0.0)
            evidence = Evidence.create(observation=obs, normalized=norm, trace=trace)
            if self.validate_evidence(evidence):
                evidence_list.append(evidence)

        releases = self._paginate(f"/repos/{self._owner}/{self._repo}/releases", params={"per_page": 100})
        if releases:
            obs = self._make_observation("releases", releases)
            norm = self.normalize(RawPayload.from_dict({"releases": releases}))
            trace = TraceInformation(self.id, self.version, ["collect", "normalize", "emit"], 0.0)
            evidence = Evidence.create(observation=obs, normalized=norm, trace=trace)
            if self.validate_evidence(evidence):
                evidence_list.append(evidence)

        tags = self._paginate(f"/repos/{self._owner}/{self._repo}/tags", params={"per_page": 100})
        if tags:
            obs = self._make_observation("tags", tags)
            norm = self.normalize(RawPayload.from_dict({"tags": tags}))
            trace = TraceInformation(self.id, self.version, ["collect", "normalize", "emit"], 0.0)
            evidence = Evidence.create(observation=obs, normalized=norm, trace=trace)
            if self.validate_evidence(evidence):
                evidence_list.append(evidence)

        contributors = self._paginate(f"/repos/{self._owner}/{self._repo}/contributors", params={"per_page": 100})
        if contributors:
            obs = self._make_observation("contributors", contributors)
            norm = self.normalize(RawPayload.from_dict({"contributors": contributors}))
            trace = TraceInformation(self.id, self.version, ["collect", "normalize", "emit"], 0.0)
            evidence = Evidence.create(observation=obs, normalized=norm, trace=trace)
            if self.validate_evidence(evidence):
                evidence_list.append(evidence)

        repo_events = self._paginate(f"/repos/{self._owner}/{self._repo}/events", params={"per_page": 100})
        if repo_events:
            obs = self._make_observation("events", repo_events)
            norm = self.normalize(RawPayload.from_dict({"events": repo_events}))
            trace = TraceInformation(self.id, self.version, ["collect", "normalize", "emit"], 0.0)
            evidence = Evidence.create(observation=obs, normalized=norm, trace=trace)
            if self.validate_evidence(evidence):
                evidence_list.append(evidence)

        self._metrics.record_sync(self.id, 0.0, len(evidence_list))
        return evidence_list

    def _make_observation(self, type_: str, data) -> Observation:
        source = Source(id=f"github:{self._owner}/{self._repo}",
                        type="github_api",
                        path=f"https://api.github.com/repos/{self._owner}/{self._repo}",
                        version=self.version)
        raw = RawPayload.from_dict(data) if isinstance(data, dict) else RawPayload.from_dict({"items": data})
        return Observation.create(type_=type_, source=source, raw=raw)
