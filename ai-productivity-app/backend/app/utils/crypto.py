"""Cryptographic utilities for secure storage of secrets."""

import base64
import logging
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config import settings

logger = logging.getLogger(__name__)


class CryptoHelper:
    """Helper class for encrypting and decrypting sensitive configuration values."""

    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._init_encryption()

    def _init_encryption(self) -> None:
        """Initialize Fernet encryption with the configured secret."""
        try:
            # Use the existing SECRET_KEY from settings as the base
            secret_key = settings.secret_key.encode("utf-8")

            # Derive a proper encryption key using PBKDF2
            salt = b"config_encryption_salt"  # Fixed salt for consistency
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(secret_key))
            self._fernet = Fernet(key)

        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            self._fernet = None

    def encrypt(self, value: str) -> str:
        """Encrypt a string value.

        Args:
            value: The plaintext value to encrypt

        Returns:
            The encrypted value as a base64-encoded string

        Raises:
            ValueError: If encryption fails or is not available
        """
        if not self._fernet:
            raise ValueError("Encryption not available - failed to initialize")

        if not value:
            return value

        try:
            plaintext = value.encode("utf-8")
            encrypted = self._fernet.encrypt(plaintext)
            return base64.urlsafe_b64encode(encrypted).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to encrypt value: {e}")
            raise ValueError(f"Encryption failed: {e}")

    def decrypt(self, encrypted_value: str) -> str:
        """Decrypt an encrypted string value.

        Args:
            encrypted_value: The encrypted value as a base64-encoded string

        Returns:
            The decrypted plaintext value

        Raises:
            ValueError: If decryption fails or is not available
        """
        if not self._fernet:
            raise ValueError("Decryption not available - failed to initialize")

        if not encrypted_value:
            return encrypted_value

        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode("utf-8"))
            decrypted = self._fernet.decrypt(encrypted_bytes)
            return decrypted.decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to decrypt value: {e}")
            raise ValueError(f"Decryption failed: {e}")

    def is_available(self) -> bool:
        """Check if encryption is available."""
        return self._fernet is not None


# Module-level singleton instance
_crypto_helper = CryptoHelper()


def encrypt_secret(value: str) -> str:
    """Encrypt a secret value.

    Args:
        value: The plaintext secret to encrypt

    Returns:
        The encrypted secret as a base64-encoded string
    """
    return _crypto_helper.encrypt(value)


def decrypt_secret(encrypted_value: str) -> str:
    """Decrypt an encrypted secret value.

    Args:
        encrypted_value: The encrypted secret as a base64-encoded string

    Returns:
        The decrypted plaintext secret
    """
    return _crypto_helper.decrypt(encrypted_value)


def is_secret_key(key: str) -> bool:
    """Check if a configuration key should be treated as a secret.

    Args:
        key: The configuration key name

    Returns:
        True if the key should be encrypted, False otherwise
    """
    secret_patterns = ["_api_key", "_secret", "_token", "_password", "_credential"]
    key_lower = key.lower()
    return any(pattern in key_lower for pattern in secret_patterns)


def mask_secret_value(value: str) -> str:
    """Return a masked representation of a secret value for display.

    Args:
        value: The secret value to mask

    Returns:
        A masked string representation
    """
    if not value:
        return value

    if len(value) <= 8:
        return "***"

    # Show first 4 and last 4 characters with asterisks in between
    return f"{value[:4]}***{value[-4:]}"


def is_encryption_available() -> bool:
    """Check if encryption is available."""
    return _crypto_helper.is_available()
