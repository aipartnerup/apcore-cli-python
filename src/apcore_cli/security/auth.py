"""API key authentication (FE-05)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apcore_cli.config import ConfigResolver
    from apcore_cli.security.config_encryptor import ConfigEncryptor


class AuthenticationError(Exception):
    pass


class AuthProvider:
    """Resolve and authenticate API keys for remote registry calls.

    Audit D1-006 parity (v0.6.x): the optional `encryptor` parameter mirrors
    the TypeScript `AuthProvider(config, encryptor?)` constructor. When
    omitted, falls back to `config.encryptor` (if present) or constructs a
    `ConfigEncryptor()` lazily.
    """

    def __init__(
        self,
        config: ConfigResolver,
        encryptor: ConfigEncryptor | None = None,
    ) -> None:
        self._config = config
        self._encryptor = encryptor

    def _get_encryptor(self) -> ConfigEncryptor:
        if self._encryptor is not None:
            return self._encryptor
        existing = getattr(self._config, "encryptor", None)
        if existing is not None:
            return existing  # type: ignore[no-any-return]
        # Lazy construction — defer the import to avoid a hard cycle.
        from apcore_cli.security.config_encryptor import ConfigEncryptor as _ConfigEncryptor

        return _ConfigEncryptor()

    def get_api_key(self) -> str | None:
        result = self._config.resolve("auth.api_key", cli_flag="--api-key", env_var="APCORE_AUTH_API_KEY")
        if result is not None and (result.startswith("keyring:") or result.startswith("enc:")):
            from apcore_cli.security.config_encryptor import ConfigDecryptionError

            try:
                result = self._get_encryptor().retrieve(result, "auth.api_key")
            except ConfigDecryptionError as exc:
                raise AuthenticationError(
                    "Failed to decrypt stored API key. Re-configure with 'apcore-cli config set auth.api_key'."
                ) from exc
        return result

    def authenticate_request(self, headers: dict) -> dict:
        key = self.get_api_key()
        if key is None:
            raise AuthenticationError(
                "Remote registry requires authentication. "
                "Set --api-key, APCORE_AUTH_API_KEY, or auth.api_key in config."
            )
        if "\r" in key or "\n" in key:
            raise AuthenticationError(
                "Malformed API key: contains invalid characters (CR/LF). "
                "Re-configure with 'apcore-cli config set auth.api_key'."
            )
        headers["Authorization"] = f"Bearer {key.strip()}"
        return headers

    def handle_response(self, status_code: int) -> None:
        if status_code in (401, 403):
            raise AuthenticationError("Authentication failed. Verify your API key.")
