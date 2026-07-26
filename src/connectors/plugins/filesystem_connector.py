import os
import time

from connectors.connector import Connector
from connectors.health import ConnectorState
from connectors.models import (
    Source, RawPayload, Observation, Evidence, NormalizedPayload,
    Artifact, TraceInformation,
)


class FilesystemConnector(Connector):
    id = "filesystem"
    name = "Filesystem Connector"
    version = "1.0.0"
    vendor = "EaglEs EyE"
    description = "Observes filesystem changes and directory structure"
    capabilities = ["filesystem", "documents", "logs", "artifacts"]
    permissions = ["read", "observe"]

    def __init__(self, config=None):
        super().__init__(config)
        self._watch_paths = self.config.get("paths", [])
        self._file_cache = {}

    def connect(self) -> bool:
        self._health.state = ConnectorState.CONNECTED
        return True

    def disconnect(self) -> bool:
        self._file_cache.clear()
        self._health.state = ConnectorState.DISCONNECTED
        return True

    def discover(self) -> list:
        sources = []
        for path in self._watch_paths or [os.getcwd()]:
            if os.path.isdir(path):
                sources.append(Source.create(
                    type_="filesystem", path=path,
                ))
        return sources

    def observe(self) -> list:
        observations = []
        for path in self._watch_paths or [os.getcwd()]:
            if not os.path.isdir(path):
                continue
            for root, dirs, files in os.walk(path):
                for name in files:
                    full_path = os.path.join(root, name)
                    try:
                        stat = os.stat(full_path)
                        raw = RawPayload.from_dict({
                            "path": full_path,
                            "size": stat.st_size,
                            "modified": stat.st_mtime,
                            "created": stat.st_ctime,
                        })
                        source = Source.create(
                            type_="filesystem", path=full_path,
                        )
                        observation = Observation.create(
                            type_="file_present",
                            source=source,
                            raw=raw,
                            metadata={"connector": self.id},
                        )
                        observations.append(observation)
                    except OSError:
                        continue
        return observations

    def collect(self) -> list:
        evidence_list = []
        observations = self.observe()
        for obs in observations:
            normalized = self.normalize(obs.raw)
            artifact = Artifact.create(
                type_="file_entry",
                path=obs.source.path,
                mime_type="application/octet-stream",
            )
            trace = TraceInformation(
                connector_id=self.id,
                connector_version=self.version,
                pipeline=["observe", "collect", "normalize", "emit"],
                duration_ms=0.0,
            )
            evidence = Evidence.create(
                observation=obs,
                normalized=normalized,
                trace=trace,
                artifacts=[artifact],
            )
            evidence_list.append(evidence)
        return evidence_list
