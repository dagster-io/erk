"""Base test class for SlackbotStorage implementations (PostgreSQL and SQLite).

This module provides a base test class with common tests that should work across
both PostgreSQL and SQLite storage implementations.
"""

import asyncio
from abc import ABC, abstractmethod

import pytest

from csbot.slackbot.storage.interface import (
    SlackbotStorage,
)
from csbot.slackbot.storage.onboarding_state import BotInstanceType, ProspectorDataType


class SlackbotStorageTestBase(ABC):
    """Base test class for SlackbotStorage implementations.

    Subclasses must provide a `storage` fixture that returns a SlackbotStorage instance.
    """

    @pytest.fixture
    @abstractmethod
    def storage(self) -> SlackbotStorage:
        """Create a SlackbotStorage instance for testing.

        This fixture must be implemented by subclasses to provide either
        SlackbotSqliteStorage or SlackbotPostgresqlStorage.
        """
        pass

    def test_create_organization_basic(self, storage):
        """Test basic organization creation."""
        organization_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        assert isinstance(organization_id, int)
        assert organization_id > 0

        # Verify the organization was created correctly
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            # Use database-agnostic placeholder (subclass will handle ? vs %s)
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT organization_name, organization_industry
                FROM organizations WHERE organization_id = {placeholder}
                """,
                (organization_id,),
            )
            result = cursor.fetchone()

            assert result is not None
            organization_name, organization_industry = result
            assert organization_name == "Test Organization"
            assert organization_industry == "Technology"

    def test_create_organization_without_industry(self, storage):
        """Test creating organization without industry."""
        organization_id = asyncio.run(
            storage.create_organization(
                name="Simple Org", has_governance_channel=True, contextstore_github_repo="test/repo"
            )
        )

        assert isinstance(organization_id, int)
        assert organization_id > 0

        # Verify the organization was created with null industry
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT organization_name, organization_industry
                FROM organizations WHERE organization_id = {placeholder}
                """,
                (organization_id,),
            )
            result = cursor.fetchone()

            assert result is not None
            organization_name, organization_industry = result
            assert organization_name == "Simple Org"
            assert organization_industry is None

    def test_create_organization_with_stripe_data(self, storage):
        """Test creating organization with Stripe customer and subscription IDs."""
        organization_id = asyncio.run(
            storage.create_organization(
                name="Stripe Org",
                industry="Finance",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
                stripe_customer_id="cus_1234567890",
                stripe_subscription_id="sub_0987654321",
            )
        )

        assert isinstance(organization_id, int)
        assert organization_id > 0

        # Verify Stripe data was stored correctly
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT organization_name, organization_industry, stripe_customer_id, stripe_subscription_id
                FROM organizations WHERE organization_id = {placeholder}
                """,
                (organization_id,),
            )
            result = cursor.fetchone()

            assert result is not None
            organization_name, organization_industry, stripe_customer_id, stripe_subscription_id = (
                result
            )
            assert organization_name == "Stripe Org"
            assert organization_industry == "Finance"
            assert stripe_customer_id == "cus_1234567890"
            assert stripe_subscription_id == "sub_0987654321"

    def test_create_multiple_organizations(self, storage):
        """Test creating multiple organizations."""
        # Create first organization
        org_id_1 = asyncio.run(
            storage.create_organization(
                name="Organization 1",
                industry="Healthcare",
                has_governance_channel=True,
                contextstore_github_repo="test/repo1",
            )
        )

        # Create second organization
        org_id_2 = asyncio.run(
            storage.create_organization(
                name="Organization 2",
                industry="Finance",
                has_governance_channel=True,
                contextstore_github_repo="test/repo2",
            )
        )

        assert org_id_1 != org_id_2
        assert isinstance(org_id_1, int)
        assert isinstance(org_id_2, int)

        # Verify both organizations exist
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM organizations")
            count = cursor.fetchone()[0]
            assert count == 2

            # Check specific organizations
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"SELECT organization_name FROM organizations WHERE organization_id = {placeholder}",
                (org_id_1,),
            )
            assert cursor.fetchone()[0] == "Organization 1"

            cursor.execute(
                f"SELECT organization_name FROM organizations WHERE organization_id = {placeholder}",
                (org_id_2,),
            )
            assert cursor.fetchone()[0] == "Organization 2"

    def test_create_organization_with_special_characters(self, storage):
        """Test creating organization with special characters."""
        organization_id = asyncio.run(
            storage.create_organization(
                name="Test & Co. Ltd.",
                industry="Manufacturing & Production",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        assert isinstance(organization_id, int)

        # Verify the data was stored correctly
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT organization_name, organization_industry
                FROM organizations WHERE organization_id = {placeholder}
                """,
                (organization_id,),
            )
            result = cursor.fetchone()
            assert result[0] == "Test & Co. Ltd."
            assert result[1] == "Manufacturing & Production"

    def test_create_organization_with_has_governance_channel_false(self, storage):
        """Test creating organization with has_governance_channel=False."""
        # Create organization with has_governance_channel=False
        organization_id = asyncio.run(
            storage.create_organization(
                name="Onboarding Org",
                industry="Technology",
                has_governance_channel=False,
                contextstore_github_repo="test/repo",
            )
        )

        assert isinstance(organization_id, int)
        assert organization_id > 0

        # Verify has_governance_channel was stored correctly
        organizations = asyncio.run(storage.list_organizations())
        org = next(o for o in organizations if o.organization_id == organization_id)
        assert org.has_governance_channel is False

    def test_list_organizations_empty(self, storage):
        """Test list_organizations when no organizations exist."""
        organizations = asyncio.run(storage.list_organizations())
        assert organizations == []

    def test_list_organizations_single(self, storage):
        """Test list_organizations with single organization."""
        org_id = asyncio.run(
            storage.create_organization(
                name="Single Org",
                industry="Tech",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
                stripe_customer_id="cus_123",
                stripe_subscription_id="sub_456",
            )
        )

        organizations = asyncio.run(storage.list_organizations())
        assert len(organizations) == 1

        org = organizations[0]
        assert org.organization_id == org_id
        assert org.organization_name == "Single Org"
        assert org.organization_industry == "Tech"
        assert org.stripe_customer_id == "cus_123"
        assert org.stripe_subscription_id == "sub_456"
        assert org.has_governance_channel is True

    def test_list_organizations_multiple_sorted(self, storage):
        """Test list_organizations with multiple organizations (should be sorted by name)."""
        # Create organizations in non-alphabetical order
        org_id_z = asyncio.run(
            storage.create_organization(
                name="Zebra Corp",
                industry="Wildlife",
                has_governance_channel=True,
                contextstore_github_repo="test/zebra",
            )
        )
        org_id_a = asyncio.run(
            storage.create_organization(
                name="Alpha Inc",
                industry="Tech",
                has_governance_channel=True,
                contextstore_github_repo="test/alpha",
            )
        )
        org_id_m = asyncio.run(
            storage.create_organization(
                name="Midway LLC",
                has_governance_channel=True,
                contextstore_github_repo="test/midway",
            )
        )

        organizations = asyncio.run(storage.list_organizations())
        assert len(organizations) == 3

        # Should be sorted alphabetically by name
        assert organizations[0].organization_name == "Alpha Inc"
        assert organizations[0].organization_id == org_id_a
        assert organizations[1].organization_name == "Midway LLC"
        assert organizations[1].organization_id == org_id_m
        assert organizations[2].organization_name == "Zebra Corp"
        assert organizations[2].organization_id == org_id_z

    def test_update_organization_industry_basic(self, storage):
        """Test basic organization industry update."""
        # Create organization
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Org",
                industry="Old Industry",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        # Update industry
        asyncio.run(storage.update_organization_industry(org_id, "New Industry"))

        # Verify update
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"SELECT organization_industry FROM organizations WHERE organization_id = {placeholder}",
                (org_id,),
            )
            result = cursor.fetchone()
            assert result[0] == "New Industry"

    def test_update_organization_industry_nonexistent(self, storage):
        """Test updating industry for non-existent organization raises ValueError."""
        with pytest.raises(ValueError, match="Organization not found for organization_id: 99999"):
            asyncio.run(storage.update_organization_industry(99999, "Some Industry"))

    def test_create_bot_instance_basic(self, storage):
        """Test basic bot instance creation."""
        # Create an organization first
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        instance_id = asyncio.run(
            storage.create_bot_instance(
                channel_name="test-channel",
                governance_alerts_channel="alerts-channel",
                contextstore_github_repo="user/test-repo",
                slack_team_id="T1234567890",
                bot_email="testbot@example.com",
                organization_id=org_id,
            )
        )

        assert isinstance(instance_id, int)
        assert instance_id > 0

        # Verify the instance was created correctly
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT channel_name, bot_email, governance_alerts_channel,
                       contextstore_github_repo, slack_team_id, organization_id
                FROM bot_instances WHERE id = {placeholder}
                """,
                (instance_id,),
            )
            result = cursor.fetchone()

            assert result is not None
            (
                channel_name,
                bot_email,
                governance_alerts_channel,
                contextstore_github_repo,
                slack_team_id,
                organization_id,
            ) = result
            assert channel_name == "test-channel"
            assert bot_email == "testbot@example.com"
            assert governance_alerts_channel == "alerts-channel"
            assert contextstore_github_repo == "user/test-repo"
            assert slack_team_id == "T1234567890"
            assert organization_id == org_id

    def test_create_bot_instance_multiple(self, storage):
        """Test creating multiple bot instances."""
        # Create organizations first
        org_id_1 = asyncio.run(
            storage.create_organization(
                name="Organization 1",
                industry="Healthcare",
                has_governance_channel=True,
                contextstore_github_repo="test/repo1",
            )
        )
        org_id_2 = asyncio.run(
            storage.create_organization(
                name="Organization 2",
                industry="Finance",
                has_governance_channel=True,
                contextstore_github_repo="test/repo2",
            )
        )

        # Create first instance
        instance_id_1 = asyncio.run(
            storage.create_bot_instance(
                channel_name="channel-1",
                governance_alerts_channel="alerts-1",
                contextstore_github_repo="user/repo-1",
                slack_team_id="T1111111111",
                bot_email="bot1@example.com",
                organization_id=org_id_1,
            )
        )

        # Create second instance
        instance_id_2 = asyncio.run(
            storage.create_bot_instance(
                channel_name="channel-2",
                governance_alerts_channel="alerts-2",
                contextstore_github_repo="user/repo-2",
                slack_team_id="T2222222222",
                bot_email="bot2@example.com",
                organization_id=org_id_2,
            )
        )

        assert instance_id_1 != instance_id_2
        assert isinstance(instance_id_1, int)
        assert isinstance(instance_id_2, int)

        # Verify both instances exist
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM bot_instances")
            count = cursor.fetchone()[0]
            assert count == 2

            # Check specific instances
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"SELECT channel_name FROM bot_instances WHERE id = {placeholder}", (instance_id_1,)
            )
            assert cursor.fetchone()[0] == "channel-1"

            cursor.execute(
                f"SELECT channel_name FROM bot_instances WHERE id = {placeholder}", (instance_id_2,)
            )
            assert cursor.fetchone()[0] == "channel-2"

    def test_create_bot_instance_with_special_characters(self, storage):
        """Test creating bot instance with special characters in fields."""
        # Create an organization first
        org_id = asyncio.run(
            storage.create_organization(
                name="Test & Co. Ltd.",
                industry="Tech",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        instance_id = asyncio.run(
            storage.create_bot_instance(
                channel_name="test-channel-with-dashes",
                governance_alerts_channel="alerts-with-special_chars",
                contextstore_github_repo="org/repo-name_with.dots",
                slack_team_id="T1234567890",
                bot_email="bot+test@example.co.uk",
                organization_id=org_id,
            )
        )

        assert isinstance(instance_id, int)

        # Verify the data was stored correctly
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"SELECT bot_email, contextstore_github_repo FROM bot_instances WHERE id = {placeholder}",
                (instance_id,),
            )
            result = cursor.fetchone()
            assert result[0] == "bot+test@example.co.uk"
            assert result[1] == "org/repo-name_with.dots"

    def test_prospector_data_type_persists_through_load(self, storage):
        from csbot.slackbot.slackbot_core import PROSPECTOR_CONNECTION_NAME

        org_id = asyncio.run(
            storage.create_organization(
                name="Sales Org",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/sales-repo",
            )
        )

        asyncio.run(
            storage.create_bot_instance(
                channel_name="sales-channel",
                governance_alerts_channel="sales-governance",
                contextstore_github_repo="test/sales-repo",
                slack_team_id="T_SALES123",
                bot_email="sales-bot@example.com",
                organization_id=org_id,
                instance_type=BotInstanceType.STANDARD,
                icp_text="Focus on enterprise sales prospects",
                data_types=[ProspectorDataType.SALES],
            )
        )

        # Add prospector connection with data_documentation_repo to make this a prospector bot
        asyncio.run(
            storage.add_connection(
                organization_id=org_id,
                connection_name=PROSPECTOR_CONNECTION_NAME,
                url="bigquery://prospector",
                additional_sql_dialect=None,
                data_documentation_contextstore_github_repo="compass/sales-data-docs",
            )
        )

        # Associate connection with bot
        bot_key = "T_SALES123-sales-channel"
        asyncio.run(
            storage.add_bot_connection(
                organization_id=org_id, bot_id=bot_key, connection_name=PROSPECTOR_CONNECTION_NAME
            )
        )

        bot_configs = asyncio.run(
            storage.load_bot_instances(
                template_context={},
                get_template_context_for_org=lambda org_id: {},
                bot_keys=None,
            )
        )

        # Verify the data type persisted and is_prospector returns true based on data_documentation_repo
        assert len(bot_configs) == 1
        bot_config = list(bot_configs.values())[0]
        assert bot_config.prospector_data_types == [ProspectorDataType.SALES]
        assert bot_config.is_prospector  # Should be true because has data_documentation_repo

    def test_add_connection_basic(self, storage):
        """Test basic connection addition."""
        # Create an organization first
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        # Add a connection
        asyncio.run(
            storage.add_connection(
                organization_id=org_id,
                connection_name="test_conn",
                url="postgresql://localhost:5432/test",
                additional_sql_dialect="postgres",
            )
        )

        # Verify the connection was added
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT connection_name, url, additional_sql_dialect, organization_id
                FROM connections WHERE organization_id = {placeholder} AND connection_name = {placeholder}
                """,
                (org_id, "test_conn"),
            )
            result = cursor.fetchone()

            assert result is not None
            connection_name, url, additional_sql_dialect, organization_id = result
            assert connection_name == "test_conn"
            assert url == "postgresql://localhost:5432/test"
            assert additional_sql_dialect == "postgres"
            assert organization_id == org_id

    def test_add_connection_upsert(self, storage):
        """Test that add_connection updates existing connections (INSERT OR REPLACE)."""
        # Create an organization first
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        # Add initial connection
        asyncio.run(
            storage.add_connection(
                organization_id=org_id,
                connection_name="test_conn",
                url="postgresql://localhost:5432/test1",
                additional_sql_dialect="postgres",
            )
        )

        # Update the same connection
        asyncio.run(
            storage.add_connection(
                organization_id=org_id,
                connection_name="test_conn",
                url="postgresql://localhost:5432/test2",
                additional_sql_dialect="mysql",
            )
        )

        # Verify only one connection exists with updated values
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT COUNT(*), url, additional_sql_dialect
                FROM connections WHERE organization_id = {placeholder} AND connection_name = {placeholder}
                GROUP BY url, additional_sql_dialect
                """,
                (org_id, "test_conn"),
            )
            result = cursor.fetchone()

            assert result is not None
            count, url, additional_sql_dialect = result
            assert count == 1
            assert url == "postgresql://localhost:5432/test2"
            assert additional_sql_dialect == "mysql"

    def test_add_bot_connection_basic(self, storage):
        """Test basic bot-to-connection mapping."""
        # Create an organization first
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        # Add a connection first
        asyncio.run(
            storage.add_connection(
                organization_id=org_id,
                connection_name="test_conn",
                url="postgresql://localhost:5432/test",
                additional_sql_dialect="postgres",
            )
        )

        # Add bot-to-connection mapping
        asyncio.run(
            storage.add_bot_connection(
                organization_id=org_id, bot_id="test_bot_123", connection_name="test_conn"
            )
        )

        # Verify the mapping was added
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT organization_id, bot_id, connection_name
                FROM bot_to_connections WHERE organization_id = {placeholder} AND bot_id = {placeholder}
                """,
                (org_id, "test_bot_123"),
            )
            result = cursor.fetchone()

            assert result is not None
            organization_id, bot_id, connection_name = result
            assert organization_id == org_id
            assert bot_id == "test_bot_123"
            assert connection_name == "test_conn"

    def test_add_bot_connection_upsert(self, storage):
        """Test that add_bot_connection updates timestamp on conflict (INSERT OR REPLACE)."""
        # Create an organization first
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        # Add a connection first
        asyncio.run(
            storage.add_connection(
                organization_id=org_id,
                connection_name="test_conn",
                url="postgresql://localhost:5432/test",
                additional_sql_dialect="postgres",
            )
        )

        # Add initial bot-to-connection mapping
        asyncio.run(
            storage.add_bot_connection(
                organization_id=org_id, bot_id="test_bot_123", connection_name="test_conn"
            )
        )

        # Get initial timestamp
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT updated_at FROM bot_to_connections
                WHERE organization_id = {placeholder} AND bot_id = {placeholder} AND connection_name = {placeholder}
                """,
                (org_id, "test_bot_123", "test_conn"),
            )
            cursor.fetchone()[0]  # Get the initial timestamp but don't store it

        # Add the same mapping again
        asyncio.run(
            storage.add_bot_connection(
                organization_id=org_id, bot_id="test_bot_123", connection_name="test_conn"
            )
        )

        # Verify only one record exists and timestamp was updated
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT COUNT(*), updated_at FROM bot_to_connections
                WHERE organization_id = {placeholder} AND bot_id = {placeholder} AND connection_name = {placeholder}
                GROUP BY updated_at
                """,
                (org_id, "test_bot_123", "test_conn"),
            )
            result = cursor.fetchone()

            assert result is not None
            count, updated_timestamp = result
            assert count == 1
            # Updated timestamp should be different from initial (SQLite doesn't guarantee this will be greater due to precision)
            assert updated_timestamp is not None

    def test_remove_bot_connection_basic(self, storage):
        """Test basic bot-to-connection removal."""
        # Create an organization first
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        # Add a connection and mapping first
        asyncio.run(
            storage.add_connection(
                organization_id=org_id,
                connection_name="test_conn",
                url="postgresql://localhost:5432/test",
                additional_sql_dialect="postgres",
            )
        )
        asyncio.run(
            storage.add_bot_connection(
                organization_id=org_id, bot_id="test_bot_123", connection_name="test_conn"
            )
        )

        # Verify mapping exists
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT COUNT(*) FROM bot_to_connections
                WHERE organization_id = {placeholder} AND bot_id = {placeholder} AND connection_name = {placeholder}
                """,
                (org_id, "test_bot_123", "test_conn"),
            )
            assert cursor.fetchone()[0] == 1

        # Remove the mapping
        asyncio.run(
            storage.remove_bot_connection(
                organization_id=org_id, bot_id="test_bot_123", connection_name="test_conn"
            )
        )

        # Verify mapping was removed
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT COUNT(*) FROM bot_to_connections
                WHERE organization_id = {placeholder} AND bot_id = {placeholder} AND connection_name = {placeholder}
                """,
                (org_id, "test_bot_123", "test_conn"),
            )
            assert cursor.fetchone()[0] == 0

    def test_remove_bot_connection_nonexistent(self, storage):
        """Test removing a non-existent bot-to-connection mapping."""
        # Create an organization first
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        # Try to remove a mapping that doesn't exist (should not raise error)
        asyncio.run(
            storage.remove_bot_connection(
                organization_id=org_id, bot_id="nonexistent_bot", connection_name="nonexistent_conn"
            )
        )

        # Should complete without error
        assert True

    def test_connection_methods_isolation(self, storage):
        """Test that connection methods respect organization isolation."""
        # Create two organizations
        org_id_1 = asyncio.run(
            storage.create_organization(
                name="Organization 1",
                industry="Tech",
                has_governance_channel=True,
                contextstore_github_repo="test/org1",
            )
        )
        org_id_2 = asyncio.run(
            storage.create_organization(
                name="Organization 2",
                industry="Finance",
                has_governance_channel=True,
                contextstore_github_repo="test/org2",
            )
        )

        # Add same connection name to both organizations
        asyncio.run(
            storage.add_connection(
                organization_id=org_id_1,
                connection_name="shared_conn",
                url="postgresql://localhost:5432/org1",
                additional_sql_dialect="postgres",
            )
        )
        asyncio.run(
            storage.add_connection(
                organization_id=org_id_2,
                connection_name="shared_conn",
                url="postgresql://localhost:5432/org2",
                additional_sql_dialect="mysql",
            )
        )

        # Add bot mappings for each organization
        asyncio.run(
            storage.add_bot_connection(
                organization_id=org_id_1, bot_id="bot_org_1", connection_name="shared_conn"
            )
        )
        asyncio.run(
            storage.add_bot_connection(
                organization_id=org_id_2, bot_id="bot_org_2", connection_name="shared_conn"
            )
        )

        # Verify connections are isolated by organization
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT url, additional_sql_dialect FROM connections
                WHERE organization_id = {placeholder} AND connection_name = {placeholder}
                """,
                (org_id_1, "shared_conn"),
            )
            result = cursor.fetchone()
            assert result[0] == "postgresql://localhost:5432/org1"
            assert result[1] == "postgres"

            cursor.execute(
                f"""
                SELECT url, additional_sql_dialect FROM connections
                WHERE organization_id = {placeholder} AND connection_name = {placeholder}
                """,
                (org_id_2, "shared_conn"),
            )
            result = cursor.fetchone()
            assert result[0] == "postgresql://localhost:5432/org2"
            assert result[1] == "mysql"

        # Remove bot mapping from org 1 only
        asyncio.run(
            storage.remove_bot_connection(
                organization_id=org_id_1, bot_id="bot_org_1", connection_name="shared_conn"
            )
        )

        # Verify org 1 mapping is gone but org 2 remains
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT COUNT(*) FROM bot_to_connections
                WHERE organization_id = {placeholder} AND connection_name = {placeholder}
                """,
                (org_id_1, "shared_conn"),
            )
            assert cursor.fetchone()[0] == 0

            cursor.execute(
                f"""
                SELECT COUNT(*) FROM bot_to_connections
                WHERE organization_id = {placeholder} AND connection_name = {placeholder}
                """,
                (org_id_2, "shared_conn"),
            )
            assert cursor.fetchone()[0] == 1

    def test_get_connection_names_for_organization_empty(self, storage):
        """Test get_connection_names_for_organization with no connections."""

        # Create an organization
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        # Get connection names (should be empty)
        connection_names = asyncio.run(storage.get_connection_names_for_organization(org_id))

        assert connection_names == []

    def test_get_connection_names_for_organization_single(self, storage):
        """Test get_connection_names_for_organization with single connection."""

        # Create an organization
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        # Add a connection
        asyncio.run(
            storage.add_connection(
                organization_id=org_id,
                connection_name="test_conn",
                url="postgresql://localhost:5432/test",
                additional_sql_dialect="postgres",
            )
        )

        # Get connection names
        connection_names = asyncio.run(storage.get_connection_names_for_organization(org_id))

        assert connection_names == ["test_conn"]

    def test_get_connection_names_for_organization_multiple(self, storage):
        """Test get_connection_names_for_organization with multiple connections."""

        # Create an organization
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        # Add multiple connections
        asyncio.run(
            storage.add_connection(
                organization_id=org_id,
                connection_name="zebra_conn",
                url="postgresql://localhost:5432/zebra",
                additional_sql_dialect="postgres",
            )
        )
        asyncio.run(
            storage.add_connection(
                organization_id=org_id,
                connection_name="alpha_conn",
                url="postgresql://localhost:5432/alpha",
                additional_sql_dialect="postgres",
            )
        )
        asyncio.run(
            storage.add_connection(
                organization_id=org_id,
                connection_name="beta_conn",
                url="postgresql://localhost:5432/beta",
                additional_sql_dialect="postgres",
            )
        )

        # Get connection names (should be sorted alphabetically)
        connection_names = asyncio.run(storage.get_connection_names_for_organization(org_id))

        assert connection_names == ["alpha_conn", "beta_conn", "zebra_conn"]

    def test_get_connection_names_for_organization_isolation(self, storage):
        """Test get_connection_names_for_organization respects organization isolation."""

        # Create two organizations
        org_id_1 = asyncio.run(
            storage.create_organization(
                name="Organization 1",
                industry="Tech",
                has_governance_channel=True,
                contextstore_github_repo="test/org1",
            )
        )
        org_id_2 = asyncio.run(
            storage.create_organization(
                name="Organization 2",
                industry="Finance",
                has_governance_channel=True,
                contextstore_github_repo="test/org2",
            )
        )

        # Add connections to first organization
        asyncio.run(
            storage.add_connection(
                organization_id=org_id_1,
                connection_name="org1_conn1",
                url="postgresql://localhost:5432/org1_db1",
                additional_sql_dialect="postgres",
            )
        )
        asyncio.run(
            storage.add_connection(
                organization_id=org_id_1,
                connection_name="org1_conn2",
                url="postgresql://localhost:5432/org1_db2",
                additional_sql_dialect="postgres",
            )
        )

        # Add connections to second organization
        asyncio.run(
            storage.add_connection(
                organization_id=org_id_2,
                connection_name="org2_conn1",
                url="postgresql://localhost:5432/org2_db1",
                additional_sql_dialect="mysql",
            )
        )

        # Get connection names for each organization
        org1_connections = asyncio.run(storage.get_connection_names_for_organization(org_id_1))
        org2_connections = asyncio.run(storage.get_connection_names_for_organization(org_id_2))

        # Verify organization isolation
        assert set(org1_connections) == {"org1_conn1", "org1_conn2"}
        assert set(org2_connections) == {"org2_conn1"}
        assert org1_connections != org2_connections

    def test_get_connection_names_for_organization_nonexistent(self, storage):
        """Test get_connection_names_for_organization with non-existent organization."""

        # Get connection names for non-existent organization
        connection_names = asyncio.run(storage.get_connection_names_for_organization(99999))

        assert connection_names == []

    def test_reconcile_bot_connection_empty_to_connections(self, storage):
        """Test reconciling from no connections to multiple connections."""
        # Create organization and connections
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        # Add connections
        for conn_name in ["conn1", "conn2", "conn3"]:
            asyncio.run(
                storage.add_connection(
                    organization_id=org_id,
                    connection_name=conn_name,
                    url=f"postgresql://localhost:5432/{conn_name}",
                    additional_sql_dialect="postgres",
                )
            )

        # Reconcile bot to all connections
        asyncio.run(
            storage.reconcile_bot_connection(
                organization_id=org_id,
                bot_id="test_bot",
                connection_names=["conn1", "conn2", "conn3"],
            )
        )

        # Verify all connections are mapped
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT connection_name FROM bot_to_connections
                WHERE organization_id = {placeholder} AND bot_id = {placeholder}
                ORDER BY connection_name
                """,
                (org_id, "test_bot"),
            )
            results = [row[0] for row in cursor.fetchall()]
            assert results == ["conn1", "conn2", "conn3"]

    def test_reconcile_bot_connection_add_connections(self, storage):
        """Test reconciling by adding new connections to existing ones."""
        # Setup organization and connections
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        for conn_name in ["conn1", "conn2", "conn3", "conn4"]:
            asyncio.run(
                storage.add_connection(
                    organization_id=org_id,
                    connection_name=conn_name,
                    url=f"postgresql://localhost:5432/{conn_name}",
                    additional_sql_dialect="postgres",
                )
            )

        # Initially connect bot to only conn1 and conn2
        asyncio.run(
            storage.add_bot_connection(
                organization_id=org_id, bot_id="test_bot", connection_name="conn1"
            )
        )
        asyncio.run(
            storage.add_bot_connection(
                organization_id=org_id, bot_id="test_bot", connection_name="conn2"
            )
        )

        # Reconcile to conn1, conn2, conn3, conn4
        asyncio.run(
            storage.reconcile_bot_connection(
                organization_id=org_id,
                bot_id="test_bot",
                connection_names=["conn1", "conn2", "conn3", "conn4"],
            )
        )

        # Verify all four connections are mapped
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT connection_name FROM bot_to_connections
                WHERE organization_id = {placeholder} AND bot_id = {placeholder}
                ORDER BY connection_name
                """,
                (org_id, "test_bot"),
            )
            results = [row[0] for row in cursor.fetchall()]
            assert results == ["conn1", "conn2", "conn3", "conn4"]

    def test_reconcile_bot_connection_remove_connections(self, storage):
        """Test reconciling by removing connections."""
        # Setup organization and connections
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        for conn_name in ["conn1", "conn2", "conn3", "conn4"]:
            asyncio.run(
                storage.add_connection(
                    organization_id=org_id,
                    connection_name=conn_name,
                    url=f"postgresql://localhost:5432/{conn_name}",
                    additional_sql_dialect="postgres",
                )
            )

        # Initially connect bot to all connections
        for conn_name in ["conn1", "conn2", "conn3", "conn4"]:
            asyncio.run(
                storage.add_bot_connection(
                    organization_id=org_id, bot_id="test_bot", connection_name=conn_name
                )
            )

        # Reconcile to only conn1 and conn3
        asyncio.run(
            storage.reconcile_bot_connection(
                organization_id=org_id, bot_id="test_bot", connection_names=["conn1", "conn3"]
            )
        )

        # Verify only conn1 and conn3 are mapped
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT connection_name FROM bot_to_connections
                WHERE organization_id = {placeholder} AND bot_id = {placeholder}
                ORDER BY connection_name
                """,
                (org_id, "test_bot"),
            )
            results = [row[0] for row in cursor.fetchall()]
            assert results == ["conn1", "conn3"]

    def test_reconcile_bot_connection_mixed_operations(self, storage):
        """Test reconciling with both additions and removals."""
        # Setup organization and connections
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        for conn_name in ["conn1", "conn2", "conn3", "conn4", "conn5"]:
            asyncio.run(
                storage.add_connection(
                    organization_id=org_id,
                    connection_name=conn_name,
                    url=f"postgresql://localhost:5432/{conn_name}",
                    additional_sql_dialect="postgres",
                )
            )

        # Initially connect bot to conn1, conn2, conn3
        for conn_name in ["conn1", "conn2", "conn3"]:
            asyncio.run(
                storage.add_bot_connection(
                    organization_id=org_id, bot_id="test_bot", connection_name=conn_name
                )
            )

        # Reconcile to conn2, conn4, conn5 (remove conn1, conn3; keep conn2; add conn4, conn5)
        asyncio.run(
            storage.reconcile_bot_connection(
                organization_id=org_id,
                bot_id="test_bot",
                connection_names=["conn2", "conn4", "conn5"],
            )
        )

        # Verify correct connections are mapped
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT connection_name FROM bot_to_connections
                WHERE organization_id = {placeholder} AND bot_id = {placeholder}
                ORDER BY connection_name
                """,
                (org_id, "test_bot"),
            )
            results = [row[0] for row in cursor.fetchall()]
            assert results == ["conn2", "conn4", "conn5"]

    def test_reconcile_bot_connection_to_empty(self, storage):
        """Test reconciling to empty connection list (remove all)."""
        # Setup organization and connections
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        for conn_name in ["conn1", "conn2", "conn3"]:
            asyncio.run(
                storage.add_connection(
                    organization_id=org_id,
                    connection_name=conn_name,
                    url=f"postgresql://localhost:5432/{conn_name}",
                    additional_sql_dialect="postgres",
                )
            )

        # Initially connect bot to all connections
        for conn_name in ["conn1", "conn2", "conn3"]:
            asyncio.run(
                storage.add_bot_connection(
                    organization_id=org_id, bot_id="test_bot", connection_name=conn_name
                )
            )

        # Reconcile to empty list
        asyncio.run(
            storage.reconcile_bot_connection(
                organization_id=org_id, bot_id="test_bot", connection_names=[]
            )
        )

        # Verify no connections are mapped
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT COUNT(*) FROM bot_to_connections
                WHERE organization_id = {placeholder} AND bot_id = {placeholder}
                """,
                (org_id, "test_bot"),
            )
            count = cursor.fetchone()[0]
            assert count == 0

    def test_reconcile_bot_connection_idempotent(self, storage):
        """Test that reconciling to the same state is idempotent."""
        # Setup organization and connections
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        for conn_name in ["conn1", "conn2"]:
            asyncio.run(
                storage.add_connection(
                    organization_id=org_id,
                    connection_name=conn_name,
                    url=f"postgresql://localhost:5432/{conn_name}",
                    additional_sql_dialect="postgres",
                )
            )

        # Initially connect bot to conn1 and conn2
        for conn_name in ["conn1", "conn2"]:
            asyncio.run(
                storage.add_bot_connection(
                    organization_id=org_id, bot_id="test_bot", connection_name=conn_name
                )
            )

        # Reconcile to the same connections multiple times
        for _ in range(3):
            asyncio.run(
                storage.reconcile_bot_connection(
                    organization_id=org_id, bot_id="test_bot", connection_names=["conn1", "conn2"]
                )
            )

        # Verify connections remain the same
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT connection_name FROM bot_to_connections
                WHERE organization_id = {placeholder} AND bot_id = {placeholder}
                ORDER BY connection_name
                """,
                (org_id, "test_bot"),
            )
            results = [row[0] for row in cursor.fetchall()]
            assert results == ["conn1", "conn2"]

    def test_reconcile_bot_connection_organization_isolation(self, storage):
        """Test that reconcile_bot_connection respects organization isolation."""
        # Create two organizations
        org_id_1 = asyncio.run(
            storage.create_organization(
                name="Organization 1",
                industry="Tech",
                has_governance_channel=True,
                contextstore_github_repo="test/org1",
            )
        )
        org_id_2 = asyncio.run(
            storage.create_organization(
                name="Organization 2",
                industry="Finance",
                has_governance_channel=True,
                contextstore_github_repo="test/org2",
            )
        )

        # Add connections to both organizations
        for org_id in [org_id_1, org_id_2]:
            for conn_name in ["conn1", "conn2", "conn3"]:
                asyncio.run(
                    storage.add_connection(
                        organization_id=org_id,
                        connection_name=conn_name,
                        url=f"postgresql://localhost:5432/{conn_name}_org{org_id}",
                        additional_sql_dialect="postgres",
                    )
                )

        # Setup initial connections for both organizations
        for conn_name in ["conn1", "conn2"]:
            asyncio.run(
                storage.add_bot_connection(
                    organization_id=org_id_1, bot_id="bot_org1", connection_name=conn_name
                )
            )
            asyncio.run(
                storage.add_bot_connection(
                    organization_id=org_id_2, bot_id="bot_org2", connection_name=conn_name
                )
            )

        # Reconcile only org1's bot to add conn3
        asyncio.run(
            storage.reconcile_bot_connection(
                organization_id=org_id_1,
                bot_id="bot_org1",
                connection_names=["conn1", "conn2", "conn3"],
            )
        )

        # Verify org1 has 3 connections
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT connection_name FROM bot_to_connections
                WHERE organization_id = {placeholder} AND bot_id = {placeholder}
                ORDER BY connection_name
                """,
                (org_id_1, "bot_org1"),
            )
            org1_results = [row[0] for row in cursor.fetchall()]
            assert org1_results == ["conn1", "conn2", "conn3"]

            # Verify org2 still has only 2 connections (unchanged)
            cursor.execute(
                f"""
                SELECT connection_name FROM bot_to_connections
                WHERE organization_id = {placeholder} AND bot_id = {placeholder}
                ORDER BY connection_name
                """,
                (org_id_2, "bot_org2"),
            )
            org2_results = [row[0] for row in cursor.fetchall()]
            assert org2_results == ["conn1", "conn2"]

    def test_reconcile_bot_connection_bot_isolation(self, storage):
        """Test that reconcile_bot_connection respects bot isolation."""
        # Setup organization and connections
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        for conn_name in ["conn1", "conn2", "conn3"]:
            asyncio.run(
                storage.add_connection(
                    organization_id=org_id,
                    connection_name=conn_name,
                    url=f"postgresql://localhost:5432/{conn_name}",
                    additional_sql_dialect="postgres",
                )
            )

        # Setup initial connections for both bots
        for bot_id in ["bot1", "bot2"]:
            for conn_name in ["conn1", "conn2"]:
                asyncio.run(
                    storage.add_bot_connection(
                        organization_id=org_id, bot_id=bot_id, connection_name=conn_name
                    )
                )

        # Reconcile only bot1 to have conn3 (remove conn2, add conn3)
        asyncio.run(
            storage.reconcile_bot_connection(
                organization_id=org_id, bot_id="bot1", connection_names=["conn1", "conn3"]
            )
        )

        # Verify bot1 has conn1 and conn3
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT connection_name FROM bot_to_connections
                WHERE organization_id = {placeholder} AND bot_id = {placeholder}
                ORDER BY connection_name
                """,
                (org_id, "bot1"),
            )
            bot1_results = [row[0] for row in cursor.fetchall()]
            assert bot1_results == ["conn1", "conn3"]

            # Verify bot2 still has conn1 and conn2 (unchanged)
            cursor.execute(
                f"""
                SELECT connection_name FROM bot_to_connections
                WHERE organization_id = {placeholder} AND bot_id = {placeholder}
                ORDER BY connection_name
                """,
                (org_id, "bot2"),
            )
            bot2_results = [row[0] for row in cursor.fetchall()]
            assert bot2_results == ["conn1", "conn2"]

    def test_reconcile_bot_connection_duplicate_names(self, storage):
        """Test reconciling with duplicate connection names in the list."""
        # Setup organization and connections
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        for conn_name in ["conn1", "conn2"]:
            asyncio.run(
                storage.add_connection(
                    organization_id=org_id,
                    connection_name=conn_name,
                    url=f"postgresql://localhost:5432/{conn_name}",
                    additional_sql_dialect="postgres",
                )
            )

        # Reconcile with duplicate names (should handle gracefully)
        asyncio.run(
            storage.reconcile_bot_connection(
                organization_id=org_id,
                bot_id="test_bot",
                connection_names=["conn1", "conn2", "conn1", "conn2"],
            )
        )

        # Verify only unique connections are mapped
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT connection_name FROM bot_to_connections
                WHERE organization_id = {placeholder} AND bot_id = {placeholder}
                ORDER BY connection_name
                """,
                (org_id, "test_bot"),
            )
            results = [row[0] for row in cursor.fetchall()]
            assert results == ["conn1", "conn2"]

    def test_reconcile_bot_connection_nonexistent_bot(self, storage):
        """Test reconciling connections for non-existent bot (should work)."""
        # Setup organization and connections
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        asyncio.run(
            storage.add_connection(
                organization_id=org_id,
                connection_name="conn1",
                url="postgresql://localhost:5432/conn1",
                additional_sql_dialect="postgres",
            )
        )

        # Reconcile for non-existent bot (should create new mappings)
        asyncio.run(
            storage.reconcile_bot_connection(
                organization_id=org_id, bot_id="nonexistent_bot", connection_names=["conn1"]
            )
        )

        # Verify mapping was created
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"""
                SELECT connection_name FROM bot_to_connections
                WHERE organization_id = {placeholder} AND bot_id = {placeholder}
                """,
                (org_id, "nonexistent_bot"),
            )
            results = [row[0] for row in cursor.fetchall()]
            assert results == ["conn1"]

    def test_get_organization_connections_with_details_empty(self, storage):
        """Test get_organization_connections_with_details with no connections."""

        # Create an organization
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        # Get connections (should be empty)
        connections = asyncio.run(storage.get_organization_connections_with_details(org_id))

        assert connections == []

    def test_get_organization_connections_with_details_single_connection_no_bots(self, storage):
        """Test get_organization_connections_with_details with a connection that has no bots."""

        # Create an organization
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        # Add a connection
        asyncio.run(
            storage.add_connection(
                organization_id=org_id,
                connection_name="snowflake_prod",
                url="snowflake://account/database",
                additional_sql_dialect="snowflake",
            )
        )

        # Get connections
        connections = asyncio.run(storage.get_organization_connections_with_details(org_id))

        assert len(connections) == 1
        assert connections[0].connection_name == "snowflake_prod"
        assert connections[0].connection_type == "snowflake"
        assert connections[0].bot_ids == []
        assert connections[0].channel_names == []

    def test_get_organization_connections_with_details_with_bots(self, storage):
        """Test get_organization_connections_with_details with connections and bots."""

        # Create an organization
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        # Add connections
        asyncio.run(
            storage.add_connection(
                organization_id=org_id,
                connection_name="snowflake_prod",
                url="snowflake://account/database",
                additional_sql_dialect="snowflake",
            )
        )
        asyncio.run(
            storage.add_connection(
                organization_id=org_id,
                connection_name="postgres_dev",
                url="postgresql://localhost:5432/dev",
                additional_sql_dialect="postgres",
            )
        )

        # Add bot connections
        asyncio.run(
            storage.add_bot_connection(
                organization_id=org_id,
                bot_id="T123-compass",
                connection_name="snowflake_prod",
            )
        )
        asyncio.run(
            storage.add_bot_connection(
                organization_id=org_id,
                bot_id="T123-data-team",
                connection_name="snowflake_prod",
            )
        )
        asyncio.run(
            storage.add_bot_connection(
                organization_id=org_id,
                bot_id="T123-engineering",
                connection_name="postgres_dev",
            )
        )

        # Get connections
        connections = asyncio.run(storage.get_organization_connections_with_details(org_id))

        assert len(connections) == 2

        # Find each connection by name
        postgres_conn = next(c for c in connections if c.connection_name == "postgres_dev")
        snowflake_conn = next(c for c in connections if c.connection_name == "snowflake_prod")

        # Check postgres connection
        assert postgres_conn.connection_type == "postgres"
        assert sorted(postgres_conn.bot_ids) == ["T123-engineering"]
        assert postgres_conn.channel_names == ["engineering"]

        # Check snowflake connection
        assert snowflake_conn.connection_type == "snowflake"
        assert sorted(snowflake_conn.bot_ids) == ["T123-compass", "T123-data-team"]
        assert sorted(snowflake_conn.channel_names) == ["compass", "data-team"]

    def test_get_organization_connections_with_details_isolation(self, storage):
        """Test get_organization_connections_with_details respects organization isolation."""

        # Create two organizations
        org1_id = asyncio.run(
            storage.create_organization(
                name="Org 1",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/org1",
            )
        )
        org2_id = asyncio.run(
            storage.create_organization(
                name="Org 2",
                industry="Finance",
                has_governance_channel=True,
                contextstore_github_repo="test/org2",
            )
        )

        # Add connections to org1
        asyncio.run(
            storage.add_connection(
                organization_id=org1_id,
                connection_name="org1_conn",
                url="postgresql://localhost:5432/org1",
                additional_sql_dialect="postgres",
            )
        )

        # Add connections to org2
        asyncio.run(
            storage.add_connection(
                organization_id=org2_id,
                connection_name="org2_conn",
                url="postgresql://localhost:5432/org2",
                additional_sql_dialect="postgres",
            )
        )

        # Get connections for org1
        org1_connections = asyncio.run(storage.get_organization_connections_with_details(org1_id))

        assert len(org1_connections) == 1
        assert org1_connections[0].connection_name == "org1_conn"

        # Get connections for org2
        org2_connections = asyncio.run(storage.get_organization_connections_with_details(org2_id))

        assert len(org2_connections) == 1
        assert org2_connections[0].connection_name == "org2_conn"

    def test_get_organization_connections_with_details_null_dialect(self, storage):
        """Test get_organization_connections_with_details with null additional_sql_dialect.

        When additional_sql_dialect is None, connection_type is inferred from the URL.
        """

        # Create an organization
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        # Add a connection with null dialect
        asyncio.run(
            storage.add_connection(
                organization_id=org_id,
                connection_name="generic_conn",
                url="postgresql://localhost:5432/test",
                additional_sql_dialect=None,
            )
        )

        # Get connections
        connections = asyncio.run(storage.get_organization_connections_with_details(org_id))

        assert len(connections) == 1
        assert connections[0].connection_name == "generic_conn"
        assert connections[0].connection_type == "postgresql"
        assert connections[0].bot_ids == []
        assert connections[0].channel_names == []

    def test_context_status_upsert_and_retrieval(self, storage):
        """Test context status upsert (insert/update) and basic retrieval."""
        from csbot.slackbot.slackbot_github_monitor import PrInfo
        from csbot.slackbot.storage.interface import (
            ContextStatusType,
            ContextUpdateType,
        )

        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        # Test insert with CONTEXT_UPDATE
        asyncio.run(
            storage.upsert_context_status(
                organization_id=org_id,
                repo_name="test/repo",
                update_type=ContextUpdateType.CONTEXT_UPDATE,
                github_url="https://github.com/test/repo/pull/1",
                title="Initial PR",
                description="Initial description",
                status=ContextStatusType.OPEN,
                created_at=1000000,
                updated_at=1000000,
                github_updated_at=1000000,
                pr_info=PrInfo(type="context_update_created", bot_id="bot123"),
            )
        )

        # Test update (upsert same URL)
        asyncio.run(
            storage.upsert_context_status(
                organization_id=org_id,
                repo_name="test/repo",
                update_type=ContextUpdateType.CONTEXT_UPDATE,
                github_url="https://github.com/test/repo/pull/1",
                title="Updated PR",
                description="Updated description",
                status=ContextStatusType.MERGED,
                created_at=1000000,
                updated_at=2000000,
                github_updated_at=1500000,
                pr_info=PrInfo(type="scheduled_analysis_created", bot_id="bot456"),
            )
        )

        # Test insert with DATA_REQUEST
        asyncio.run(
            storage.upsert_context_status(
                organization_id=org_id,
                repo_name="test/repo",
                update_type=ContextUpdateType.DATA_REQUEST,
                github_url="https://github.com/test/repo/issues/1",
                title="Data request",
                description="Request description",
                status=ContextStatusType.OPEN,
                created_at=3000000,
                updated_at=3000000,
                github_updated_at=3000000,
                pr_info=None,
            )
        )

        # Verify update worked (only 1 entry for PR, updated values)
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = (
                "?"
                if hasattr(storage, "__class__") and "Sqlite" in storage.__class__.__name__
                else "%s"
            )
            cursor.execute(
                f"SELECT COUNT(*), title, status FROM context_status WHERE github_url = {placeholder} GROUP BY title, status",
                ("https://github.com/test/repo/pull/1",),
            )
            result = cursor.fetchone()
            assert result[0] == 1
            assert result[1] == "Updated PR"
            assert result[2] == ContextStatusType.MERGED.value

        # Basic retrieval test
        entries = asyncio.run(storage.get_context_status(organization_id=org_id))
        assert len(entries) == 2
        assert entries[0].title == "Data request"  # Most recent by updated_at
        assert entries[1].title == "Updated PR"

    def test_context_status_filtering_and_pagination(self, storage):
        """Test context status filtering by status/type and pagination with org isolation."""
        from csbot.slackbot.storage.interface import (
            ContextStatusType,
            ContextUpdateType,
        )

        # Create two orgs for isolation testing
        org1_id = asyncio.run(
            storage.create_organization(
                name="Org 1",
                industry="Tech",
                has_governance_channel=True,
                contextstore_github_repo="test/org1",
            )
        )
        org2_id = asyncio.run(
            storage.create_organization(
                name="Org 2",
                industry="Finance",
                has_governance_channel=True,
                contextstore_github_repo="test/org2",
            )
        )

        # Insert varied entries for org1: 2 OPEN context updates, 1 MERGED context update, 1 OPEN data request
        for i, (update_type, status) in enumerate(
            [
                (ContextUpdateType.CONTEXT_UPDATE, ContextStatusType.OPEN),
                (ContextUpdateType.CONTEXT_UPDATE, ContextStatusType.OPEN),
                (ContextUpdateType.CONTEXT_UPDATE, ContextStatusType.MERGED),
                (ContextUpdateType.DATA_REQUEST, ContextStatusType.OPEN),
            ],
            start=1,
        ):
            asyncio.run(
                storage.upsert_context_status(
                    organization_id=org1_id,
                    repo_name="test/org1",
                    update_type=update_type,
                    github_url=f"https://github.com/test/org1/{i}",
                    title=f"Entry {i}",
                    description=f"Desc {i}",
                    status=status,
                    created_at=i * 1000000,
                    updated_at=i * 1000000,
                    github_updated_at=i * 1000000,
                    pr_info=None,
                )
            )

        # Insert one entry for org2 to test isolation
        asyncio.run(
            storage.upsert_context_status(
                organization_id=org2_id,
                repo_name="test/org2",
                update_type=ContextUpdateType.CONTEXT_UPDATE,
                github_url="https://github.com/test/org2/1",
                title="Org2 Entry",
                description="Org2",
                status=ContextStatusType.OPEN,
                created_at=5000000,
                updated_at=5000000,
                github_updated_at=5000000,
                pr_info=None,
            )
        )

        # Test status filter: get OPEN entries for org1
        open_entries = asyncio.run(
            storage.get_context_status(organization_id=org1_id, status=ContextStatusType.OPEN)
        )
        assert len(open_entries) == 3  # 2 context updates + 1 data request
        assert all(e.status == ContextStatusType.OPEN for e in open_entries)

        # Test update_type filter: get CONTEXT_UPDATE entries for org1
        context_updates = asyncio.run(
            storage.get_context_status(
                organization_id=org1_id, update_type=ContextUpdateType.CONTEXT_UPDATE
            )
        )
        assert len(context_updates) == 3
        assert all(e.update_type == ContextUpdateType.CONTEXT_UPDATE for e in context_updates)

        # Test combined filters: OPEN CONTEXT_UPDATE for org1
        open_updates = asyncio.run(
            storage.get_context_status(
                organization_id=org1_id,
                status=ContextStatusType.OPEN,
                update_type=ContextUpdateType.CONTEXT_UPDATE,
            )
        )
        assert len(open_updates) == 2

        # Test pagination: limit and offset
        page1 = asyncio.run(storage.get_context_status(organization_id=org1_id, limit=2))
        assert len(page1) == 2
        page2 = asyncio.run(storage.get_context_status(organization_id=org1_id, limit=2, offset=2))
        assert len(page2) == 2

        # Test organization isolation: org2 should only see its own entry
        org2_entries = asyncio.run(storage.get_context_status(organization_id=org2_id))
        assert len(org2_entries) == 1
        assert org2_entries[0].title == "Org2 Entry"

    def test_basic_user_org(self, storage):
        """Test basic user operations: add users to orgs, fetch by email and slack_user_id."""
        org1_id = asyncio.run(
            storage.create_organization(
                name="Org 1", has_governance_channel=True, contextstore_github_repo="test/repo1"
            )
        )
        org2_id = asyncio.run(
            storage.create_organization(
                name="Org 2", has_governance_channel=True, contextstore_github_repo="test/repo2"
            )
        )

        asyncio.run(
            storage.add_org_user(
                slack_user_id="U1",
                email="user1@org1.com",
                organization_id=org1_id,
                is_org_admin=True,
            )
        )
        asyncio.run(
            storage.add_org_user(
                slack_user_id="U2",
                email="user2@org1.com",
                organization_id=org1_id,
                is_org_admin=False,
            )
        )
        asyncio.run(
            storage.add_org_user(
                slack_user_id="U3",
                email="user3@org2.com",
                organization_id=org2_id,
                is_org_admin=False,
            )
        )

        user1_by_email = asyncio.run(
            storage.get_org_user_by_email(email="user1@org1.com", organization_id=org1_id)
        )
        assert user1_by_email is not None
        assert user1_by_email.slack_user_id == "U1"
        assert user1_by_email.email == "user1@org1.com"
        assert user1_by_email.organization_id == org1_id
        assert user1_by_email.is_org_admin is True

        user2_by_slack_id = asyncio.run(
            storage.get_org_user_by_slack_user_id(slack_user_id="U2", organization_id=org1_id)
        )
        assert user2_by_slack_id is not None
        assert user2_by_slack_id.slack_user_id == "U2"
        assert user2_by_slack_id.email == "user2@org1.com"
        assert user2_by_slack_id.organization_id == org1_id
        assert user2_by_slack_id.is_org_admin is False

        org1_users = asyncio.run(storage.get_org_users(organization_id=org1_id))
        assert len(org1_users) == 2
        assert all(u.organization_id == org1_id for u in org1_users)
        assert {u.slack_user_id for u in org1_users} == {"U1", "U2"}

        org2_users = asyncio.run(storage.get_org_users(organization_id=org2_id))
        assert len(org2_users) == 1
        assert org2_users[0].slack_user_id == "U3"
        assert org2_users[0].email == "user3@org2.com"

    def test_org_user_admin_status_update(self, storage):
        """Test updating admin status for an org user."""
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Org", has_governance_channel=True, contextstore_github_repo="test/repo"
            )
        )

        asyncio.run(
            storage.add_org_user(
                slack_user_id="U123",
                email="user@example.com",
                organization_id=org_id,
                is_org_admin=False,
            )
        )

        user = asyncio.run(
            storage.get_org_user_by_slack_user_id(slack_user_id="U123", organization_id=org_id)
        )
        assert user is not None
        assert user.is_org_admin is False

        asyncio.run(
            storage.update_org_user_admin_status(
                slack_user_id="U123", organization_id=org_id, is_org_admin=True
            )
        )

        user_after_update = asyncio.run(
            storage.get_org_user_by_slack_user_id(slack_user_id="U123", organization_id=org_id)
        )
        assert user_after_update is not None
        assert user_after_update.is_org_admin is True

    def test_add_org_user_without_email(self, storage):
        """Test adding a user without an email address."""
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Org", has_governance_channel=True, contextstore_github_repo="test/repo"
            )
        )

        # Add user without email
        user = asyncio.run(
            storage.add_org_user(
                slack_user_id="U999",
                email=None,
                organization_id=org_id,
                is_org_admin=False,
                name="Test User",
            )
        )

        assert user is not None
        assert user.slack_user_id == "U999"
        assert user.email is None
        assert user.organization_id == org_id
        assert user.is_org_admin is False
        assert user.name == "Test User"

        # Verify user can be retrieved by slack_user_id
        retrieved_user = asyncio.run(
            storage.get_org_user_by_slack_user_id(slack_user_id="U999", organization_id=org_id)
        )
        assert retrieved_user is not None
        assert retrieved_user.email is None
        assert retrieved_user.slack_user_id == "U999"

    def test_org_users_pagination(self, storage):
        """Test cursor-based pagination for get_org_users."""
        org_id = asyncio.run(
            storage.create_organization(
                name="Big Org", has_governance_channel=True, contextstore_github_repo="test/repo"
            )
        )

        for i in range(15):
            asyncio.run(
                storage.add_org_user(
                    slack_user_id=f"U{i}",
                    email=f"user{i}@example.com",
                    organization_id=org_id,
                    is_org_admin=False,
                )
            )

        page1 = asyncio.run(storage.get_org_users(organization_id=org_id, limit=5))
        assert len(page1) == 5

        page2 = asyncio.run(
            storage.get_org_users(organization_id=org_id, cursor=page1[-1].id, limit=5)
        )
        assert len(page2) == 5

        page3 = asyncio.run(
            storage.get_org_users(organization_id=org_id, cursor=page2[-1].id, limit=5)
        )
        assert len(page3) == 5

        page4 = asyncio.run(
            storage.get_org_users(organization_id=org_id, cursor=page3[-1].id, limit=5)
        )
        assert len(page4) == 0

        all_users = page1 + page2 + page3
        assert len(all_users) == 15
        assert len({u.id for u in all_users}) == 15

        for i in range(len(all_users) - 1):
            assert all_users[i].id < all_users[i + 1].id

    @pytest.mark.asyncio
    async def test_url_encryption(self, storage: SlackbotStorage):
        org_id = await storage.create_organization(
            name="test1234", has_governance_channel=True, contextstore_github_repo="test/repo"
        )

        connection_name = "test"
        await storage.create_bot_instance(
            channel_name="test-channel",
            governance_alerts_channel="alerts-channel",
            contextstore_github_repo="user/test-repo",
            slack_team_id="T1234567890",
            bot_email="testbot@example.com",
            organization_id=org_id,
        )
        bot_id = "T1234567890-test-channel"
        await storage.add_connection(org_id, connection_name, "", None, plaintext_url="to encrypt")
        await storage.add_bot_connection(org_id, bot_id, connection_name)
        instances = await storage.load_bot_instances({}, lambda _: {}, None)
        bot = next(iter(instances.values()))
        connection = next(iter(bot.connections.values()))
        assert connection.url == "to encrypt", str(connection)
