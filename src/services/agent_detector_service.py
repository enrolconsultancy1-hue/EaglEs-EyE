"""Agent classification from visible workspace markers only."""

import os

from services.service import Service


class AgentDetectorService(Service):
    MARKERS = {"Codex": (".codex", "AGENTS.md"), "Claude Code": (".claude",), "Aider": (".aider", ".aider.conf.yml"), "Cursor": (".cursor",), "Cline": (".cline",), "Roo Code": (".roo",)}

    def detect(self, workspace):
        workspace = os.path.abspath(workspace); detected = []
        for agent, markers in self.MARKERS.items():
            evidence = [os.path.join(workspace, marker) for marker in markers if os.path.exists(os.path.join(workspace, marker))]
            if evidence: detected.append({"agent": agent, "evidence": evidence, "confidence": "marker_observed"})
        return {"workspace": workspace, "agents": detected, "scope": "Visible markers only; no hidden reasoning is inferred."}
