"""Workspace identity registry for future multi-workspace observation."""

import hashlib
import os

from services.service import Service


class WorkspaceObserverService(Service):
    """Registers isolated workspaces without changing watcher behavior."""

    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        if not self.store:
            raise RuntimeError("WorkspaceObserverService requires KnowledgeStoreService.")

    def register_workspace(self, path, metadata=None):
        workspace_path = os.path.abspath(path)
        if not os.path.isdir(workspace_path):
            raise ValueError("Workspace path must be an existing directory: %s" % workspace_path)
        workspace_id = self.workspace_id(workspace_path)
        evidence = dict(metadata or {})
        evidence["identity_source"] = "normalized_workspace_path"
        return self.store.upsert_workspace(workspace_id, workspace_path, evidence)

    def unregister_workspace(self, workspace_id):
        return self.store.set_workspace_status(workspace_id, "inactive")

    def workspaces(self, include_inactive=True):
        return self.store.list_workspaces(include_inactive=include_inactive)

    @staticmethod
    def workspace_id(path):
        normalized = os.path.normcase(os.path.abspath(path))
        return "workspace-" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]
