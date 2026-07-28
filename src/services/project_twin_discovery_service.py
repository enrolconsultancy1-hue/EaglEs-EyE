"""ProjectTwinDiscoveryService — orchestrates project twin discovery using the
LocalProjectConnector, stores twin artifacts, indexes knowledge, and publishes
notification events.

v3.1 Historical Memory: Every scan creates a versioned twin with timestamp,
fingerprint, and persistent history. The service tracks how the project evolves.
"""

import json
import os
import time

from services.service import Service
from connectors.plugins.local_project_connector import LocalProjectConnector
from services.project_intelligence_enhancer import enhance as enhance_intelligence


TWIN_DISCOVERY_EVENT = "TWIN_DISCOVERY_EVENT"
TWIN_CONNECTED = "TWIN_CONNECTED"
TWIN_IDENTIFIED = "TWIN_IDENTIFIED"
TWIN_SCAN = "TWIN_SCAN"
TWIN_STACK_DETECTED = "TWIN_STACK_DETECTED"
TWIN_GIT_DETECTED = "TWIN_GIT_DETECTED"
TWIN_DEPENDENCIES = "TWIN_DEPENDENCIES"
TWIN_DOCUMENTATION = "TWIN_DOCUMENTATION"
TWIN_CONFIG = "TWIN_CONFIG"
TWIN_CREATED = "TWIN_CREATED"
TWIN_VERSIONED = "TWIN_VERSIONED"


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

    # --- History Management ---

    def _get_twins_dir(self):
        config = self.kernel.get_config() or {}
        memory_path = config.get("memory_path", "memory")
        return os.path.join(memory_path, "twins")

    def _get_project_history_path(self, project_name):
        twins_dir = self._get_twins_dir()
        return os.path.join(twins_dir, project_name, "history.json")

    def _get_project_versions_dir(self, project_name):
        twins_dir = self._get_twins_dir()
        path = os.path.join(twins_dir, project_name, "versions")
        os.makedirs(path, exist_ok=True)
        return path

    def _load_twin_history(self, project_name):
        path = self._get_project_history_path(project_name)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return {"project_name": project_name, "versions": [], "current_version": 0}

    def _save_twin_history(self, project_name, history):
        path = self._get_project_history_path(project_name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        temp_path = path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)

    def _get_next_twin_version(self, project_name):
        history = self._load_twin_history(project_name)
        return history["current_version"] + 1

    def _load_previous_twin(self, project_name):
        """Load the most recent previous twin version, if it exists."""
        history = self._load_twin_history(project_name)
        if history["current_version"] < 1:
            return None
        prev_v = history["current_version"]
        v_dir = self._get_project_versions_dir(project_name)
        v_path = os.path.join(v_dir, f"v{prev_v}.json")
        if os.path.isfile(v_path):
            with open(v_path, encoding="utf-8") as f:
                return json.load(f)
        return None

    # --- Knowledge Memory ---

    def _capture_knowledge_memory(self, twin_data):
        """Capture knowledge memory snapshot from twin data."""
        classification = twin_data.get("project", {}).get("classification", {})
        return {
            "summary": twin_data.get("architect_summary", ""),
            "purpose": twin_data.get("purpose_clues", {}).get("summary", ""),
            "classification": {
                "domain": classification.get("domain", ""),
                "confidence": classification.get("confidence", ""),
            },
            "architecture_observations": [
                {
                    "path": doc.get("path", ""),
                    "preview": doc.get("preview", "")[:120],
                }
                for doc in twin_data.get("documentation_categories", {})
                .get("architecture", [])
            ],
            "frameworks": twin_data.get("project", {}).get("frameworks", []),
            "languages": twin_data.get("project", {}).get("languages", []),
            "dependency_count": len(twin_data.get("dependencies", [])),
            "file_count": twin_data.get("statistics", {}).get("file_count", 0),
        }

    # --- Store & Index ---

    def _store_twin(self, project_name, twin_data):
        twins_dir = self._get_twins_dir()
        os.makedirs(twins_dir, exist_ok=True)
        twin_path = os.path.join(twins_dir, f"{project_name}.twin.json")
        temp_path = twin_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(twin_data, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, twin_path)
        return twin_path

    def _store_versioned_twin(self, project_name, twin_data, version):
        """Store a versioned copy of the twin in the project's versions directory."""
        v_dir = self._get_project_versions_dir(project_name)
        v_path = os.path.join(v_dir, f"v{version}.json")
        temp_path = v_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(twin_data, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, v_path)
        return v_path

    def _index_knowledge(self, project_name, twin_data):
        if not self.store:
            return
        path = twin_data.get("project", {}).get("path", project_name)
        doc_info = twin_data.get("documentation", {})
        config_info = twin_data.get("config_files", {})
        classification = twin_data.get("project", {}).get("classification", {})
        payload = {
            "discovery_type": "project_twin",
            "project_name": project_name,
            "project_type": twin_data.get("project", {}).get("type"),
            "languages": twin_data.get("project", {}).get("languages", []),
            "frameworks": twin_data.get("project", {}).get("frameworks", []),
            "dependencies": twin_data.get("dependencies", []),
            "file_count": twin_data.get("statistics", {}).get("file_count", 0),
            "has_git": twin_data.get("repository", {}).get("detected", False),
            "documentation_count": doc_info.get("count", 0),
            "readme_summary": doc_info.get("summary", ""),
            "config_file_count": config_info.get("count", 0),
            "ci_types": config_info.get("ci_types", []),
            "classification_domain": classification.get("domain", ""),
            "classification_confidence": classification.get("confidence", ""),
            "framework_tiers": twin_data.get("project", {}).get("framework_tiers", {}),
            "doc_categories": twin_data.get("documentation_categories", {}),
            "purpose_summary": twin_data.get("purpose_clues", {}).get("summary", ""),
            "architect_summary": twin_data.get("architect_summary", ""),
            "classification_evidence": classification.get("evidence", []),
            "twin_version": twin_data.get("twin_version", 0),
            "fingerprint": twin_data.get("fingerprint", ""),
            "previous_fingerprint": twin_data.get("previous_fingerprint", ""),
            "twin_data": twin_data,
        }
        self.store.record_event("PROJECT_TWIN_DISCOVERED", path, payload)

    # --- Main discovery ---

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

        # Enhance connector output with improved intelligence
        enhance_intelligence(discovery)

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

        doc_info = discovery.get("documentation", {})
        if doc_info.get("count", 0):
            self._publish(TWIN_DOCUMENTATION, {
                "count": doc_info["count"],
                "summary": doc_info.get("summary", ""),
            })
            notifications.append({"type": "documentation", "message": "DOCUMENTATION DISCOVERED"})

        config_info = discovery.get("config_files", {})
        if config_info.get("count", 0):
            self._publish(TWIN_CONFIG, {
                "count": config_info["count"],
                "ci_types": config_info.get("ci_types", []),
            })
            notifications.append({"type": "config", "message": "CONFIGURATION DETECTED"})

        twin_data = dict(discovery)
        twin_data["discovery_time"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        twin_data["status"] = "CONNECTED"

        # --- Historical memory: version, fingerprint, knowledge memory ---
        previous_twin = self._load_previous_twin(project_name)
        if previous_twin:
            twin_data["previous_fingerprint"] = previous_twin.get("fingerprint", "")
            twin_data["twin_version"] = previous_twin.get("twin_version", 0) + 1
        else:
            twin_data["twin_version"] = 1
            twin_data["previous_fingerprint"] = ""

        twin_data["timestamp"] = twin_data["discovery_time"]
        twin_data["fingerprint"] = discovery.get("fingerprint", "")

        # Capture knowledge memory
        knowledge_memory = self._capture_knowledge_memory(twin_data)
        twin_data["knowledge_memory"] = knowledge_memory
        if previous_twin:
            prev_km = self._capture_knowledge_memory(previous_twin)
            twin_data["previous_knowledge_memory"] = prev_km
        else:
            twin_data["previous_knowledge_memory"] = None

        # Update history
        history = self._load_twin_history(project_name)
        version_entry = {
            "version": twin_data["twin_version"],
            "timestamp": twin_data["timestamp"],
            "fingerprint": twin_data["fingerprint"],
            "previous_fingerprint": twin_data["previous_fingerprint"],
        }
        history["versions"].append(version_entry)
        history["current_version"] = twin_data["twin_version"]
        self._save_twin_history(project_name, history)

        # Store versioned twin
        v_path = self._store_versioned_twin(project_name, twin_data, twin_data["twin_version"])

        twin_data["versioned_twin_path"] = v_path
        twin_path = self._store_twin(project_name, twin_data)
        self._index_knowledge(project_name, twin_data)

        self._publish(TWIN_VERSIONED, {
            "project_name": project_name,
            "twin_version": twin_data["twin_version"],
            "fingerprint": twin_data["fingerprint"],
            "has_changes": twin_data["fingerprint"] != twin_data["previous_fingerprint"],
        })
        notifications.append({
            "type": "twin_versioned",
            "message": f"VERSION {twin_data['twin_version']}",
        })

        self._publish(TWIN_CREATED, {
            "project_name": project_name,
            "twin_path": twin_path,
        })
        notifications.append({"type": "twin_created", "message": "PROJECT TWIN CREATED"})

        # Preserve enriched intelligence fields on the project dict
        # returned in the result.  The GUI reads project-level fields
        # (framework_tiers, classification) and discovery-level fields
        # (documentation_categories, architect_summary, purpose_clues,
        # tech_stack).  Although the enriched discovery dict already
        # carries these, we re-attach them explicitly so that any
        # serialisation or shallow-copy edge case is covered.
        _project = discovery.get("project")
        if _project is not None:
            _project["framework_tiers"] = _project.get("framework_tiers", {})
            _project["classification"] = _project.get("classification", {})

        result = {
            "project_name": project_name,
            "project_path": project_path,
            "discovery": discovery,
            "twin_path": twin_path,
            "twin_version": twin_data["twin_version"],
            "fingerprint": twin_data["fingerprint"],
            "previous_fingerprint": twin_data["previous_fingerprint"],
            "versioned_twin_path": v_path,
            "notifications": notifications,
            "status": "CONNECTED",
        }

        return result
