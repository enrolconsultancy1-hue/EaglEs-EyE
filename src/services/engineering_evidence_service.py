"""Passive ingestion for observable engineering-session evidence."""

import os

from services.service import Service


class EngineeringEvidenceService(Service):
    """Stores externally observed Git, build, test, and terminal facts.

    This service does not execute commands, inspect hidden agent state, or alter
    a watched workspace. Callers provide evidence they have already observed.
    """

    EVENT_TYPES = {
        "git": "GIT_OBSERVED",
        "build": "BUILD_OBSERVED",
        "test": "TEST_OBSERVED",
        "terminal": "TERMINAL_OBSERVED",
    }

    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        if not self.store:
            raise RuntimeError("EngineeringEvidenceService requires KnowledgeStoreService.")

    def record_git(self, workspace, action, output=None, metadata=None):
        return self._record("git", workspace, {"action": action, "output": output}, metadata)

    def record_build(self, workspace, command, exit_code, output=None, metadata=None):
        return self._record("build", workspace, {
            "command": command, "exit_code": int(exit_code), "output": output,
        }, metadata)

    def record_test(self, workspace, command, exit_code, output=None, metadata=None):
        return self._record("test", workspace, {
            "command": command, "exit_code": int(exit_code), "output": output,
        }, metadata)

    def record_terminal(self, workspace, command, output=None, exit_code=None, metadata=None):
        payload = {"command": command, "output": output}
        if exit_code is not None:
            payload["exit_code"] = int(exit_code)
        return self._record("terminal", workspace, payload, metadata)

    def _record(self, kind, workspace, payload, metadata):
        if kind not in self.EVENT_TYPES:
            raise ValueError("Unsupported evidence kind: %s" % kind)
        path = os.path.abspath(workspace)
        evidence = dict(metadata or {})
        evidence.update({key: value for key, value in payload.items() if value is not None})
        evidence["evidence_kind"] = kind
        self.store.record_event(self.EVENT_TYPES[kind], path, evidence)
        return {"event_type": self.EVENT_TYPES[kind], "workspace": path, "payload": evidence}
