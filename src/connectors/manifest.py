import json
import os
from dataclasses import dataclass, field
from typing import Optional

from connectors.exceptions import ConnectorManifestError


@dataclass
class ConnectorManifest:
    connector_id: str
    name: str
    version: str
    vendor: str = ""
    description: str = ""
    capabilities: list = field(default_factory=list)
    permissions: list = field(default_factory=list)
    min_eye_version: str = "0.0.0"
    supported_os: list = field(default_factory=list)
    supported_protocols: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)
    entry_point: str = ""
    config_schema: dict = field(default_factory=dict)
    observation_surfaces: list = field(default_factory=list)
    preferred_surface: str = "auto"
    supports_multi_surface: bool = False
    supports_incremental_sync: bool = False
    supports_realtime: bool = False

    def supports_capability(self, capability: str) -> bool:
        return capability in self.capabilities

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def is_compatible(self) -> bool:
        return True


class ManifestParser:
    SUPPORTED_EXTENSIONS = (".json", ".yaml", ".yml")

    @staticmethod
    def parse(path: str) -> ConnectorManifest:
        ext = os.path.splitext(path)[1].lower()
        if ext not in ManifestParser.SUPPORTED_EXTENSIONS:
            raise ConnectorManifestError(f"Unsupported manifest extension: {ext}")

        with open(path, "r", encoding="utf-8") as f:
            if ext == ".json":
                data = json.load(f)
            else:
                try:
                    import yaml
                    data = yaml.safe_load(f)
                except ImportError:
                    raise ConnectorManifestError(
                        "PyYAML is required to parse .yaml manifests"
                    )

        return ManifestParser._from_dict(data, path)

    @staticmethod
    def parse_string(content: str, format_: str = "json") -> ConnectorManifest:
        if format_ == "json":
            data = json.loads(content)
        elif format_ in ("yaml", "yml"):
            try:
                import yaml
                data = yaml.safe_load(content)
            except ImportError:
                raise ConnectorManifestError(
                    "PyYAML is required to parse YAML manifests"
                )
        else:
            raise ConnectorManifestError(f"Unsupported format: {format_}")

        return ManifestParser._from_dict(data, "<string>")

    @staticmethod
    def _from_dict(data: dict, source: str) -> ConnectorManifest:
        connector_id = data.get("connector_id") or data.get("id")
        if not connector_id:
            raise ConnectorManifestError(
                f"Manifest at {source} missing required 'connector_id' field"
            )
        name = data.get("name") or connector_id
        version = data.get("version") or "0.1.0"
        if not isinstance(version, str):
            version = str(version)

        return ConnectorManifest(
            connector_id=connector_id,
            name=name,
            version=version,
            vendor=data.get("vendor", ""),
            description=data.get("description", ""),
            capabilities=data.get("capabilities", []),
            permissions=data.get("permissions", []),
            min_eye_version=data.get("min_eye_version", "0.0.0"),
            supported_os=data.get("supported_os", []),
            supported_protocols=data.get("supported_protocols", []),
            dependencies=data.get("dependencies", []),
            entry_point=data.get("entry_point", ""),
            config_schema=data.get("config_schema", {}),
            observation_surfaces=data.get("observation_surfaces", []),
            preferred_surface=data.get("preferred_surface", "auto"),
            supports_multi_surface=data.get("supports_multi_surface", False),
            supports_incremental_sync=data.get("supports_incremental_sync", False),
            supports_realtime=data.get("supports_realtime", False),
        )
