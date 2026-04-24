"""Encrypted configuration storage (FE-05)."""

from __future__ import annotations

import base64
import binascii
import hashlib
import logging
import os
import socket

from cryptography.exceptions import InvalidTag

logger = logging.getLogger("apcore_cli.security")


class ConfigDecryptionError(Exception):
    pass


class ConfigEncryptor:
    SERVICE_NAME = "apcore-cli"

    def store(self, key: str, value: str) -> str:
        if self._keyring_available():
            import keyring as kr

            kr.set_password(self.SERVICE_NAME, key, value)
            return f"keyring:{key}"
        else:
            logger.warning(
                "OS keyring unavailable. Falling back to file-based obfuscation "
                "with a host+user-derived key. This is NOT strong encryption: any "
                "local user who can read the config AND observe hostname+username "
                "can recover the value. Install a real keyring backend "
                "(macOS Keychain / GNOME Keyring / KWallet / Windows Credential "
                "Manager) for real protection."
            )
            ciphertext = self._aes_encrypt(value)
            return f"enc:{base64.b64encode(ciphertext).decode()}"

    def retrieve(self, config_value: str, key: str) -> str:
        if config_value.startswith("keyring:"):
            import keyring as kr

            ref_key = config_value[len("keyring:") :]
            result = kr.get_password(self.SERVICE_NAME, ref_key)
            if result is None:
                raise ConfigDecryptionError(f"Keyring entry not found for '{ref_key}'.")
            return result
        elif config_value.startswith("enc:"):
            try:
                ciphertext = base64.b64decode(config_value[len("enc:") :])
                return self._aes_decrypt(ciphertext)
            except (InvalidTag, ValueError, binascii.Error, UnicodeDecodeError) as exc:
                raise ConfigDecryptionError(
                    f"Failed to decrypt configuration value '{key}'. Re-configure with 'apcore-cli config set {key}'."
                ) from exc
        else:
            return config_value

    def _keyring_available(self) -> bool:
        try:
            import keyring as kr

            backend = kr.get_keyring()
            return not (
                hasattr(kr, "backends")
                and hasattr(kr.backends, "fail")
                and isinstance(backend, kr.backends.fail.Keyring)
            )
        except Exception:
            return False

    def _derive_key(self) -> bytes:
        hostname = socket.gethostname()
        username = os.getenv("USER", os.getenv("USERNAME", "unknown"))
        salt = b"apcore-cli-config-v1"
        material = f"{hostname}:{username}".encode()
        return hashlib.pbkdf2_hmac("sha256", material, salt, iterations=100_000)

    def _aes_encrypt(self, plaintext: str) -> bytes:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        key = self._derive_key()
        nonce = os.urandom(12)
        encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
        ct = encryptor.update(plaintext.encode("utf-8")) + encryptor.finalize()
        tag = encryptor.tag
        # Wire format: nonce(12) + tag(16) + ciphertext
        return nonce + tag + ct

    def _aes_decrypt(self, data: bytes) -> str:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        key = self._derive_key()
        nonce = data[:12]
        tag = data[12:28]
        ct = data[28:]
        decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
        plaintext = decryptor.update(ct) + decryptor.finalize()
        return plaintext.decode("utf-8")
