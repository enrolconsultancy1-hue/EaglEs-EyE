class ConnectorError(Exception):
    """Base exception for all connector framework errors."""

class ConnectorNotFoundError(ConnectorError):
    """Raised when a connector ID is not found in the registry."""

class ConnectorLoadError(ConnectorError):
    """Raised when a connector module cannot be loaded."""

class ConnectorManifestError(ConnectorError):
    """Raised when a connector manifest is invalid or missing."""

class ConnectorStateError(ConnectorError):
    """Raised when an operation is invalid for the current connector state."""

class ConnectorCapabilityError(ConnectorError):
    """Raised when a connector does not support a required capability."""

class ConnectorPermissionError(ConnectorError):
    """Raised when a connector lacks a required permission."""

class ConnectorHealthError(ConnectorError):
    """Raised when a connector health check fails."""

class ConnectorTimeoutError(ConnectorError):
    """Raised when a connector operation exceeds its timeout."""

class ConnectorDiscoveryError(ConnectorError):
    """Raised when connector discovery fails."""

class ConnectorRegistrationError(ConnectorError):
    """Raised when connector registration fails."""

class ConnectorValidationError(ConnectorError):
    """Raised when connector validation fails."""
