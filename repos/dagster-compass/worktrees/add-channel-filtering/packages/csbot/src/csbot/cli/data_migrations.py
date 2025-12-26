"""
Data migration CLI command

Provides CLI interface for running data migrations against a csbot configuration.
"""

import importlib.util
from pathlib import Path
from typing import Any

import click
from dotenv import find_dotenv, load_dotenv

from csbot.slackbot.bot_server.bot_server import create_secret_store
from csbot.slackbot.envelope_encryption import KekProvider
from csbot.slackbot.slackbot_core import load_bot_server_config_from_path
from csbot.slackbot.storage.data_migrations import DataMigration
from csbot.slackbot.storage.factory import create_connection_factory


def load_migration_from_file(migration_file: Path, **kwargs: Any) -> list[DataMigration]:
    """Load migration classes from a Python file.

    Args:
        migration_file: Path to Python file containing DataMigration subclasses
        **kwargs: Keyword arguments to pass to migration constructors

    Returns:
        List of instantiated migration objects
    """
    import inspect

    spec = importlib.util.spec_from_file_location("migration_module", migration_file)
    if spec is None or spec.loader is None:
        raise ValueError(f"Could not load migration file: {migration_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    migrations = []
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, type):
            # Check if it's a subclass of DataMigration by looking at the MRO
            try:
                # Look for DataMigration in the method resolution order
                is_data_migration_subclass = any(
                    base.__name__ == "DataMigration" for base in attr.__mro__
                )
                if is_data_migration_subclass and attr.__name__ != "DataMigration":
                    # Get the __init__ parameters
                    sig = inspect.signature(attr.__init__)
                    init_params = [
                        p.name
                        for p in sig.parameters.values()
                        if p.name not in ("self", "args", "kwargs")
                        and p.default == inspect.Parameter.empty
                    ]

                    # Verify all required parameters are provided
                    missing_params = [p for p in init_params if p not in kwargs]
                    if missing_params:
                        raise ValueError(
                            f"Migration {attr.__name__} requires parameters {missing_params} "
                            f"but they were not provided in kwargs"
                        )

                    # Extract only the parameters needed for this migration
                    migration_kwargs = {k: v for k, v in kwargs.items() if k in init_params}

                    migrations.append(attr(**migration_kwargs))
            except (TypeError, AttributeError):
                # Skip if there are issues with MRO inspection
                continue

    return migrations


def find_migration_by_name(migrations: list[DataMigration], name: str) -> DataMigration | None:
    """Find a migration by name from a list of migrations."""
    for migration in migrations:
        if migration.name == name:
            return migration
    return None


def _get_migrations(migration_file: str | None, **deps: Any) -> tuple[Path, list[DataMigration]]:
    """Load migrations from file and return path and migrations list."""
    # Determine migration file to use
    if migration_file:
        migration_file_path = Path(migration_file)
    else:
        # Default to data_migrations.py
        current_dir = Path(__file__).parent.parent / "slackbot" / "storage"
        migration_file_path = current_dir / "data_migrations.py"

    if not migration_file_path.exists():
        raise click.ClickException(f"Migration file not found: {migration_file_path}")

    # Load migrations from file
    try:
        migrations = load_migration_from_file(
            migration_file_path,
            **deps,
        )
    except Exception as e:
        raise click.ClickException(f"Error loading migrations from {migration_file_path}: {e}")

    return migration_file_path, migrations


@click.command(name="execute-data-migration")
@click.argument("config_file", type=click.Path(exists=True))
@click.argument("migration_names", nargs=-1, required=True)
@click.option(
    "--migration-file",
    type=click.Path(exists=True),
    help="Path to Python file containing migrations (defaults to data_migrations.py)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Check if migration would run without actually applying it",
)
def execute_data_migration(
    config_file: str,
    migration_names: tuple[str, ...],
    migration_file: str | None,
    dry_run: bool,
):
    """Execute one or more migrations.

    CONFIG_FILE: Path to csbot configuration YAML file (e.g., staging.csbot.config.yaml)
    MIGRATION_NAMES: Name(s) of the migration(s) to run

    Examples:
      # Run a single migration
      compass-dev data-migration execute staging.csbot.config.yaml populate_organizations_from_bot_instances

      # Run multiple migrations
      compass-dev data-migration execute staging.csbot.config.yaml migration1 migration2 migration3

      # Dry run to check if migration would apply
      compass-dev data-migration execute staging.csbot.config.yaml my_migration --dry-run
    """
    # Load environment variables
    load_dotenv(find_dotenv(usecwd=True), override=True)

    # Load bot configuration
    bot_config = load_bot_server_config_from_path(config_file)

    # Create database connection
    sql_conn_factory = create_connection_factory(
        bot_config.db_config.model_copy(update={"seed_database_from": None}),
    )

    kek_provider = KekProvider(bot_config.db_config.kek_config)
    secret_store = create_secret_store(bot_config)
    stripe_client = None

    with sql_conn_factory.with_conn() as conn:
        migration_file_path, migrations = _get_migrations(
            migration_file,
            kek_provider=kek_provider,
            secret_store=secret_store,
            stripe_client=stripe_client,
        )

        # Process each migration
        for migration_name in migration_names:
            # Find specific migration to run
            migration = find_migration_by_name(migrations, migration_name)
            if not migration:
                click.echo(f"Error: Migration '{migration_name}' not found.", err=True)
                click.echo("Available migrations:")
                for m in migrations:
                    click.echo(f"  {m.name}")
                raise click.ClickException(f"Migration '{migration_name}' not found")

            # Check if needed
            if not migration.is_needed(conn):
                click.echo(f"Migration '{migration.name}' is not needed (conditions not met).")
                continue

            if dry_run:
                click.echo(f"DRY RUN: Migration '{migration.name}' would be applied.")
                click.echo(f"Description: {migration.description}")
                continue

            # Apply the migration
            click.echo(f"Applying migration: {migration.name}")
            click.echo(f"Description: {migration.description}")

            try:
                migration.apply(conn, bot_config)
                conn.commit()
                click.echo(f"✓ Successfully applied migration: {migration.name}")
            except Exception as e:
                conn.rollback()
                click.echo(f"✗ Migration failed: {e}", err=True)
                raise
