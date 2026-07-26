"""DEPRECATED — Passive ingestion for observable engineering-session evidence.

This service is deprecated. Use the connector evidence pipeline instead:

    Connector → EvidenceBus → EvidenceIngestionService → Knowledge Store

This shim remains for backward compatibility. It writes to the KnowledgeStore
directly and emits evidence through the EvidenceBus when the connector framework
is available.
"""

import os
import warnings

from services.service import Service


class EngineeringEvidenceService(Service):
    """DEPRECATED — Use connector evidence pipeline."""

    EVENT_TYPES = {
        "git": "GIT_OBSERVED",
        "build": "BUILD_OBSERVED",
        "test": "TEST_OBSERVED",
        "terminal": "TERMINAL_OBSERVED",
    }

    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None
        self._evidence_bus = None
        self._warned = False

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        if not self.store:
            raise RuntimeError("EngineeringEvidenceService requires KnowledgeStoreService.")
        connector_svc = self.kernel.get_service("ConnectorService")
        if connector_svc and connector_svc.get_manager():
            self._evidence_bus = connector_svc.get_manager().get_evidence_bus()

    def record_git(self, workspace, action, output=None, metadata=None, workspace_id=None, session_id=None):
        self._deprecation_warning()
        return self._record("git", workspace, {"action": action, "output": output}, metadata, workspace_id, session_id)

    def record_build(self, workspace, command, exit_code, output=None, metadata=None, workspace_id=None, session_id=None):
        self._deprecation_warning()
        return self._record("build", workspace, {
            "command": command, "exit_code": int(exit_code), "output": output,
        }, metadata, workspace_id, session_id)

    def record_test(self, workspace, command, exit_code, output=None, metadata=None, workspace_id=None, session_id=None):
        self._deprecation_warning()
        return self._record("test", workspace, {
            "command": command, "exit_code": int(exit_code), "output": output,
        }, metadata, workspace_id, session_id)

    def record_terminal(self, workspace, command, output=None, exit_code=None, metadata=None, workspace_id=None, session_id=None):
        self._deprecation_warning()
        payload = {"command": command, "output": output}
        if exit_code is not None:
            payload["exit_code"] = int(exit_code)
        return self._record("terminal", workspace, payload, metadata, workspace_id, session_id)

    def _record(self, kind, workspace, payload, metadata, workspace_id=None, session_id=None):
        if kind not in self.EVENT_TYPES:
            raise ValueError("Unsupported evidence kind: %s" % kind)
        path = os.path.abspath(workspace)
        evidence = dict(metadata or {})
        evidence.update({key: value for key, value in payload.items() if value is not None})
        evidence["evidence_kind"] = kind
        self.store.record_event(self.EVENT_TYPES[kind], path, evidence, workspace_id, session_id)
        if self._evidence_bus:
            from connectors.models import RawPayload, Source, Observation, Evidence as EvidenceModel, NormalizedPayload, TraceInformation
            source = Source.create(type_=kind, path=path)
            raw = RawPayload.from_dict(evidence)
            obs = Observation.create(type_=self.EVENT_TYPES[kind], source=source, raw=raw)
            norm = NormalizedPayload.structured({"evidence": evidence, "kind": kind})
            trace = TraceInformation("engineering_evidence", "2.3.0", ["record", "normalize", "emit"])
            ev = EvidenceModel.create(observation=obs, normalized=norm, trace=trace)
            self._evidence_bus.publish_evidence("engineering_evidence", [ev])
        return {"event_type": self.EVENT_TYPES[kind], "workspace": path, "payload": evidence}

    def _deprecation_warning(self):
        if not self._warned:
            warnings.warn(
                "EngineeringEvidenceService is deprecated. Use connector evidence pipeline.",
                DeprecationWarning, stacklevel=3,
            )
            self._warned = True
