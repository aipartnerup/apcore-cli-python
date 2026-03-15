"""Tests for ConfigEncryptor (FE-05)."""

import base64
from unittest.mock import MagicMock, patch

import pytest

from apcore_cli.security.config_encryptor import ConfigDecryptionError, ConfigEncryptor


class TestConfigEncryptor:
    def test_aes_roundtrip(self):
        enc = ConfigEncryptor()
        plaintext = "my_secret_api_key_12345"
        ciphertext = enc._aes_encrypt(plaintext)
        decrypted = enc._aes_decrypt(ciphertext)
        assert decrypted == plaintext

    def test_store_without_keyring(self):
        enc = ConfigEncryptor()
        with patch.object(enc, "_keyring_available", return_value=False):
            result = enc.store("auth.api_key", "secret123")
        assert result.startswith("enc:")

    def test_store_with_keyring(self):
        enc = ConfigEncryptor()
        mock_kr = MagicMock()
        with (
            patch.object(enc, "_keyring_available", return_value=True),
            patch.dict("sys.modules", {"keyring": mock_kr}),
        ):
            result = enc.store("auth.api_key", "secret123")
        assert result == "keyring:auth.api_key"

    def test_retrieve_enc_ref(self):
        enc = ConfigEncryptor()
        ct = enc._aes_encrypt("my_secret")
        enc_ref = f"enc:{base64.b64encode(ct).decode()}"
        result = enc.retrieve(enc_ref, "auth.api_key")
        assert result == "my_secret"

    def test_retrieve_plaintext(self):
        enc = ConfigEncryptor()
        result = enc.retrieve("plain_value", "some.key")
        assert result == "plain_value"

    def test_retrieve_corrupted_ciphertext(self):
        enc = ConfigEncryptor()
        bad_ct = base64.b64encode(b"corrupted_data").decode()
        with pytest.raises(ConfigDecryptionError, match="Failed to decrypt"):
            enc.retrieve(f"enc:{bad_ct}", "auth.api_key")

    def test_keyring_available_returns_bool(self):
        enc = ConfigEncryptor()
        result = enc._keyring_available()
        assert isinstance(result, bool)
