"""TwinComparisonService — detects changes between Project Twin snapshots.

Compares two twin snapshots and produces a structured diff covering:
- New files
- Removed files
- Changed architecture
- Changed dependencies
- Changed frameworks
- Documentation changes

Extends the v3.0.0 platform without modifying frozen components.
"""

from services.service import Service


class TwinComparisonService(Service):
    """Compares two Project Twin snapshots and produces a structured diff."""

    def __init__(self, kernel):
        super().__init__(kernel)

    def compare(self, old_twin, new_twin):
        """Compare two twin dicts and return structured diff result."""
        result = {
            "has_changes": False,
            "summary": [],
            "new_files": [],
            "removed_files": [],
            "changed_architecture": {},
            "changed_dependencies": {"added": [], "removed": []},
            "changed_frameworks": {"added": [], "removed": []},
            "documentation_changes": {"added": [], "removed": []},
            "classification_changed": False,
            "purpose_changed": False,
        }

        if old_twin is None or new_twin is None:
            result["summary"].append("No previous snapshot available for comparison.")
            return result

        # File comparison (via doc paths + config paths)
        old_files = self._extract_file_paths(old_twin)
        new_files = self._extract_file_paths(new_twin)
        added_files = sorted(new_files - old_files)
        removed_files = sorted(old_files - new_files)
        result["new_files"] = added_files
        result["removed_files"] = removed_files
        if added_files:
            result["summary"].append(f"{len(added_files)} new file(s)")
        if removed_files:
            result["summary"].append(f"{len(removed_files)} removed file(s)")

        # Dependency comparison
        old_deps = set(old_twin.get("dependencies", []))
        new_deps = set(new_twin.get("dependencies", []))
        result["changed_dependencies"]["added"] = sorted(new_deps - old_deps)
        result["changed_dependencies"]["removed"] = sorted(old_deps - new_deps)
        deps_added = result["changed_dependencies"]["added"]
        deps_removed = result["changed_dependencies"]["removed"]
        if deps_added:
            result["summary"].append(f"New dependencies: {', '.join(deps_added[:5])}")
        if deps_removed:
            result["summary"].append(f"Removed dependencies: {', '.join(deps_removed[:5])}")

        # Framework comparison
        old_fws = set(old_twin.get("project", {}).get("frameworks", []))
        new_fws = set(new_twin.get("project", {}).get("frameworks", []))
        result["changed_frameworks"]["added"] = sorted(new_fws - old_fws)
        result["changed_frameworks"]["removed"] = sorted(old_fws - new_fws)
        fws_added = result["changed_frameworks"]["added"]
        fws_removed = result["changed_frameworks"]["removed"]
        if fws_added:
            result["summary"].append(f"New frameworks: {', '.join(fws_added)}")
        if fws_removed:
            result["summary"].append(f"Removed frameworks: {', '.join(fws_removed)}")

        # Architecture comparison
        old_arch = self._extract_architecture(old_twin)
        new_arch = self._extract_architecture(new_twin)
        if old_arch != new_arch:
            result["changed_architecture"] = {
                "old": old_arch,
                "new": new_arch,
            }
            result["summary"].append("Architecture documentation changed")

        # Documentation comparison
        old_doc_paths = self._extract_doc_paths(old_twin)
        new_doc_paths = self._extract_doc_paths(new_twin)
        result["documentation_changes"]["added"] = sorted(new_doc_paths - old_doc_paths)
        result["documentation_changes"]["removed"] = sorted(old_doc_paths - new_doc_paths)
        docs_added = result["documentation_changes"]["added"]
        docs_removed = result["documentation_changes"]["removed"]
        if docs_added:
            result["summary"].append(f"New documentation: {', '.join(docs_added)}")
        if docs_removed:
            result["summary"].append(f"Removed documentation: {', '.join(docs_removed)}")

        # Classification comparison
        old_cls = old_twin.get("project", {}).get("classification", {})
        new_cls = new_twin.get("project", {}).get("classification", {})
        if old_cls.get("domain") != new_cls.get("domain"):
            result["classification_changed"] = True
            result["summary"].append(
                f"Domain changed from '{old_cls.get('domain', 'unknown')}' "
                f"to '{new_cls.get('domain', 'unknown')}'"
            )

        # Purpose comparison
        old_purpose = old_twin.get("purpose_clues", {}).get("summary", "")
        new_purpose = new_twin.get("purpose_clues", {}).get("summary", "")
        if old_purpose != new_purpose:
            result["purpose_changed"] = True
            result["summary"].append("Project purpose description changed")

        result["has_changes"] = bool(
            added_files or removed_files
            or deps_added or deps_removed
            or fws_added or fws_removed
            or old_arch != new_arch
            or docs_added or docs_removed
            or result["classification_changed"]
            or result["purpose_changed"]
        )

        return result

    def compare_versions(self, twins_dir, project_name, from_version, to_version):
        """Load two specific twin versions from disk and compare them."""
        import json
        import os

        def _load_version(ver):
            v_path = os.path.join(twins_dir, project_name, "versions", f"v{ver}.json")
            if not os.path.isfile(v_path):
                return None
            with open(v_path, encoding="utf-8") as f:
                return json.load(f)

        old_twin = _load_version(from_version) if from_version else None
        new_twin = _load_version(to_version)
        if new_twin is None:
            return {"error": f"Version v{to_version} not found for {project_name}"}

        comparison = self.compare(old_twin, new_twin)
        comparison["from_version"] = from_version or 0
        comparison["to_version"] = to_version
        comparison["project_name"] = project_name
        return comparison

    # --- Internal helpers ---

    def _extract_file_paths(self, twin):
        """Extract set of all known file paths from a twin snapshot."""
        paths = set()
        for doc in twin.get("documentation", {}).get("files", []):
            p = doc.get("path", "")
            if p:
                paths.add(p)
        for cfg in twin.get("config_files", {}).get("files", []):
            p = cfg.get("path", "")
            if p:
                paths.add(p)
        return paths

    def _extract_architecture(self, twin):
        """Extract architecture-relevant content from twin."""
        arch = {}
        cats = twin.get("documentation_categories", {})
        for doc in cats.get("architecture", []):
            arch[doc.get("path", "")] = doc.get("preview", "")[:100]
        return arch

    def _extract_doc_paths(self, twin):
        """Extract set of documentation file paths."""
        paths = set()
        for doc in twin.get("documentation", {}).get("files", []):
            roles_to_track = {"architecture", "readme", "changelog", "contributing"}
            if doc.get("role") in roles_to_track:
                p = doc.get("path", "")
                if p:
                    paths.add(p)
        return paths
