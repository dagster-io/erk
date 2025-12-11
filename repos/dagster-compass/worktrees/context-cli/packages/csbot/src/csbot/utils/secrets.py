import base64
import os

from cryptography.fernet import Fernet
from pydantic import SecretStr


def get_symmetric_key() -> bytes:
    """Retrieves the symmetric key from the SECRET_ENCRYPTION_KEY
    environment variable"""
    key_str = os.environ.get("SECRET_ENCRYPTION_KEY")
    if not key_str:
        raise ValueError("SECRET_ENCRYPTION_KEY environment variable not set")
    return base64.urlsafe_b64decode(key_str.encode())


def get_secret_value(secret_name: str) -> SecretStr:
    """Retrieves the secret value from the environment variable and decrypts it."""
    encrypted_value = os.environ.get(secret_name)
    if not encrypted_value:
        raise ValueError(f"Environment variable {secret_name} not set")

    key = get_symmetric_key()
    fernet = Fernet(key)

    try:
        decrypted_bytes = fernet.decrypt(encrypted_value.encode())
        return SecretStr(decrypted_bytes.decode())
    except Exception as e:
        raise ValueError(f"Failed to decrypt secret {secret_name}: {e}")


def encrypt_string(plaintext: str) -> str:
    """Encrypts a string using the SECRET_ENCRYPTION_KEY.

    Args:
        plaintext: The string to encrypt

    Returns:
        Base64-encoded encrypted string

    Raises:
        ValueError: If SECRET_ENCRYPTION_KEY is not set or encryption fails
    """
    key = get_symmetric_key()
    fernet = Fernet(key)

    try:
        encrypted_bytes = fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted_bytes).decode()
    except Exception as e:
        raise ValueError(f"Failed to encrypt string: {e}")


def decrypt_string(encrypted_value: str) -> str:
    """Decrypts a string using the SECRET_ENCRYPTION_KEY."""
    key = get_symmetric_key()
    fernet = Fernet(key)
    return fernet.decrypt(base64.urlsafe_b64decode(encrypted_value.encode())).decode()
