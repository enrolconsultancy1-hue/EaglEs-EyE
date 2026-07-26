import threading
from typing import Optional

from connectors.connector import Connector
from connectors.manifest import ConnectorManifest
from connectors.validator import ManifestValidator
from connectors.exceptions import (
    ConnectorNotFoundError, ConnectorRegistrationError,
)


class ConnectorRegistry:
    def __init__(self):
        self._entries: dict[str, _RegistryEntry] = {}
        self._lock = threading.Lock()

    def register(self, connector: Connector, manifest: Optional[ConnectorManifest] = None) -> str:
        connector_id = connector.id or connector.__class__.__name__
        with self._lock:
            if connector_id in self._entries:
                raise ConnectorRegistrationError(
                    f"Connector already registered: {connector_id}"
                )
            entry = _RegistryEntry(
                connector=connector,
                connector_id=connector_id,
                manifest=manifest,
            )
            self._entries[connector_id] = entry
        return connector_id

    def unregister(self, connector_id: str) -> bool:
        with self._lock:
            entry = self._entries.pop(connector_id, None)
            if entry is None:
                return False
            if entry.connector:
                entry.connector.stop()
        return True

    def get(self, connector_id: str) -> Connector:
        with self._lock:
            entry = self._entries.get(connector_id)
            if entry is None:
                raise ConnectorNotFoundError(f"Connector not found: {connector_id}")
            return entry.connector

    def get_manifest(self, connector_id: str) -> Optional[ConnectorManifest]:
        with self._lock:
            entry = self._entries.get(connector_id)
            return entry.manifest if entry else None

    def list_ids(self) -> list[str]:
        with self._lock:
            return list(self._entries.keys())

    def list_connectors(self) -> list[Connector]:
        with self._lock:
            return [e.connector for e in self._entries.values()]

    def list_manifests(self) -> list[tuple[str, ConnectorManifest]]:
        with self._lock:
            return [(cid, e.manifest) for cid, e in self._entries.items()
                    if e.manifest]

    def size(self) -> int:
        with self._lock:
            return len(self._entries)

    def has(self, connector_id: str) -> bool:
        with self._lock:
            return connector_id in self._entries

    def validate_all(self) -> list[tuple[str, list[str]]]:
        results = []
        with self._lock:
            for cid, entry in self._entries.items():
                if entry.manifest:
                    errors = ManifestValidator.validate(entry.manifest)
                    if errors:
                        results.append((cid, errors))
        return results

    def clear(self):
        with self._lock:
            for entry in self._entries.values():
                if entry.connector:
                    entry.connector.stop()
            self._entries.clear()


class _RegistryEntry:
    def __init__(self, connector: Connector, connector_id: str,
                 manifest: Optional[ConnectorManifest] = None):
        self.connector = connector
        self.connector_id = connector_id
        self.manifest = manifest
