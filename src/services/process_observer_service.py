"""Passive adapters for externally observed build, test, and terminal results."""

import os

from services.service import Service


class ProcessObserverService(Service):
    """Records completed process evidence supplied by an external observer.

    The service does not spawn processes or inspect an agent's hidden state.
    Its inputs must already be observable command facts.
    """

    def __init__(self, kernel):
        super().__init__(kernel)
        self.evidence = None

    def start(self):
        super().start()
        self.evidence = self.kernel.get_service("EngineeringEvidenceService")
        if not self.evidence:
            raise RuntimeError("ProcessObserverService requires EngineeringEvidenceService.")

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
