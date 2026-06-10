"""
Security module.
Handles encryption/decryption of AccessKey Secrets using Fernet (AES-128-CBC).
"""

import base64
import hashlib
from cryptography.fernet import Fernet, InvalidToken

from app.config import Config


class SecurityManager:
    """Manages encryption and decryption of sensitive data."""

    def __init__(self):
        self._fernet = self._create_fernet()

    def _create_fernet(self) -> Fernet:
        """
        Create Fernet instance from MASTER_KEY.
        Fernet requires a 32-byte URL-safe base64-encoded key.
        We derive it from the MASTER_KEY using SHA-256.
        """
        master_key = Config.MASTER_KEY.encode("utf-8")
        # Derive a 32-byte key using SHA-256
        derived = hashlib.sha256(master_key).digest()
        # Fernet needs url-safe base64 encoded 32 bytes
        fernet_key = base64.urlsafe_b64encode(derived)
        return Fernet(fernet_key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string. Returns base64-encoded ciphertext."""
        encrypted = self._fernet.encrypt(plaintext.encode("utf-8"))
        return encrypted.decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a base64-encoded ciphertext. Returns plaintext string."""
        try:
            decrypted = self._fernet.decrypt(ciphertext.encode("utf-8"))
            return decrypted.decode("utf-8")
        except (InvalidToken, Exception) as e:
            raise ValueError(f"Gagal dekripsi data: {e}")

    @staticmethod
    def mask_access_key_id(access_key_id: str) -> str:
        """
        Mask AccessKey ID for display.
        Example: LTAI5tAbCdEfGhIjKlMn -> LTAI****KlMn
        """
        if len(access_key_id) <= 8:
            return access_key_id[:2] + "****" + access_key_id[-2:]
        return access_key_id[:4] + "****" + access_key_id[-4:]

    @staticmethod
    def mask_secret(secret: str) -> str:
        """
        Mask AccessKey Secret for display.
        Never show full secret.
        """
        if len(secret) <= 6:
            return "******"
        return secret[:3] + "****" + secret[-3:]


# Singleton instance
security = SecurityManager()
