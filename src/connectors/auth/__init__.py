"""Connector Authentication Layer — secure credential providers.

Supports Personal Access Token, OAuth abstraction, API Key, and Bearer Token.
Credentials are never logged. Providers are configuration-only — no GUI login.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AuthConfig:
    provider: str = ""
    credentials: dict = field(default_factory=dict)


class ConnectorAuth:
    def __init__(self, config: Optional[AuthConfig] = None):
        self.config = config or AuthConfig()
        self._authenticated = False

    @property
    def authenticated(self) -> bool:
        return self._authenticated

    def authenticate(self) -> bool:
        raise NotImplementedError

    def get_headers(self) -> dict:
        raise NotImplementedError

    def sanitize(self) -> dict:
        return {"provider": self.config.provider, "authenticated": self._authenticated}

    def validate(self) -> list[str]:
        errors = []
        if not self.config.provider:
            errors.append("Auth provider not specified")
        return errors


class PATAuth(ConnectorAuth):
    def __init__(self, token: str = "", config: Optional[AuthConfig] = None):
        super().__init__(config)
        self._token = token

    def authenticate(self) -> bool:
        self._authenticated = bool(self._token)
        return self._authenticated

    def get_headers(self) -> dict:
        if not self._token:
            return {}
        return {"Authorization": f"Bearer {self._token}"}

    def sanitize(self) -> dict:
        return {"provider": "pat", "authenticated": self._authenticated, "token_present": bool(self._token)}


class OAuthAuth(ConnectorAuth):
    def __init__(self, access_token: str = "", refresh_token: str = "",
                 client_id: str = "", client_secret: str = "",
                 config: Optional[AuthConfig] = None):
        super().__init__(config)
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._client_id = client_id
        self._client_secret = client_secret

    def authenticate(self) -> bool:
        self._authenticated = bool(self._access_token)
        return self._authenticated

    def get_headers(self) -> dict:
        if not self._access_token:
            return {}
        return {"Authorization": f"Bearer {self._access_token}"}

    def sanitize(self) -> dict:
        return {"provider": "oauth", "authenticated": self._authenticated,
                "has_refresh": bool(self._refresh_token)}


class APIKeyAuth(ConnectorAuth):
    def __init__(self, api_key: str = "", header_name: str = "X-API-Key",
                 config: Optional[AuthConfig] = None):
        super().__init__(config)
        self._api_key = api_key
        self._header_name = header_name

    def authenticate(self) -> bool:
        self._authenticated = bool(self._api_key)
        return self._authenticated

    def get_headers(self) -> dict:
        if not self._api_key:
            return {}
        return {self._header_name: self._api_key}

    def sanitize(self) -> dict:
        return {"provider": "api_key", "authenticated": self._authenticated,
                "header_name": self._header_name}


class BearerTokenAuth(ConnectorAuth):
    def __init__(self, token: str = "", config: Optional[AuthConfig] = None):
        super().__init__(config)
        self._token = token

    def authenticate(self) -> bool:
        self._authenticated = bool(self._token)
        return self._authenticated

    def get_headers(self) -> dict:
        if not self._token:
            return {}
        return {"Authorization": f"Bearer {self._token}"}

    def sanitize(self) -> dict:
        return {"provider": "bearer", "authenticated": self._authenticated,
                "token_present": bool(self._token)}
