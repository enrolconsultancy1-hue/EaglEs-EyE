"""Passive, read-only Git evidence collection for watched workspaces."""

import os
import subprocess

from services.service import Service


class GitObserverService(Service):
    """Observes Git facts without staging, committing, or changing a repository."""

    def __init__(self, kernel, command_runner=None):
        super().__init__(kernel)
        self.evidence = None
        self.command_runner = command_runner or self._run_git

    def start(self):
        super().start()
        self.evidence = self.kernel.get_service("EngineeringEvidenceService")
        if not self.evidence:
            raise RuntimeError("GitObserverService requires EngineeringEvidenceService.")

    def observe(self, workspace):
        """Record the current branch, commit, and porcelain status if available."""
        workspace = os.path.abspath(workspace)
        status = self.command_runner(workspace, "status", "--porcelain=v1", "--branch")
        if status["exit_code"] != 0:
            return {
                "observed": False, "workspace": workspace, "reason": "git_unavailable_or_not_repository",
                "exit_code": status["exit_code"], "output": status["output"],
            }
        head = self.command_runner(workspace, "rev-parse", "HEAD")
        branch = self.command_runner(workspace, "branch", "--show-current")
        payload = {
            "branch": branch["output"].strip() or None,
            "head": head["output"].strip() if head["exit_code"] == 0 else None,
            "status_porcelain": status["output"],
            "head_exit_code": head["exit_code"],
        }
        recorded = self.evidence.record_git(workspace, "snapshot", metadata=payload)
        return {"observed": True, "workspace": workspace, "evidence": recorded}

    @staticmethod
    def _run_git(workspace, *arguments):
        try:
            result = subprocess.run(
                ["git", "-C", workspace, *arguments], capture_output=True,
                text=True, encoding="utf-8", errors="replace", check=False,
            )
        except OSError as error:
            return {"exit_code": 127, "output": str(error)}
        return {
            "exit_code": result.returncode,
            "output": result.stdout if result.returncode == 0 else result.stderr,
        }
