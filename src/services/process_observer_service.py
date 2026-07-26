"""DEPRECATED — Passive adapters for externally observed build, test, terminal.

This service is deprecated. Use connectors routed through the evidence pipeline:

    Connector → EvidenceBus → EvidenceIngestionService → Knowledge Store

This shim delegates to EngineeringEvidenceService for backward compatibility.
"""

import os
import warnings

from services.service import Service


class ProcessObserverService(Service):
    """DEPRECATED — Use connectors via the connector framework."""

    def __init__(self, kernel):
        super().__init__(kernel)
        self.evidence = None
        self._warned = False

    def start(self):
        super().start()
        self.evidence = self.kernel.get_service("EngineeringEvidenceService")
        if not self.evidence:
            raise RuntimeError("ProcessObserverService requires EngineeringEvidenceService.")
        if not self._warned:
            warnings.warn(
                "ProcessObserverService is deprecated. Use connectors via connector framework.",
                DeprecationWarning, stacklevel=2,
            )
            self._warned = True

    def observe_build(self, workspace, command, exit_code, output=None, metadata=None):
        return self.evidence.record_build(
            os.path.abspath(workspace), command, exit_code, output, self._metadata(metadata)
        )

    def observe_test(self, workspace, command, exit_code, output=None, metadata=None):
        return self.evidence.record_test(
            os.path.abspath(workspace), command, exit_code, output, self._metadata(metadata)
        )

    def observe_terminal(self, workspace, command, output=None, exit_code=None, metadata=None):
        return self.evidence.record_terminal(
            os.path.abspath(workspace), command, output, exit_code, self._metadata(metadata)
        )

    @staticmethod
    def _metadata(metadata):
        result = dict(metadata or {})
        result["observer"] = "external_process_observer"
        return result
