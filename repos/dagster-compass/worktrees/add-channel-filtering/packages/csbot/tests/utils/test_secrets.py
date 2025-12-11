"""Tests for csbot.utils.secrets module."""

import base64
import os
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from csbot.utils.secrets import decrypt_string, encrypt_string, get_secret_value, get_symmetric_key


class TestGetSymmetricKey:
    """Tests for get_symmetric_key function."""

    def test_get_symmetric_key_success(self):
        """Test successful retrieval and decoding of symmetric key."""
        # Generate a valid Fernet key for testing
        test_key = Fernet.generate_key()
        encoded_key = base64.urlsafe_b64encode(test_key).decode()

        with patch.dict(os.environ, {"SECRET_ENCRYPTION_KEY": encoded_key}):
            result = get_symmetric_key()
            assert result == test_key
            assert isinstance(result, bytes)

    def test_get_symmetric_key_missing_env_var(self):
        """Test error when SECRET_ENCRYPTION_KEY environment variable is not set."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ValueError, match="SECRET_ENCRYPTION_KEY environment variable not set"
            ):
                get_symmetric_key()

    def test_get_symmetric_key_invalid_base64(self):
        """Test error when SECRET_ENCRYPTION_KEY contains invalid base64."""
        with patch.dict(os.environ, {"SECRET_ENCRYPTION_KEY": "invalid-base64!@#"}):
            with pytest.raises(Exception):  # base64.urlsafe_b64decode will raise
                get_symmetric_key()


class TestGetSecretValue:
    """Tests for get_secret_value function."""

    @pytest.fixture
    def test_key_and_fernet(self):
        """Fixture providing a test key and Fernet instance."""
        key = Fernet.generate_key()
        fernet = Fernet(key)
        encoded_key = base64.urlsafe_b64encode(key).decode()
        return key, fernet, encoded_key

    def test_get_secret_value_success(self, test_key_and_fernet):
        """Test successful decryption of a secret value."""
        _, fernet, encoded_key = test_key_and_fernet

        # Encrypt a test secret
        test_secret = "my-secret-password"
        encrypted_secret = fernet.encrypt(test_secret.encode()).decode()

        with patch.dict(
            os.environ,
            {
                "SECRET_ENCRYPTION_KEY": encoded_key,
                "TEST_SECRET": encrypted_secret,
            },
        ):
            result = get_secret_value("TEST_SECRET")
            assert result.get_secret_value() == test_secret
            assert isinstance(result, SecretStr)

    def test_get_secret_value_missing_secret_env_var(self, test_key_and_fernet):
        """Test error when the requested secret environment variable is not set."""
        _, _, encoded_key = test_key_and_fernet

        with patch.dict(os.environ, {"SECRET_ENCRYPTION_KEY": encoded_key}):
            with pytest.raises(ValueError, match="Environment variable NONEXISTENT_SECRET not set"):
                get_secret_value("NONEXISTENT_SECRET")

    def test_get_secret_value_empty_secret_env_var(self, test_key_and_fernet):
        """Test error when the requested secret environment variable is empty."""
        _, _, encoded_key = test_key_and_fernet

        with patch.dict(
            os.environ,
            {
                "SECRET_ENCRYPTION_KEY": encoded_key,
                "EMPTY_SECRET": "",
            },
        ):
            with pytest.raises(ValueError, match="Environment variable EMPTY_SECRET not set"):
                get_secret_value("EMPTY_SECRET")

    def test_get_secret_value_missing_encryption_key(self):
        """Test error when SECRET_ENCRYPTION_KEY is missing."""
        with patch.dict(os.environ, {"TEST_SECRET": "some-encrypted-value"}, clear=True):
            with pytest.raises(
                ValueError, match="SECRET_ENCRYPTION_KEY environment variable not set"
            ):
                get_secret_value("TEST_SECRET")

    def test_get_secret_value_invalid_encrypted_data(self, test_key_and_fernet):
        """Test error when encrypted data is invalid."""
        _, _, encoded_key = test_key_and_fernet

        with patch.dict(
            os.environ,
            {
                "SECRET_ENCRYPTION_KEY": encoded_key,
                "INVALID_SECRET": "not-encrypted-data",
            },
        ):
            with pytest.raises(ValueError, match="Failed to decrypt secret INVALID_SECRET"):
                get_secret_value("INVALID_SECRET")

    def test_get_secret_value_wrong_key(self):
        """Test error when trying to decrypt with wrong key."""
        # Create two different keys
        key1 = Fernet.generate_key()
        key2 = Fernet.generate_key()
        fernet1 = Fernet(key1)

        # Encrypt with first key
        test_secret = "my-secret"
        encrypted_with_key1 = fernet1.encrypt(test_secret.encode()).decode()

        # Try to decrypt with second key
        encoded_key2 = base64.urlsafe_b64encode(key2).decode()

        with patch.dict(
            os.environ,
            {
                "SECRET_ENCRYPTION_KEY": encoded_key2,
                "WRONG_KEY_SECRET": encrypted_with_key1,
            },
        ):
            with pytest.raises(ValueError, match="Failed to decrypt secret WRONG_KEY_SECRET"):
                get_secret_value("WRONG_KEY_SECRET")

    def test_get_secret_value_multiline_content(self, test_key_and_fernet):
        """Test successful decryption of multiline content."""
        _, fernet, encoded_key = test_key_and_fernet

        # Test with multiline content
        test_secret = "line1\nline2\nline3\n"
        encrypted_secret = fernet.encrypt(test_secret.encode()).decode()

        with patch.dict(
            os.environ,
            {
                "SECRET_ENCRYPTION_KEY": encoded_key,
                "MULTILINE_SECRET": encrypted_secret,
            },
        ):
            result = get_secret_value("MULTILINE_SECRET")
            assert result.get_secret_value() == test_secret


class TestEncryptString:
    """Tests for encrypt_string function."""

    def test_encrypt_string_success(self):
        """Test successful encryption of a string."""
        test_key = Fernet.generate_key()
        encoded_key = base64.urlsafe_b64encode(test_key).decode()

        with patch.dict(os.environ, {"SECRET_ENCRYPTION_KEY": encoded_key}):
            test_string = "my-secret-password"
            encrypted_string = encrypt_string(test_string)
            decrypted_string = decrypt_string(encrypted_string)
            assert encrypted_string != test_string
            assert decrypted_string == test_string
