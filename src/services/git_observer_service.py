"""DEPRECATED — Passive, read-only Git evidence collection.

This service is deprecated. Use GitConnector (connectors/plugins/git_connector.py)
which routes through the connector evidence pipeline:

    GitConnector → EvidenceBus → EvidenceIngestionService → Knowledge Store

This shim remains for backward compatibility. It delegates to GitConnector when
available and prints a deprecation warning on first use.
"""

import os
import warnings

from services.service import Service


class GitObserverService(Service):
    """DEPRECATED — Use GitConnector via the connector framework."""

    def __init__(self, kernel, command_runner=None):
        super().__init__(kernel)
        self._git_connector = None
        self._warned = False

    def start(self):
        super().start()
        connector_svc = self.kernel.get_service("ConnectorService")
        if connector_svc and connector_svc.get_manager():
            try:
                self._git_connector = connector_svc.get_manager().get_connector("git")
            except Exception:
                pass

    def observe(self, workspace):
        if not self._warned:
            warnings.warn(
                "GitObserverService is deprecated. Use GitConnector via connector framework.",
                DeprecationWarning, stacklevel=2,
            )
            self._warned = True
        if self._git_connector:
            self._git_connector.config["repo_path"] = os.path.abspath(workspace)
            if self._git_connector.connect():
                observations = self._git_connector.observe()
                evidence = self._git_connector.collect()
                return {
                    "observed": True,
                    "workspace": workspace,
                    "via": "GitConnector",
                    "observations": len(observations),
                    "evidence": len(evidence),
                }
        return {
            "observed": False,
            "workspace": workspace,
            "reason": "GitConnector unavailable or not connected",
        }
