"""Tests for AuthProvider (FE-05)."""

from unittest.mock import MagicMock

import pytest

from apcore_cli.security.auth import AuthenticationError, AuthProvider


def _make_config(api_key=None):
    config = MagicMock()
    config.resolve.return_value = api_key
    return config


class TestAuthProvider:
    def test_get_api_key_from_env(self):
        config = _make_config("abc123")
        auth = AuthProvider(config)
        assert auth.get_api_key() == "abc123"

    def test_get_api_key_none(self):
        config = _make_config(None)
        auth = AuthProvider(config)
        assert auth.get_api_key() is None

    def test_get_api_key_keyring_ref(self):
        config = _make_config("keyring:auth.api_key")
        encryptor = MagicMock()
        encryptor.retrieve.return_value = "decrypted_key"
        config.encryptor = encryptor
        auth = AuthProvider(config)
        assert auth.get_api_key() == "decrypted_key"

    def test_authenticate_request_adds_header(self):
        config = _make_config("abc123")
        auth = AuthProvider(config)
        headers = auth.authenticate_request({})
        assert headers["Authorization"] == "Bearer abc123"

    def test_authenticate_request_no_key_raises(self):
        config = _make_config(None)
        auth = AuthProvider(config)
        with pytest.raises(AuthenticationError, match="requires authentication"):
            auth.authenticate_request({})

    def test_handle_response_401(self):
        config = _make_config()
        auth = AuthProvider(config)
        with pytest.raises(AuthenticationError, match="Authentication failed"):
            auth.handle_response(401)

    def test_handle_response_403(self):
        config = _make_config()
        auth = AuthProvider(config)
        with pytest.raises(AuthenticationError, match="Authentication failed"):
            auth.handle_response(403)

    def test_handle_response_200(self):
        config = _make_config()
        auth = AuthProvider(config)
        auth.handle_response(200)  # No error

    def test_decryption_error_wrapped_as_authentication_error(self):
        """A-D-009: ConfigDecryptionError must not leak past AuthProvider boundary."""
        from apcore_cli.security.config_encryptor import ConfigDecryptionError

        config = _make_config("enc:v2:bad_payload")
        encryptor = MagicMock()
        encryptor.retrieve.side_effect = ConfigDecryptionError("bad decrypt")
        config.encryptor = encryptor
        auth = AuthProvider(config)
        # Must raise AuthenticationError, not ConfigDecryptionError
        with pytest.raises(AuthenticationError, match="Failed to decrypt"):
            auth.get_api_key()
