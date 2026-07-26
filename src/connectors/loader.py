import importlib
import inspect
import os
import sys

from connectors.connector import Connector
from connectors.manifest import ManifestParser, ConnectorManifest
from connectors.exceptions import ConnectorLoadError, ConnectorManifestError


class ConnectorLoader:
    def __init__(self, plugins_dir: str = ""):
        self._plugins_dir = plugins_dir
        if plugins_dir and plugins_dir not in sys.path:
            sys.path.insert(0, plugins_dir)

    def load_connector(self, module_path: str, class_name: str = "",
                       config: dict = None) -> Connector:
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise ConnectorLoadError(
                f"Failed to import module '{module_path}': {e}"
            )

        if class_name:
            cls = getattr(module, class_name, None)
            if cls is None:
                raise ConnectorLoadError(
                    f"Class '{class_name}' not found in module '{module_path}'"
                )
        else:
            cls = self._find_connector_class(module)
            if cls is None:
                raise ConnectorLoadError(
                    f"No Connector subclass found in module '{module_path}'"
                )

        try:
            connector = cls(config=config)
        except TypeError as e:
            raise ConnectorLoadError(
                f"Failed to instantiate '{cls.__name__}': {e}"
            )

        connector._source_module = module_path
        return connector

    def load_from_manifest(self, manifest_path: str,
                           config: dict = None) -> Connector:
        if not os.path.isfile(manifest_path):
            raise ConnectorLoadError(f"Manifest file not found: {manifest_path}")
        manifest = ManifestParser.parse(manifest_path)
        module_dir = os.path.dirname(os.path.abspath(manifest_path))
        if manifest.entry_point:
            module_path = manifest.entry_point
        else:
            module_path = f"connectors.plugins.{manifest.connector_id}_connector"

        try:
            if module_dir not in sys.path:
                sys.path.insert(0, module_dir)
            connector = self.load_connector(module_path, config=config)
        except ConnectorLoadError:
            module_path = f"connectors.plugins.{manifest.connector_id}_connector"
            connector = self.load_connector(module_path, config=config)

        connector.id = manifest.connector_id
        connector.name = manifest.name
        connector.version = manifest.version
        connector.vendor = manifest.vendor
        connector.description = manifest.description
        connector.capabilities = list(manifest.capabilities)
        connector.permissions = list(manifest.permissions)
        connector.manifest = manifest
        return connector

    def discover_plugins(self) -> list[tuple[str, ConnectorManifest]]:
        if not self._plugins_dir or not os.path.isdir(self._plugins_dir):
            return []
        results = []
        for fname in os.listdir(self._plugins_dir):
            if fname.endswith((".json", ".yaml", ".yml")):
                manifest_path = os.path.join(self._plugins_dir, fname)
                try:
                    manifest = ManifestParser.parse(manifest_path)
                    results.append((manifest_path, manifest))
                except (ConnectorManifestError, IOError):
                    continue
        return results

    @staticmethod
    def _find_connector_class(module):
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Connector) and obj is not Connector:
                return obj
        return None

    @staticmethod
    def resolve_entry_point(manifest: ConnectorManifest) -> str:
        if manifest.entry_point:
            return manifest.entry_point
        return f"connectors.plugins.{manifest.connector_id}_connector"
