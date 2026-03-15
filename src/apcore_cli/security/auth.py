"""API key authentication (FE-05)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apcore_cli.config import ConfigResolver


class AuthenticationError(Exception):
    pass


class AuthProvider:
    def __init__(self, config: ConfigResolver) -> None:
        self._config = config

    def get_api_key(self) -> str | None:
        result = self._config.resolve("auth.api_key", cli_flag="--api-key", env_var="APCORE_AUTH_API_KEY")
        if result is not None and (result.startswith("keyring:") or result.startswith("enc:")):
            result = self._config.encryptor.retrieve(result, "auth.api_key")
        return result

    def authenticate_request(self, headers: dict) -> dict:
        key = self.get_api_key()
        if key is None:
            raise AuthenticationError(
                "Remote registry requires authentication. "
                "Set --api-key, APCORE_AUTH_API_KEY, or auth.api_key in config."
            )
        headers["Authorization"] = f"Bearer {key}"
        return headers

    def handle_response(self, status_code: int) -> None:
        if status_code in (401, 403):
            raise AuthenticationError("Authentication failed. Verify your API key.")
