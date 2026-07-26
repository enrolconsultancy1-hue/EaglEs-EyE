"""ProjectTwinDiscoveryService — orchestrates project twin discovery using the
LocalProjectConnector, stores twin artifacts, indexes knowledge, and publishes
notification events.

Extends the v3.0.0 platform without modifying frozen components.
"""

import json
import os
import time

from services.service import Service
from connectors.plugins.local_project_connector import LocalProjectConnector


TWIN_DISCOVERY_EVENT = "TWIN_DISCOVERY_EVENT"
TWIN_CONNECTED = "TWIN_CONNECTED"
TWIN_IDENTIFIED = "TWIN_IDENTIFIED"
TWIN_SCAN = "TWIN_SCAN"
TWIN_STACK_DETECTED = "TWIN_STACK_DETECTED"
TWIN_GIT_DETECTED = "TWIN_GIT_DETECTED"
TWIN_DEPENDENCIES = "TWIN_DEPENDENCIES"
TWIN_CREATED = "TWIN_CREATED"


class ProjectTwinDiscoveryService(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None
        self.kernel_ref = kernel

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")

    def _publish(self, event_type, data=None):
        if hasattr(self.kernel, "event_bus") and self.kernel.event_bus:
            self.kernel.event_bus.publish(event_type, data)

    def _store_twin(self, project_name, twin_data):
        config = self.kernel.get_config() or {}
        memory_path = config.get("memory_path", "memory")
        twins_dir = os.path.join(memory_path, "twins")
        os.makedirs(twins_dir, exist_ok=True)
        twin_path = os.path.join(twins_dir, f"{project_name}.twin.json")
        temp_path = twin_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(twin_data, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, twin_path)
        return twin_path

    def _index_knowledge(self, project_name, twin_data):
        if not self.store:
            return
        path = twin_data.get("project", {}).get("path", project_name)
        payload = {
            "discovery_type": "project_twin",
            "project_name": project_name,
            "project_type": twin_data.get("project", {}).get("type"),
            "languages": twin_data.get("project", {}).get("languages", []),
            "frameworks": twin_data.get("project", {}).get("frameworks", []),
            "dependencies": twin_data.get("dependencies", []),
            "file_count": twin_data.get("statistics", {}).get("file_count", 0),
            "has_git": twin_data.get("repository", {}).get("detected", False),
            "twin_data": twin_data,
        }
        self.store.record_event("PROJECT_TWIN_DISCOVERED", path, payload)

    def discover_project(self, project_path):
        notifications = []

        if not os.path.isdir(project_path):
            return {"error": f"Project path does not exist: {project_path}"}

        project_name = os.path.basename(os.path.normpath(project_path))

        connector = LocalProjectConnector(config={"project_path": project_path})

        connected = connector.connect()
        if not connected:
            return {"error": f"Could not connect to project: {project_path}"}

        self._publish(TWIN_CONNECTED, {
            "project_path": project_path,
            "project_name": project_name,
            "connection_type": "Local Project Connector",
        })
        notifications.append({"type": "connected", "message": "CONNECTED"})

        self._publish(TWIN_SCAN, {
            "status": "started",
            "project_path": project_path,
        })
        notifications.append({"type": "scan", "message": "EYE SCAN"})

        observations = connector.observe()
        discovery = connector.get_discovery_result()

        if not discovery:
            return {"error": "Discovery returned no results"}

        self._publish(TWIN_IDENTIFIED, {
            "project_name": project_name,
            "project_type": discovery.get("project", {}).get("type"),
        })
        notifications.append({"type": "identified", "message": "PROJECT IDENTIFIED"})

        languages = discovery.get("project", {}).get("languages", [])
        frameworks = discovery.get("project", {}).get("frameworks", [])
        self._publish(TWIN_STACK_DETECTED, {
            "languages": languages,
            "frameworks": frameworks,
        })
        notifications.append({"type": "stack_detected", "message": "STACK DETECTED"})

        has_git = discovery.get("repository", {}).get("detected", False)
        if has_git:
            self._publish(TWIN_GIT_DETECTED, {"project_path": project_path})
            notifications.append({"type": "git_detected", "message": "GIT REPOSITORY DETECTED"})

        dependencies = discovery.get("dependencies", [])
        if dependencies:
            self._publish(TWIN_DEPENDENCIES, {"dependencies": dependencies})
            notifications.append({"type": "dependencies", "message": "DEPENDENCIES DISCOVERED"})

        twin_data = dict(discovery)
        twin_data["discovery_time"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        twin_data["status"] = "CONNECTED"

        twin_path = self._store_twin(project_name, twin_data)
        self._index_knowledge(project_name, twin_data)

        self._publish(TWIN_CREATED, {
            "project_name": project_name,
            "twin_path": twin_path,
        })
        notifications.append({"type": "twin_created", "message": "PROJECT TWIN CREATED"})

        result = {
            "project_name": project_name,
            "project_path": project_path,
            "discovery": discovery,
            "twin_path": twin_path,
            "notifications": notifications,
            "status": "CONNECTED",
        }

        return result
