from connectors.manifest import ConnectorManifest
from connectors.exceptions import ConnectorValidationError

VALID_CAPABILITIES = {
    "filesystem", "git", "tasks", "commits", "issues", "documents",
    "chat", "email", "calendar", "mcp", "api", "database", "terminal",
    "logs", "artifacts", "knowledge", "network", "webhook",
}

VALID_OBSERVATION_SURFACES = {
    "native_connector", "mcp_server", "extension_sdk", "official_api",
    "webhook", "event_stream", "local_workspace", "git_repository",
    "project_files", "build_artifacts", "config_files", "logs",
    "local_database", "other",
}

VALID_PERMISSIONS = {
    "read", "write", "observe", "execute", "reason", "mirror", "sync",
}

REQUIRED_MANIFEST_FIELDS = {"connector_id", "name", "version"}


class CapabilityValidator:
    @staticmethod
    def validate_capability(capability: str) -> bool:
        if capability not in VALID_CAPABILITIES:
            raise ConnectorValidationError(
                f"Unknown capability: {capability}. "
                f"Valid: {', '.join(sorted(VALID_CAPABILITIES))}"
            )
        return True

    @staticmethod
    def validate_capabilities(capabilities: list) -> list[str]:
        errors = []
        for cap in capabilities:
            if cap not in VALID_CAPABILITIES:
                errors.append(f"Unknown capability: {cap}")
        return errors

    @staticmethod
    def check_required(connector, required: list[str]) -> list[str]:
        missing = [cap for cap in required if cap not in connector.capabilities]
        return missing


class PermissionValidator:
    @staticmethod
    def validate_permission(permission: str) -> bool:
        if permission not in VALID_PERMISSIONS:
            raise ConnectorValidationError(
                f"Unknown permission: {permission}. "
                f"Valid: {', '.join(sorted(VALID_PERMISSIONS))}"
            )
        return True

    @staticmethod
    def validate_permissions(permissions: list) -> list[str]:
        errors = []
        for perm in permissions:
            if perm not in VALID_PERMISSIONS:
                errors.append(f"Unknown permission: {perm}")
        return errors

    @staticmethod
    def check_required(connector, required: list[str]) -> list[str]:
        missing = [perm for perm in required if perm not in connector.permissions]
        return missing


class ManifestValidator:
    @staticmethod
    def validate(manifest: ConnectorManifest) -> list[str]:
        errors = []
        if not manifest.connector_id:
            errors.append("Manifest missing connector_id")
        if not manifest.name:
            errors.append("Manifest missing name")
        if not manifest.version:
            errors.append("Manifest missing version")
        cap_errors = CapabilityValidator.validate_capabilities(manifest.capabilities)
        errors.extend(cap_errors)
        perm_errors = PermissionValidator.validate_permissions(manifest.permissions)
        errors.extend(perm_errors)
        for surface in manifest.observation_surfaces:
            if surface not in VALID_OBSERVATION_SURFACES:
                errors.append(f"Unknown observation surface: {surface}")
        return errors
