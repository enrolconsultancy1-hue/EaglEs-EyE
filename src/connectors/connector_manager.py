import time
import threading
from typing import Optional

from connectors.registry import ConnectorRegistry
from connectors.discovery import ConnectorDiscovery
from connectors.loader import ConnectorLoader
from connectors.health import ConnectorState
from connectors.events import (
    ConnectorEventData,
    CONNECTOR_REGISTERED, CONNECTOR_STARTED, CONNECTOR_STOPPED,
    CONNECTOR_HEALTH_CHANGED, CONNECTOR_DISCOVERED, CONNECTOR_FAILED,
    CONNECTOR_OBSERVATION, CONNECTOR_EVIDENCE, CONNECTOR_WARNING,
    CONNECTOR_ERROR,
)
from connectors.exceptions import ConnectorNotFoundError


class ConnectorManager:
    def __init__(self, plugins_dir: str = "",
                 auto_discover: bool = True,
                 event_bus=None):
        self._registry = ConnectorRegistry()
        self._discovery = ConnectorDiscovery(
            registry=self._registry, plugins_dir=plugins_dir,
        )
        self._loader = ConnectorLoader(plugins_dir=plugins_dir)
        self._event_bus = event_bus
        self._plugins_dir = plugins_dir
        self._auto_discover = auto_discover
        self._running = False
        self._lock = threading.Lock()
        self._started_at: Optional[float] = None

    # --- Lifecycle ---

    def start(self, config: Optional[dict] = None):
        with self._lock:
            if self._running:
                return
            self._running = True
            self._started_at = time.time()

        config = config or {}
        if self._auto_discover:
            self._discover_and_register(config)

    def stop(self):
        with self._lock:
            if not self._running:
                return
            self._running = False
            self._registry.clear()
            self._started_at = None

    # --- Discovery ---

    def _discover_and_register(self, config: dict):
        results = self._discovery.discover_all(config=config)
        for cid, success, message in results:
            event_type = CONNECTOR_DISCOVERED if success else CONNECTOR_FAILED
            self._publish_event(event_type, {
                "connector_id": cid,
                "success": success,
                "message": message,
            })
            if success:
                self._publish_event(CONNECTOR_REGISTERED, {
                    "connector_id": cid,
                })

    # --- Connector access ---

    def get_connector(self, connector_id: str):
        return self._registry.get(connector_id)

    def list_connectors(self):
        return self._registry.list_connectors()

    def list_ids(self) -> list[str]:
        return self._registry.list_ids()

    def has_connector(self, connector_id: str) -> bool:
        return self._registry.has(connector_id)

    def size(self) -> int:
        return self._registry.size()

    # --- Connector operations ---

    def start_connector(self, connector_id: str) -> bool:
        connector = self._registry.get(connector_id)
        result = connector.start()
        if result:
            self._publish_event(CONNECTOR_STARTED, {"connector_id": connector_id})
        else:
            self._publish_event(CONNECTOR_FAILED, {
                "connector_id": connector_id,
                "message": "Failed to start",
            })
        return result

    def stop_connector(self, connector_id: str) -> bool:
        connector = self._registry.get(connector_id)
        result = connector.stop()
        if result:
            self._publish_event(CONNECTOR_STOPPED, {"connector_id": connector_id})
        return result

    def observe_connector(self, connector_id: str):
        connector = self._registry.get(connector_id)
        observations = connector.observe()
        if observations:
            self._publish_event(CONNECTOR_OBSERVATION, {
                "connector_id": connector_id,
                "count": len(observations),
            })
        return observations

    def collect_evidence(self, connector_id: str):
        connector = self._registry.get(connector_id)
        evidence_list = connector.collect()
        for evidence in evidence_list:
            self._publish_event(CONNECTOR_EVIDENCE, {
                "connector_id": connector_id,
                "evidence_id": evidence.id,
            })
        return evidence_list

    def heartbeat_connector(self, connector_id: str) -> bool:
        connector = self._registry.get(connector_id)
        return connector.heartbeat()

    def connector_status(self, connector_id: str) -> dict:
        connector = self._registry.get(connector_id)
        return connector.status()

    # --- Health ---

    def check_health_all(self) -> dict[str, dict]:
        results = {}
        for cid in self._registry.list_ids():
            try:
                connector = self._registry.get(cid)
                results[cid] = connector.health().to_dict()
            except Exception:
                results[cid] = {"state": "error", "errors": ["health check failed"]}
        return results

    def get_uptime(self) -> float:
        if self._started_at:
            return time.time() - self._started_at
        return 0.0

    # --- Plugin registration ---

    def register_plugin(self, manifest_path: str,
                        config: Optional[dict] = None) -> tuple[bool, str, str]:
        try:
            manifest = self._discovery._loader.load_from_manifest(
                manifest_path, config=config,
            )
        except Exception as e:
            return False, "", f"Failed to load plugin: {e}"

        try:
            connector_id = self._registry.register(
                manifest, manifest=manifest.manifest,
            )
        except Exception as e:
            return False, "", f"Failed to register: {e}"

        self._publish_event(CONNECTOR_REGISTERED, {"connector_id": connector_id})
        return True, connector_id, "Registered"

    # --- Internal ---

    def _publish_event(self, event_type: str, data: dict):
        if self._event_bus:
            event_data = ConnectorEventData(
                connector_id=data.get("connector_id", ""),
                event_type=event_type,
                payload=data,
            )
            self._event_bus.publish(event_type, event_data)
