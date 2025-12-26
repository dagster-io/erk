"""
Test cases for add_connections webapp functionality.

This module tests warehouse configuration URL serialization and deserialization.
"""

import unittest

from csbot.slackbot.webapp.add_connections.models import (
    BigQueryWarehouseConfig,
    CompassWarehouseConfig,
    JsonConfig,
    SnowflakePasswordCredential,
    SnowflakePrivateKeyCredential,
    SnowflakeWarehouseConfig,
    compass_warehouse_config_from_json_config,
)


class TestWarehouseConfigURLFormats(unittest.TestCase):
    """Test cases for warehouse configuration URL generation."""

    def _roundtrip(self, config: CompassWarehouseConfig):
        url = config.to_url()
        json_config = JsonConfig.from_url(url)
        warehouse_config = compass_warehouse_config_from_json_config(json_config)
        self.assertEqual(config, warehouse_config)

    def test_snowflake_password_url_with_database_and_schema(self):
        """Test Snowflake password authentication URL with database and schema."""
        password_cred = SnowflakePasswordCredential(type="password", password="mypassword")
        config = SnowflakeWarehouseConfig(
            account_id="abc12345",
            username="myuser",
            credential=password_cred,
            warehouse="MY_WAREHOUSE",
            role="MY_ROLE",
            region="us-east-1",
        )
        self._roundtrip(config)

    def test_snowflake_password_url_without_database_and_schema(self):
        """Test Snowflake password authentication URL without database and schema."""
        password_cred = SnowflakePasswordCredential(type="password", password="mypassword")
        config = SnowflakeWarehouseConfig(
            account_id="abc12345",
            username="myuser",
            credential=password_cred,
            warehouse="MY_WAREHOUSE",
            role="MY_ROLE",
            region="us-east-1",
        )

        self._roundtrip(config)

    def test_snowflake_password_url_with_database_only(self):
        """Test Snowflake password authentication URL with database only (no schema)."""
        password_cred = SnowflakePasswordCredential(type="password", password="mypassword")
        config = SnowflakeWarehouseConfig(
            account_id="abc12345",
            username="myuser",
            credential=password_cred,
            warehouse="MY_WAREHOUSE",
            role="MY_ROLE",
            region="us-east-1",
        )

        self._roundtrip(config)

    def test_snowflake_private_key_url_with_database_and_schema(self):
        """Test Snowflake private key authentication URL with database and schema."""
        private_key_cred = SnowflakePrivateKeyCredential(
            type="private_key",
            private_key_file="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----",
        )
        config = SnowflakeWarehouseConfig(
            account_id="abc12345",
            username="myuser",
            credential=private_key_cred,
            warehouse="MY_WAREHOUSE",
            role="MY_ROLE",
            region="us-east-1",
        )

        self._roundtrip(config)

    def test_snowflake_private_key_url_without_database_and_schema(self):
        """Test Snowflake private key authentication URL without database and schema."""
        private_key_cred = SnowflakePrivateKeyCredential(
            type="private_key",
            private_key_file="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----",
        )
        config = SnowflakeWarehouseConfig(
            account_id="abc12345",
            username="myuser",
            credential=private_key_cred,
            warehouse="MY_WAREHOUSE",
            role="MY_ROLE",
            region="us-east-1",
        )

        self._roundtrip(config)

    def test_snowflake_url_without_region(self):
        """Test Snowflake URL generation without region suffix."""
        password_cred = SnowflakePasswordCredential(type="password", password="mypassword")
        config = SnowflakeWarehouseConfig(
            account_id="abc12345",
            username="myuser",
            credential=password_cred,
            warehouse="MY_WAREHOUSE",
            role="MY_ROLE",
            region="",
        )

        self._roundtrip(config)

    def test_bigquery_url_format(self):
        """Test BigQuery URL generation."""
        service_account_json = """{
            "type": "service_account",
            "project_id": "my-project-123",
            "private_key_id": "key123",
            "private_key": "-----BEGIN PRIVATE KEY-----\\nMIIE...\\n-----END PRIVATE KEY-----\\n",
            "client_email": "test@my-project-123.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }"""

        config = BigQueryWarehouseConfig.from_location_and_service_account_json(
            location="us", service_account_json_string=service_account_json
        )

        self._roundtrip(config)

    def test_bigquery_url_format_with_different_location(self):
        """Test BigQuery URL generation with different location."""
        service_account_json = """{
            "type": "service_account",
            "project_id": "my-project-456",
            "private_key_id": "key456",
            "private_key": "-----BEGIN PRIVATE KEY-----\\nMIIE...\\n-----END PRIVATE KEY-----\\n",
            "client_email": "test@my-project-456.iam.gserviceaccount.com",
            "client_id": "987654321",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }"""

        config = BigQueryWarehouseConfig.from_location_and_service_account_json(
            location="europe-west1", service_account_json_string=service_account_json
        )

        self._roundtrip(config)

    def test_bigquery_invalid_service_account_json_raises_error(self):
        """Test that invalid service account JSON raises ValueError."""
        # Missing type field
        invalid_json = """{
            "project_id": "my-project-123",
            "private_key": "test-key"
        }"""

        with self.assertRaises(ValueError) as cm:
            BigQueryWarehouseConfig.from_location_and_service_account_json(
                location="us", service_account_json_string=invalid_json
            )

        self.assertIn("not a valid Google Cloud service account", str(cm.exception))

    def test_bigquery_missing_project_id_raises_error(self):
        """Test that service account JSON missing project_id raises ValueError."""
        invalid_json = """{
            "type": "service_account",
            "private_key": "test-key"
        }"""

        with self.assertRaises(ValueError) as cm:
            BigQueryWarehouseConfig.from_location_and_service_account_json(
                location="us", service_account_json_string=invalid_json
            )

        self.assertIn("project_id not found in service account JSON", str(cm.exception))

    def test_snowflake_url_without_region_field(self):
        """Test Snowflake URL generation when region is None."""
        password_cred = SnowflakePasswordCredential(type="password", password="mypassword")
        config = SnowflakeWarehouseConfig(
            account_id="abc12345",
            username="myuser",
            credential=password_cred,
            warehouse="MY_WAREHOUSE",
            role="MY_ROLE",
            region="",  # No region specified
        )

        self._roundtrip(config)

    def test_snowflake_private_key_url_without_region_field(self):
        """Test Snowflake private key URL generation when region is None."""
        private_key_cred = SnowflakePrivateKeyCredential(
            type="private_key",
            private_key_file="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----",
        )
        config = SnowflakeWarehouseConfig(
            account_id="abc12345",
            username="myuser",
            credential=private_key_cred,
            warehouse="MY_WAREHOUSE",
            role="MY_ROLE",
            region="",  # No region specified
        )

        self._roundtrip(config)

    def test_snowflake_url_minimal_config_no_region(self):
        """Test Snowflake URL generation with minimal config (no region, database, or schema)."""
        password_cred = SnowflakePasswordCredential(type="password", password="mypassword")
        config = SnowflakeWarehouseConfig(
            account_id="abc12345",
            username="myuser",
            credential=password_cred,
            warehouse="MY_WAREHOUSE",
            role="MY_ROLE",
            region="",
        )

        self._roundtrip(config)


if __name__ == "__main__":
    unittest.main()
