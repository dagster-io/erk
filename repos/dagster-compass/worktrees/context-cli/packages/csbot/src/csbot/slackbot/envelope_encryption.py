"""
Envelope encryption utilities for connection URLs.

This module implements envelope encryption using AWS KMS where:
1. A system-wide Data Encryption Key (DEK) is generated using KMS generate_data_key
2. Connection URLs are encrypted with the plaintext DEK
3. The encrypted DEK (ciphertext blob) is stored in the database
4. KMS decrypts the DEK when needed using the KMS key

This approach provides:
- AWS KMS manages the master key (no key material in our system)
- Key rotation through KMS without re-encrypting data
- Encryption context for additional security
- Local plaintext mode for development
"""

import base64
import sqlite3
from functools import cache
from typing import assert_never

import boto3
from cryptography.fernet import Fernet

from csbot.slackbot.config import AWSKmsConfig, KekConfig, PlaintextKekConfig, UnsupportedKekConfig
from csbot.slackbot.storage.utils import ConnectionType, is_postgresql
from csbot.utils.check_async_context import ensure_not_in_async_context


@cache
def boto3_client(kek_config: AWSKmsConfig):
    kwargs = {}
    if kek_config.endpoint_url:
        kwargs["endpoint_url"] = kek_config.endpoint_url
    if kek_config.aws_access_key_id and kek_config.aws_secret_access_key:
        kwargs["aws_access_key_id"] = kek_config.aws_access_key_id
        kwargs["aws_secret_access_key"] = kek_config.aws_secret_access_key
    return boto3.client(
        service_name="kms",
        region_name=kek_config.region,
        **kwargs,
    )


class KekProvider:
    """Provider for encrypting/decrypting DEKs using KMS or plaintext."""

    def __init__(self, kek_config: KekConfig):
        self.kek_config = kek_config

    def generate_data_key(self, organization_id: int) -> tuple[bytes, bytes]:
        """Generate a new data key for an organization.

        Args:
            organization_id: Organization ID for encryption context

        Returns:
            Tuple of (plaintext_dek, encrypted_dek) where both are raw bytes
        """
        ensure_not_in_async_context()
        if isinstance(self.kek_config, PlaintextKekConfig):
            plaintext_dek = Fernet.generate_key()
            kek = self.kek_config.key.get_secret_value().encode()
            fernet = Fernet(kek)
            encrypted_dek = fernet.encrypt(plaintext_dek)
            return base64.urlsafe_b64decode(plaintext_dek), base64.urlsafe_b64decode(encrypted_dek)
        elif isinstance(self.kek_config, AWSKmsConfig):
            client = boto3_client(self.kek_config)
            response = client.generate_data_key(
                KeyId=self.kek_config.kms_key_id,
                KeySpec="AES_256",
                EncryptionContext={"organization": str(organization_id)},
            )
            return response["Plaintext"], response["CiphertextBlob"]
        elif isinstance(self.kek_config, UnsupportedKekConfig):
            raise NotImplementedError
        else:
            assert_never(self.kek_config)

    def decrypt_data_key(self, encrypted_dek: bytes, organization_id: int) -> bytes:
        """Decrypt a data key for an organization.

        Args:
            encrypted_dek: The encrypted DEK (raw bytes)
            organization_id: Organization ID for encryption context

        Returns:
            Plaintext DEK (raw bytes)
        """
        if isinstance(self.kek_config, PlaintextKekConfig):
            kek = self.kek_config.key.get_secret_value().encode()
            fernet = Fernet(kek)
            return base64.urlsafe_b64decode(fernet.decrypt(base64.urlsafe_b64encode(encrypted_dek)))
        elif isinstance(self.kek_config, AWSKmsConfig):
            client = boto3_client(self.kek_config)
            response = client.decrypt(
                CiphertextBlob=encrypted_dek,
                KeyId=self.kek_config.kms_key_id,
                EncryptionContext={"organization": str(organization_id)},
            )
            return response["Plaintext"]
        else:
            raise ValueError(f"Unknown KEK config type: {type(self.kek_config)}")


def encrypt_url_with_dek(url: str, dek: bytes) -> str:
    """Encrypt a connection URL with a DEK.

    Args:
        url: The plaintext connection URL
        dek: The DEK to use for encryption (raw bytes)

    Returns:
        Base64-encoded encrypted URL
    """
    fernet = Fernet(base64.urlsafe_b64encode(dek))
    encrypted_url = fernet.encrypt(url.encode())
    return base64.urlsafe_b64encode(encrypted_url).decode()


def decrypt_url_with_dek(encrypted_url: str, dek: bytes) -> str:
    """Decrypt a connection URL using a DEK.

    Args:
        encrypted_url: Base64-encoded encrypted URL
        dek: The DEK to use for decryption (raw bytes)

    Returns:
        Decrypted plaintext URL
    """
    fernet = Fernet(base64.b64encode(dek))
    encrypted_url_bytes = base64.urlsafe_b64decode(encrypted_url.encode())
    return fernet.decrypt(encrypted_url_bytes).decode()


def encrypt_connection_url(url: str, dek: bytes) -> str:
    """Encrypt a connection URL using a DEK.

    Args:
        url: The plaintext connection URL
        dek: The DEK to use for encryption (raw bytes)

    Returns:
        Base64-encoded encrypted URL
    """
    return encrypt_url_with_dek(url, dek)


def decrypt_connection_url(encrypted_url: str, dek: bytes) -> str:
    """Decrypt a connection URL using a DEK.

    Args:
        encrypted_url: Base64-encoded encrypted URL
        dek: The DEK to use for decryption (raw bytes)

    Returns:
        Decrypted plaintext URL
    """
    return decrypt_url_with_dek(encrypted_url, dek)


def get_or_create_organization_dek(
    conn: ConnectionType, organization_id: int, kek_provider: KekProvider, auto_commit: bool = False
) -> bytes:
    """Get an organization's DEK, creating it if it doesn't exist.

    Uses KMS generate_data_key with encryption context {"organization": org_id}
    to create both plaintext and encrypted DEK in one call.
    The encrypted DEK is stored as raw bytes (BYTEA/BLOB) for KMS compatibility.

    Handles race conditions: if INSERT fails due to unique constraint violation,
    reads the value that was created by the concurrent winner.

    Args:
        conn: Database connection
        organization_id: Organization ID for encryption context and lookup
        kek_provider: Provider for generating/decrypting DEKs
        auto_commit: If True, commit after creating DEK. Default False.

    Returns:
        The plaintext DEK (raw bytes)
    """
    import psycopg.errors

    cursor = conn.cursor()

    if is_postgresql(conn):
        cursor.execute(
            "SELECT encrypted_dek FROM encrypted_deks WHERE organization_id = %s",
            (organization_id,),
        )  # type: ignore[arg-type]
    else:
        cursor.execute(
            "SELECT encrypted_dek FROM encrypted_deks WHERE organization_id = ?",
            (organization_id,),
        )  # type: ignore[arg-type]

    result = cursor.fetchone()

    if result:
        encrypted_dek_blob = result[0]
        return kek_provider.decrypt_data_key(encrypted_dek_blob, organization_id)
    else:
        plaintext_dek, encrypted_dek_blob = kek_provider.generate_data_key(organization_id)

        try:
            if is_postgresql(conn):
                cursor.execute(
                    "INSERT INTO encrypted_deks (organization_id, encrypted_dek) VALUES (%s, %s)",
                    (organization_id, encrypted_dek_blob),
                )  # type: ignore[arg-type]
            else:
                cursor.execute(
                    "INSERT INTO encrypted_deks (organization_id, encrypted_dek) VALUES (?, ?)",
                    (organization_id, encrypted_dek_blob),
                )  # type: ignore[arg-type]

            if auto_commit:
                conn.commit()

            return plaintext_dek
        except (psycopg.errors.UniqueViolation, sqlite3.IntegrityError):
            if auto_commit:
                conn.rollback()

            if is_postgresql(conn):
                cursor.execute(
                    "SELECT encrypted_dek FROM encrypted_deks WHERE organization_id = %s",
                    (organization_id,),
                )  # type: ignore[arg-type]
            else:
                cursor.execute(
                    "SELECT encrypted_dek FROM encrypted_deks WHERE organization_id = ?",
                    (organization_id,),
                )  # type: ignore[arg-type]

            result = cursor.fetchone()
            if not result:
                raise ValueError(
                    f"Race condition: DEK creation failed but no DEK found for org {organization_id}"
                )
            encrypted_dek_blob = result[0]
            return kek_provider.decrypt_data_key(encrypted_dek_blob, organization_id)
