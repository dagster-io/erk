"""Create referral token command for compass-dev CLI."""

import uuid
from typing import Literal

import click

from csbot.compass_dev.utils.render import execute_sql_query
from csbot.slackbot.config import DatabaseConfig
from csbot.slackbot.storage.sqlite import create_sqlite_connection_factory


@click.command()
@click.argument("tier", type=click.Choice(["prod", "staging", "local"], case_sensitive=False))
@click.option("--count", type=int, default=1)
def create_referral_token(tier: Literal["prod", "staging", "local"], count: int) -> None:
    """Create a referral token and insert it into the database.

    Args:
        tier: Database tier to use - 'prod', 'staging', or 'local'
        count: Number of referral tokens to create
    """
    # Generate a UUID for the referral token
    tokens = [str(uuid.uuid4()) for _ in range(count)]

    try:
        if tier == "local":
            # Handle local SQLite database
            sql_conn_factory = create_sqlite_connection_factory(
                DatabaseConfig.from_sqlite_path("./compassbot.db")
            )

            with sql_conn_factory.with_conn() as conn:
                cursor = conn.cursor()
                cursor.executemany(
                    "INSERT INTO referral_tokens (token) VALUES (?)", [(token,) for token in tokens]
                )
                conn.commit()

            click.echo(f"✅ Successfully created {count} referral tokens:\n{'\n'.join(tokens)}")
            click.echo("📊 Token inserted into local SQLite database (compassbot.db)")
        else:
            # Handle prod/staging with existing render CLI logic
            for token in tokens:
                insert_query = f"INSERT INTO referral_tokens (token) VALUES ('{token}')"
                execute_sql_query(tier, insert_query)

            click.echo(f"✅ Successfully created {count} referral tokens:\n{'\n'.join(tokens)}")

    except Exception as e:
        click.echo(f"❌ Failed to create referral token: {e}", err=True)
        raise click.ClickException(f"Database operation failed: {e}")
