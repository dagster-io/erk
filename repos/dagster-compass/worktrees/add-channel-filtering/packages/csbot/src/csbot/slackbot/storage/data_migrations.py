"""
Data migration framework for database data transformations.

This module provides a framework for applying data migrations to database records,
separate from schema changes. Data migrations can transform existing data, clean up
inconsistencies, or populate new columns based on existing data.
"""

from abc import ABC, abstractmethod
from typing import Any

from csbot.slackbot.storage.utils import ConnectionType, is_postgresql


class DataMigration(ABC):
    """Base class for data migration operations.

    Data migrations are operations that transform existing data in the database,
    such as:
    - Populating new columns with calculated values
    - Cleaning up data inconsistencies
    - Migrating data formats
    - Removing obsolete records
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this migration."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this migration does."""
        pass

    @abstractmethod
    def is_needed(self, conn: ConnectionType) -> bool:
        """Check if this migration needs to be applied.

        Args:
            conn: Database connection

        Returns:
            True if migration should be applied, False if already done
        """
        pass

    @abstractmethod
    def apply(self, conn: ConnectionType, bot_config=None) -> None:
        """Apply the data migration.

        Args:
            conn: Database connection
            bot_config: Optional bot server configuration for migrations that need external dependencies

        Raises:
            Exception: If migration fails
        """
        pass

    def _execute_query(
        self, conn: ConnectionType, query: str, params: tuple[Any, ...] | None = None
    ) -> Any:
        """Execute a query with appropriate parameter binding."""
        cursor = conn.cursor()
        if is_postgresql(conn):
            if params:
                cursor.execute(query, params)  # type: ignore[arg-type]
            else:
                cursor.execute(query)  # type: ignore[arg-type]
        else:
            # SQLite uses ? parameters
            if params:
                # Convert %s to ? for SQLite
                sqlite_query = query.replace("%s", "?")
                cursor.execute(sqlite_query, params)  # type: ignore[arg-type]
            else:
                cursor.execute(query)  # type: ignore[arg-type]
        return cursor

    def _fetch_one(
        self, conn: ConnectionType, query: str, params: tuple[Any, ...] | None = None
    ) -> Any:
        """Execute query and fetch one result."""
        cursor = self._execute_query(conn, query, params)
        return cursor.fetchone()

    def _fetch_all(
        self, conn: ConnectionType, query: str, params: tuple[Any, ...] | None = None
    ) -> list[Any]:
        """Execute query and fetch all results."""
        cursor = self._execute_query(conn, query, params)
        return cursor.fetchall()


class PopulateOrganizationsFromBotInstances(DataMigration):
    """Migrate data from bot_instances to organizations table.

    This migration creates organization records for each existing bot instance,
    using the organization_name if available or deriving it from channel_name.
    It can only run if the organizations table is empty.
    """

    @property
    def name(self) -> str:
        return "populate_organizations_from_bot_instances"

    @property
    def description(self) -> str:
        return "Populate organizations table from existing bot_instances data"

    def is_needed(self, conn: ConnectionType) -> bool:
        """Check if migration is needed - organizations table must be empty."""
        # First check if organizations table has any data
        org_count = self._fetch_one(conn, "SELECT COUNT(*) FROM organizations")[0]
        if org_count > 0:
            return False

        # Check if there are bot instances to migrate
        instance_count = self._fetch_one(conn, "SELECT COUNT(*) FROM bot_instances")[0]
        return instance_count > 0

    def apply(self, conn: ConnectionType, bot_config=None) -> None:
        """Apply the migration."""
        # Double-check that organizations table is empty
        org_count = self._fetch_one(conn, "SELECT COUNT(*) FROM organizations")[0]
        if org_count > 0:
            raise Exception("Cannot run migration: organizations table is not empty")

        # Get all bot instances
        instances = self._fetch_all(
            conn, "SELECT id, channel_name, organization_name FROM bot_instances"
        )

        # Create organizations and update bot_instances
        for instance_id, channel_name, org_name in instances:
            # Use organization_name if available, otherwise derive from channel_name
            if org_name:
                final_org_name = org_name
            else:
                final_org_name = channel_name.replace("-", " ")

            # Insert new organization
            if is_postgresql(conn):
                cursor = self._execute_query(
                    conn,
                    "INSERT INTO organizations (organization_name, organization_industry) VALUES (%s, %s) RETURNING organization_id",
                    (final_org_name, ""),
                )
                org_id = cursor.fetchone()[0]
            else:
                # SQLite
                self._execute_query(
                    conn,
                    "INSERT INTO organizations (organization_name, organization_industry) VALUES (?, ?)",
                    (final_org_name, ""),
                )
                org_id = self._fetch_one(conn, "SELECT last_insert_rowid()")[0]

            # Update bot_instance to reference the new organization
            self._execute_query(
                conn,
                "UPDATE bot_instances SET organization_id = %s WHERE id = %s",
                (org_id, instance_id),
            )


class CreateStripeCustomersAndSubscriptions(DataMigration):
    """Create Stripe customers and subscriptions for organizations that don't have them.

    This migration creates a Stripe customer for each organization missing one, and
    subscribes them to the Free plan (product ID: prod_Swl8Ec25xkX2VE).

    Requires a Stripe client to be passed during initialization.
    """

    def __init__(self, stripe_client):
        """Initialize with a Stripe client.

        Args:
            stripe_client: StripeClientProtocol implementation for creating customers/subscriptions
        """
        self.stripe_client = stripe_client
        self.free_product_id = "prod_Swl8Ec25xkX2VE"  # Free plan product ID

    @property
    def name(self) -> str:
        return "create_stripe_customers_and_subscriptions"

    @property
    def description(self) -> str:
        return "Create Stripe customers and Free plan subscriptions for organizations missing them"

    def is_needed(self, conn: ConnectionType) -> bool:
        """Check if any organizations are missing Stripe customer or subscription IDs."""
        if not self.stripe_client:
            return False  # Can't run without Stripe client

        # Check for organizations missing stripe_customer_id or stripe_subscription_id
        missing_customers = self._fetch_one(
            conn, "SELECT COUNT(*) FROM organizations WHERE stripe_customer_id IS NULL"
        )[0]

        missing_subscriptions = self._fetch_one(
            conn, "SELECT COUNT(*) FROM organizations WHERE stripe_subscription_id IS NULL"
        )[0]

        return missing_customers > 0 or missing_subscriptions > 0

    def apply(self, conn: ConnectionType, bot_config=None) -> None:
        """Apply the migration by creating missing Stripe customers and subscriptions."""
        if not self.stripe_client:
            raise Exception("Cannot run migration: Stripe client is required")

        # Get all organizations that need Stripe setup
        organizations = self._fetch_all(
            conn,
            """
            SELECT organization_id, organization_name, stripe_customer_id, stripe_subscription_id
            FROM organizations
            WHERE stripe_customer_id IS NULL OR stripe_subscription_id IS NULL
            """,
        )

        for org_id, org_name, existing_customer_id, existing_subscription_id in organizations:
            try:
                customer_id = existing_customer_id

                # Create Stripe customer if missing
                if not customer_id:
                    # Use organization name as email placeholder since we don't have user emails
                    # In practice, this would ideally use a real contact email
                    placeholder_email = f"billing+{org_id}@compass-bot.com"

                    customer = self.stripe_client.create_customer(
                        organization_name=org_name,
                        organization_id=str(org_id),
                        email=placeholder_email,
                    )
                    customer_id = customer["id"]

                    # Update organization with customer ID
                    self._execute_query(
                        conn,
                        "UPDATE organizations SET stripe_customer_id = %s WHERE organization_id = %s",
                        (customer_id, org_id),
                    )

                # Create Free plan subscription if missing
                if not existing_subscription_id and customer_id:
                    subscription = self.stripe_client.create_subscription(
                        customer_id=customer_id, product_id=self.free_product_id
                    )
                    subscription_id = subscription["id"]

                    # Update organization with subscription ID
                    self._execute_query(
                        conn,
                        "UPDATE organizations SET stripe_subscription_id = %s WHERE organization_id = %s",
                        (subscription_id, org_id),
                    )

            except Exception as e:
                # Log error but continue with other organizations
                print(
                    f"Warning: Failed to create Stripe setup for organization {org_id} ({org_name}): {e}"
                )
                continue


class PopulateConnectionsOrganizationId(DataMigration):
    """Populate organization_id column in connections table based on bot_instances.

    This migration updates the connections table to include organization_id from
    the associated bot_instance record.
    """

    @property
    def name(self) -> str:
        return "populate_connections_organization_id"

    @property
    def description(self) -> str:
        return "Populate organization_id in connections table from bot_instances"

    def is_needed(self, conn: ConnectionType) -> bool:
        """Check if there are connections without organization_id that have a bot_instance."""
        # Check if there are connections with NULL organization_id that have valid bot_instance_id
        result = self._fetch_one(
            conn,
            """
            SELECT COUNT(*) FROM connections c
            JOIN bot_instances bi ON c.bot_instance_id = bi.id
            WHERE c.organization_id IS NULL AND bi.organization_id IS NOT NULL
            """,
        )
        return result[0] > 0

    def apply(self, conn: ConnectionType, bot_config=None) -> None:
        """Update connections with organization_id from their bot_instances."""
        # Update connections with organization_id from bot_instances
        self._execute_query(
            conn,
            """
            UPDATE connections
            SET organization_id = (
                SELECT bi.organization_id
                FROM bot_instances bi
                WHERE bi.id = connections.bot_instance_id
            )
            WHERE organization_id IS NULL
            AND bot_instance_id IN (
                SELECT id FROM bot_instances WHERE organization_id IS NOT NULL
            )
            """,
        )


class PopulateBotToConnections(DataMigration):
    """Populate bot_to_connections table with existing connection mappings.

    This migration creates bot_to_connections records for existing connections,
    using the bot_instance's channel_name as the bot_id.
    """

    @property
    def name(self) -> str:
        return "populate_bot_to_connections"

    @property
    def description(self) -> str:
        return "Populate bot_to_connections table from existing connections"

    def is_needed(self, conn: ConnectionType) -> bool:
        """Check if there are connections that don't have bot_to_connections mappings."""
        # Check if bot_to_connections table is empty but connections exist
        bot_connections_count = self._fetch_one(conn, "SELECT COUNT(*) FROM bot_to_connections")[0]
        if bot_connections_count > 0:
            return False

        # Check if there are connections to migrate
        connections_count = self._fetch_one(
            conn,
            """
            SELECT COUNT(*) FROM connections c
            JOIN bot_instances bi ON c.bot_instance_id = bi.id
            WHERE c.organization_id IS NOT NULL AND bi.organization_id IS NOT NULL
            """,
        )[0]
        return connections_count > 0

    def apply(self, conn: ConnectionType, bot_config=None) -> None:
        """Create bot_to_connections records for existing connections."""
        from csbot.utils.misc import normalize_channel_name

        # Get all connections with their bot instance info
        connections = self._fetch_all(
            conn,
            """
            SELECT c.connection_name, c.organization_id, bi.channel_name, bi.slack_team_id
            FROM connections c
            JOIN bot_instances bi ON c.bot_instance_id = bi.id
            WHERE c.organization_id IS NOT NULL AND bi.organization_id IS NOT NULL
            """,
        )

        # Insert bot_to_connections records
        for connection_name, org_id, channel_name, slack_team_id in connections:
            # Construct bot_id using the same logic as BotKey.to_bot_id()
            normalized_channel_name = normalize_channel_name(channel_name)
            bot_id = f"{slack_team_id}-{normalized_channel_name}"

            # Insert or update the bot_to_connections mapping
            if is_postgresql(conn):
                self._execute_query(
                    conn,
                    """
                    INSERT INTO bot_to_connections (organization_id, bot_id, connection_name)
                    VALUES (%s, %s, %s)

                    """,
                    (org_id, bot_id, connection_name),
                )
            else:
                # SQLite doesn't have ON CONFLICT DO UPDATE, use INSERT OR REPLACE
                self._execute_query(
                    conn,
                    """
                    INSERT INTO bot_to_connections
                    (organization_id, bot_id, connection_name, created_at, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (org_id, bot_id, connection_name),
                )


class PopulateOrganizationContextstoreRepo(DataMigration):
    """Populate contextstore_github_repo for organizations with NULL values.

    For each organization with a NULL contextstore_github_repo, find the first
    associated bot instance and copy its contextstore_github_repo value.
    """

    @property
    def name(self) -> str:
        return "populate_organization_contextstore_repo"

    @property
    def description(self) -> str:
        return "Populate contextstore_github_repo in organizations from bot_instances"

    def is_needed(self, conn: ConnectionType) -> bool:
        """Check if there are organizations with NULL contextstore_github_repo that have bot instances."""
        result = self._fetch_one(
            conn,
            """
            SELECT COUNT(*)
            FROM organizations o
            WHERE o.contextstore_github_repo IS NULL
            AND EXISTS (
                SELECT 1 FROM bot_instances bi
                WHERE bi.organization_id = o.organization_id
                AND bi.contextstore_github_repo IS NOT NULL
            )
            """,
        )
        return result[0] > 0

    def apply(self, conn: ConnectionType, bot_config=None) -> None:
        """Update organizations with contextstore_github_repo from their bot_instances."""
        self._execute_query(
            conn,
            """
            UPDATE organizations
            SET contextstore_github_repo = (
                SELECT bi.contextstore_github_repo
                FROM bot_instances bi
                WHERE bi.organization_id = organizations.organization_id
                AND bi.contextstore_github_repo IS NOT NULL
                LIMIT 1
            )
            WHERE organizations.contextstore_github_repo IS NULL
            AND EXISTS (
                SELECT 1 FROM bot_instances bi
                WHERE bi.organization_id = organizations.organization_id
                AND bi.contextstore_github_repo IS NOT NULL
            )
            """,
        )


class CreateOrganizationDeks(DataMigration):
    """Create DEKs for all organizations that don't have them.

    This migration ensures each organization has a DEK in the encrypted_deks table.
    Uses KMS encryption context {"organization": org_id} for additional security.
    Should be run before EncryptExistingConnectionUrls.

    Requires a KekProvider for encrypting DEKs with KMS.
    """

    def __init__(self, kek_provider):
        """Initialize with a KekProvider.

        Args:
            kek_provider: KekProvider instance for encrypting/decrypting DEKs
        """
        self.kek_provider = kek_provider

    @property
    def name(self) -> str:
        return "create_organization_deks"

    @property
    def description(self) -> str:
        return "Create per-organization DEKs for envelope encryption"

    def is_needed(self, conn: ConnectionType) -> bool:
        """Check if any organizations are missing DEKs."""
        if not self.kek_provider:
            return False

        result = self._fetch_one(
            conn,
            """
            SELECT COUNT(*) FROM organizations o
            WHERE NOT EXISTS (
                SELECT 1 FROM encrypted_deks e WHERE e.organization_id = o.organization_id
            )
            """,
        )
        return result[0] > 0

    def apply(self, conn: ConnectionType, bot_config=None) -> None:
        """Create DEKs for all organizations missing them."""
        if not self.kek_provider:
            raise Exception("Cannot run migration: KekProvider is required")

        from csbot.slackbot.envelope_encryption import get_or_create_organization_dek

        organizations = self._fetch_all(
            conn,
            """
            SELECT organization_id FROM organizations o
            WHERE NOT EXISTS (
                SELECT 1 FROM encrypted_deks e WHERE e.organization_id = o.organization_id
            )
            """,
        )

        for (organization_id,) in organizations:
            get_or_create_organization_dek(
                conn, organization_id, self.kek_provider, auto_commit=False
            )


class EncryptExistingConnectionUrls(DataMigration):
    """Encrypt existing connection URLs using envelope encryption.

    This migration reads plaintext URLs from the url column, renders any Jinja
    templates (using the SecretStore for secrets), encrypts them using per-organization
    DEKs, and stores the encrypted URLs.

    Assumes organization DEKs already exist (created by CreateOrganizationDeks migration).
    Requires a KekProvider (for decrypting DEKs) and a SecretStore (for rendering
    Jinja templates with secret access).
    """

    def __init__(self, kek_provider, secret_store):
        """Initialize with a KekProvider and SecretStore.

        Args:
            kek_provider: KekProvider instance for encrypting/decrypting DEKs
            secret_store: SecretStore instance for rendering Jinja templates
        """
        self.kek_provider = kek_provider
        self.secret_store = secret_store

    @property
    def name(self) -> str:
        return "encrypt_existing_connection_urls"

    @property
    def description(self) -> str:
        return "Encrypt existing connection URLs using envelope encryption"

    def is_needed(self, conn: ConnectionType) -> bool:
        """Check if there are connections with plaintext URLs that need encryption."""
        if not self.kek_provider:
            return False

        result = self._fetch_one(
            conn,
            """
            SELECT COUNT(*) FROM connections
            WHERE url IS NOT NULL AND encrypted_url IS NULL
            """,
        )
        return result[0] > 0

    def apply(self, conn: ConnectionType, bot_config=None) -> None:
        """Encrypt all plaintext connection URLs."""
        if not self.kek_provider:
            raise Exception("Cannot run migration: KekProvider is required")

        from pathlib import Path

        import jinja2

        from csbot.slackbot.envelope_encryption import (
            encrypt_connection_url,
            get_or_create_organization_dek,
        )
        from csbot.slackbot.slackbot_core import get_jinja_template_context_with_secret_store

        jinja_env = jinja2.Environment(loader=jinja2.BaseLoader(), undefined=jinja2.StrictUndefined)

        connections = self._fetch_all(
            conn,
            """
            SELECT c.id, c.url, c.organization_id
            FROM connections c
            WHERE c.url IS NOT NULL AND c.encrypted_url IS NULL
            """,
        )

        org_deks = {}
        for connection_id, url_template, organization_id in connections:
            if organization_id not in org_deks:
                org_deks[organization_id] = get_or_create_organization_dek(
                    conn, organization_id, self.kek_provider, auto_commit=False
                )

            dek = org_deks[organization_id]

            template_context = get_jinja_template_context_with_secret_store(
                Path.cwd(), self.secret_store, organization_id
            )
            rendered_url = jinja_env.from_string(url_template or "").render(template_context)

            encrypted_url = encrypt_connection_url(rendered_url, dek)

            self._execute_query(
                conn,
                "UPDATE connections SET encrypted_url = %s WHERE id = %s",
                (encrypted_url, connection_id),
            )


class PopulateProspectorConnectionsDataDocRepo(DataMigration):
    """Populate data_documentation_contextstore_github_repo for prospector bot connections.

    For connections belonging to prospector or community_prospector bot instances,
    set the data_documentation_contextstore_github_repo to point to the organization's
    contextstore_github_repo. This enables composite context store providers that merge
    the shared prospector dataset documentation with org-specific context.
    """

    @property
    def name(self) -> str:
        return "populate_prospector_connections_data_doc_repo"

    @property
    def description(self) -> str:
        return "Set data_documentation_contextstore_github_repo on prospector connections to org-level contextstore"

    def is_needed(self, conn: ConnectionType) -> bool:
        """Check if there are prospector connections without data_documentation_contextstore_github_repo."""
        result = self._fetch_one(
            conn,
            """
            SELECT COUNT(*)
            FROM connections c
            JOIN bot_to_connections btc ON c.connection_name = btc.connection_name AND c.organization_id = btc.organization_id
            JOIN bot_instances bi ON btc.bot_id = bi.slack_team_id || '-' || REPLACE(LOWER(bi.channel_name), '_', '-')
            JOIN organizations o ON bi.organization_id = o.organization_id
            WHERE bi.instance_type IN ('prospector', 'community_prospector')
            AND c.data_documentation_contextstore_github_repo IS NULL
            AND o.contextstore_github_repo IS NOT NULL
            """,
        )
        return result[0] > 0

    def apply(self, conn: ConnectionType, bot_config=None) -> None:
        """Update prospector connections with data_documentation_contextstore_github_repo from organizations."""
        # For each prospector bot instance, find its connections and update them
        prospector_instances = self._fetch_all(
            conn,
            """
            SELECT bi.id, bi.slack_team_id, bi.channel_name, bi.organization_id
            FROM bot_instances bi
            WHERE bi.instance_type IN ('prospector', 'community_prospector')
            """,
        )

        for instance_id, slack_team_id, channel_name, org_id in prospector_instances:
            # Get organization's contextstore repo
            org_contextstore = self._fetch_one(
                conn,
                "SELECT contextstore_github_repo FROM organizations WHERE organization_id = %s",
                (org_id,),
            )
            if not org_contextstore or not org_contextstore[0]:
                continue

            org_contextstore_repo = org_contextstore[0]

            # Construct bot_id using same logic as BotKey.to_bot_id()
            from csbot.utils.misc import normalize_channel_name

            normalized_channel_name = normalize_channel_name(channel_name)
            bot_id = f"{slack_team_id}-{normalized_channel_name}"

            # Update all connections for this bot to use the org's contextstore as data doc repo
            self._execute_query(
                conn,
                """
                UPDATE connections
                SET data_documentation_contextstore_github_repo = %s
                WHERE organization_id = %s
                AND connection_name IN (
                    SELECT connection_name FROM bot_to_connections
                    WHERE organization_id = %s AND bot_id = %s
                )
                AND data_documentation_contextstore_github_repo IS NULL
                """,
                (org_contextstore_repo, org_id, org_id, bot_id),
            )


class CreateProspectorOrgContextstoreRepos(DataMigration):
    """Create GitHub contextstore repositories for prospector organizations.

    For prospector organizations that don't have a contextstore_github_repo,
    create a new GitHub repository and update the organization record.

    This migration requires bot_config to be provided to apply() method, which
    contains GitHub auth, AI agent config, and other necessary dependencies.
    """

    @property
    def name(self) -> str:
        return "create_prospector_org_contextstore_repos"

    @property
    def description(self) -> str:
        return "Create GitHub contextstore repositories for prospector organizations without one"

    def is_needed(self, conn: ConnectionType) -> bool:
        """Check if there are prospector orgs without contextstore_github_repo."""
        result = self._fetch_one(
            conn,
            """
            SELECT COUNT(DISTINCT o.organization_id)
            FROM organizations o
            JOIN bot_instances bi ON bi.organization_id = o.organization_id
            WHERE bi.instance_type IN ('prospector', 'community_prospector')
            AND o.contextstore_github_repo IS NULL
            """,
        )
        return result[0] > 0

    def apply(self, conn: ConnectionType, bot_config=None) -> None:
        """Create contextstore repos for prospector orgs and update organization records."""
        if not bot_config:
            raise Exception(
                "Cannot run migration: bot_config is required. "
                "This migration needs GitHub auth, AI agent, and logger from bot configuration."
            )

        import logging

        from csbot.agents.factory import create_agent_from_config

        # Extract dependencies from bot_config
        github_auth_source = bot_config.github.get_auth_source()
        agent = create_agent_from_config(bot_config.ai_config)
        logger = logging.getLogger(__name__)

        # Import here to avoid circular dependencies
        import asyncio

        from csbot.local_context_store.github.api import (
            create_repository,
            initialize_contextstore_repository,
        )
        from csbot.slackbot.channel_bot.personalization import get_company_info_from_domain

        # Get all prospector organizations without contextstore repos
        prospector_orgs = self._fetch_all(
            conn,
            """
            SELECT DISTINCT o.organization_id, o.organization_name
            FROM organizations o
            JOIN bot_instances bi ON bi.organization_id = o.organization_id
            WHERE bi.instance_type IN ('prospector', 'community_prospector')
            AND o.contextstore_github_repo IS NULL
            """,
        )

        for org_id, org_name in prospector_orgs:
            try:
                # Generate team name from organization name (same logic as onboarding)
                from csbot.slackbot.slack_utils import generate_urlsafe_team_name

                team_name = generate_urlsafe_team_name(org_name)
                repo_name = f"{team_name}-context"

                logger.info(
                    f"Creating contextstore repository '{repo_name}' for prospector organization {org_id} ({org_name})"
                )

                # Create the GitHub repository
                create_repository(github_auth_source, repo_name)

                # Try to get company info from TOS records if available
                company_info = None
                tos_record = self._fetch_one(
                    conn,
                    "SELECT email FROM tos_records WHERE organization_id = %s ORDER BY accepted_at DESC LIMIT 1",
                    (org_id,),
                )

                if tos_record and tos_record[0]:
                    user_email = tos_record[0]
                    try:
                        email_domain = user_email.split("@")[1]

                        async def get_company_info_async():
                            return await get_company_info_from_domain(agent, email_domain)

                        company_info = asyncio.run(get_company_info_async())
                    except Exception as e:
                        logger.error(f"Failed to get company info for org {org_id}: {e}")

                # Initialize the repository with contextstore files
                project_name = f"{team_name}/compass"
                initialized_repo = initialize_contextstore_repository(
                    github_auth_source,
                    repo_name,
                    project_name,
                    "dagster-compass",
                    company_info,
                )

                contextstore_repo_path = initialized_repo.github_config.repo_name

                # Update organization with the new contextstore repo
                self._execute_query(
                    conn,
                    "UPDATE organizations SET contextstore_github_repo = %s WHERE organization_id = %s",
                    (contextstore_repo_path, org_id),
                )

                logger.info(
                    f"Successfully created contextstore repo '{contextstore_repo_path}' for organization {org_id}"
                )

            except Exception as e:
                # Log error but continue with other organizations
                logger.error(
                    f"Failed to create contextstore repo for organization {org_id} ({org_name}): {e}"
                )
                continue


class MigrationRunner:
    """Runs data migrations with proper error handling."""

    def __init__(self, conn: ConnectionType):
        self.conn = conn

    @staticmethod
    def get_all_migrations() -> list[DataMigration]:
        """Get all available data migrations in dependency order.

        Returns:
            List of migration instances in the order they should be applied
        """
        return [
            PopulateOrganizationsFromBotInstances(),
            PopulateConnectionsOrganizationId(),
            PopulateBotToConnections(),
            PopulateOrganizationContextstoreRepo(),
            PopulateProspectorConnectionsDataDocRepo(),
            CreateProspectorOrgContextstoreRepos(),
        ]

    def run_migration(
        self, migration: DataMigration, dry_run: bool = False, bot_config=None
    ) -> bool:
        """Run a single migration.

        Args:
            migration: The migration to run
            dry_run: If True, only check if migration is needed without applying
            bot_config: Optional bot configuration for migrations that need it

        Returns:
            True if migration was applied (or would be applied in dry run), False if not needed
        """
        # Check if migration thinks it's needed
        if not migration.is_needed(self.conn):
            return False

        if dry_run:
            return True

        try:
            migration.apply(self.conn, bot_config)
            self.conn.commit()
            return True
        except Exception:
            self.conn.rollback()
            raise

    def run_migrations(
        self, migrations: list[DataMigration], dry_run: bool = False, bot_config=None
    ) -> dict[str, bool]:
        """Run multiple migrations.

        Args:
            migrations: List of migrations to run
            dry_run: If True, only check which migrations would be applied
            bot_config: Optional bot configuration for migrations that need it

        Returns:
            Dict mapping migration names to whether they were applied
        """
        results = {}
        for migration in migrations:
            results[migration.name] = self.run_migration(migration, dry_run, bot_config)
        return results
