import os

from services.service import Service
from connectors.connector_manager import ConnectorManager
from connectors.plugins.filesystem_connector import FilesystemConnector
from connectors.plugins.git_connector import GitConnector
from connectors.plugins.mock_connector import MockConnector


class ConnectorService(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self._manager = None
        self._plugins_dir = ""

    def start(self):
        super().start()
        config = self.kernel.get_config()
        conn_config = config.get("connectors", {})
        self._plugins_dir = conn_config.get(
            "plugins_dir",
            os.path.join(os.path.dirname(__file__), "..", "connectors", "plugins"),
        )
        auto_discover = conn_config.get("auto_discover", True)
        self._manager = ConnectorManager(
            plugins_dir=self._plugins_dir,
            auto_discover=auto_discover,
            event_bus=self.kernel.event_bus,
        )
        connector_config = conn_config.get("config", {})
        self._manager.start(config=connector_config)

        connector_config = conn_config.get("config", {})
        self._register_builtin_connectors(connector_config)
        self._start_registered_connectors(connector_config)

    def stop(self):
        if self._manager:
            self._manager.stop()
        super().stop()

    def _register_builtin_connectors(self, config: dict):
        connectors = {
            "filesystem": (
                FilesystemConnector,
                config.get("filesystem", {"paths": []}),
            ),
            "git": (
                GitConnector,
                config.get("git", {}),
            ),
            "mock": (
                MockConnector,
                config.get("mock", {}),
            ),
        }
        for cid, (cls, cfg) in connectors.items():
            if not self._manager.has_connector(cid):
                connector = cls(config=cfg)
                self._manager._registry.register(connector)

    def _start_registered_connectors(self, config: dict):
        for cid in self._manager.list_ids():
            enabled = config.get(cid, {}).get("enabled", True)
            if enabled:
                self._manager.start_connector(cid)

    def get_manager(self):
        return self._manager

    @property
    def manager(self):
        return self._manager
