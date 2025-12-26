from urllib.parse import urlparse

from csbot.slackbot.config import DatabaseConfig, KekConfig
from csbot.slackbot.envelope_encryption import KekProvider

from ...utils.time import SecondsNow, system_seconds_now
from .interface import SlackbotStorage, SqlConnectionFactory
from .postgresql import (
    PostgresqlConnectionFactory,
    SlackbotPostgresqlStorage,
)
from .sqlite import SlackbotSqliteStorage, SqliteConnectionFactory


def create_connection_factory(
    db_config: DatabaseConfig,
    seconds_now: SecondsNow = system_seconds_now,
) -> SqlConnectionFactory:
    parsed = urlparse(db_config.database_uri)

    if parsed.scheme == "postgresql":
        if db_config.seed_database_from:
            raise ValueError(
                "Database seeding is not supported for PostgreSQL databases to prevent accidental production data overwrites"
            )
        return PostgresqlConnectionFactory.from_db_config(db_config, seconds_now)
    elif parsed.scheme == "sqlite":
        # Handle sqlite:///path/to/db.db format
        return SqliteConnectionFactory.from_db_config(db_config, seconds_now)
    else:
        # Treat as SQLite file path
        sqlite_db_config = db_config.model_copy(
            update={"database_uri": f"sqlite:///{db_config.database_uri}"}
        )
        return SqliteConnectionFactory.from_db_config(
            sqlite_db_config,
            seconds_now,
        )


def create_storage(
    sql_conn_factory: SqlConnectionFactory,
    kek_config: KekConfig,
    seconds_now: SecondsNow = system_seconds_now,
) -> SlackbotStorage:
    kek_provider = KekProvider(kek_config)
    if isinstance(sql_conn_factory, PostgresqlConnectionFactory):
        return SlackbotPostgresqlStorage(sql_conn_factory, kek_provider, seconds_now)
    else:
        return SlackbotSqliteStorage(sql_conn_factory, kek_provider, seconds_now)


def create_storage_from_uri(
    database_uri: str,
    kek_config: KekConfig,
    seconds_now: SecondsNow = system_seconds_now,
    seed_database_from: str | None = None,
) -> SlackbotStorage:
    config = DatabaseConfig(database_uri=database_uri, seed_database_from=seed_database_from)
    sql_conn_factory = create_connection_factory(config, seconds_now)
    return create_storage(sql_conn_factory, kek_config, seconds_now=seconds_now)


def get_database_type(database_uri: str) -> str:
    """Get the current database type based on provided database_uri."""
    parsed = urlparse(database_uri)
    if parsed.scheme == "postgresql":
        return "postgresql"
    elif parsed.scheme == "sqlite":
        return "sqlite"
    else:
        # Treat as SQLite file path
        return "sqlite"
