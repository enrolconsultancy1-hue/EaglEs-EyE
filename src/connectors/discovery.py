import os
from typing import Optional

from connectors.registry import ConnectorRegistry
from connectors.manifest import ManifestParser, ConnectorManifest
from connectors.loader import ConnectorLoader
from connectors.exceptions import ConnectorDiscoveryError


class ConnectorDiscovery:
    def __init__(self, registry: ConnectorRegistry,
                 plugins_dir: str = ""):
        self._registry = registry
        self._loader = ConnectorLoader(plugins_dir=plugins_dir)
        self._plugins_dir = plugins_dir

    def discover_all(self, config: Optional[dict] = None) -> list[tuple[str, bool, str]]:
        results = []
        manifests = self._loader.discover_plugins()
        for manifest_path, manifest in manifests:
            success, message = self._register_from_manifest(
                manifest_path, manifest, config
            )
            results.append((manifest.connector_id, success, message))
        return results

    def discover_directory(self, directory: str,
                           config: Optional[dict] = None) -> list[tuple[str, bool, str]]:
        if not os.path.isdir(directory):
            raise ConnectorDiscoveryError(f"Directory not found: {directory}")
        results = []
        for fname in os.listdir(directory):
            if fname.endswith((".json", ".yaml", ".yml")):
                manifest_path = os.path.join(directory, fname)
                try:
                    manifest = ManifestParser.parse(manifest_path)
                    success, message = self._register_from_manifest(
                        manifest_path, manifest, config
                    )
                    results.append((manifest.connector_id, success, message))
                except Exception:
                    results.append((fname, False, "Failed to parse manifest"))
        return results

    def resolve_dependencies(self) -> list[tuple[str, list[str]]]:
        unresolved = []
        for cid in self._registry.list_ids():
            manifest = self._registry.get_manifest(cid)
            if manifest and manifest.dependencies:
                missing = [
                    dep for dep in manifest.dependencies
                    if not self._registry.has(dep)
                ]
                if missing:
                    unresolved.append((cid, missing))
        return unresolved

    def _register_from_manifest(self, manifest_path: str,
                                manifest: ConnectorManifest,
                                config: Optional[dict] = None) -> tuple[bool, str]:
        if self._registry.has(manifest.connector_id):
            return False, f"Already registered: {manifest.connector_id}"
        try:
            connector = self._loader.load_from_manifest(
                manifest_path, config=config
            )
            self._registry.register(connector, manifest=manifest)
            return True, f"Registered: {manifest.connector_id}"
        except Exception as e:
            return False, f"Failed to load {manifest.connector_id}: {e}"
