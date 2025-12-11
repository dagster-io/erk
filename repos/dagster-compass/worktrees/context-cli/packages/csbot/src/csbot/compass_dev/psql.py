"""PostgreSQL database connection utility for Compass environments."""

import os
import subprocess
import sys
import tempfile

import click

from .database_config import Environment, get_database_config, get_database_password


@click.command()
@click.argument("environment", type=click.Choice(["staging", "prod"]))
@click.option("--read-only/--read-write", default=True)
@click.option("--host-only", is_flag=True, help="Only print the database host")
@click.option("--connection-string", is_flag=True, help="Print full connection string")
def psql(
    environment: Environment, read_only: bool, host_only: bool, connection_string: bool
) -> None:
    """Connect to Compass database via psql.

    Uses Tailscale network hostnames and fetches credentials from render CLI.

    Examples:
        compass-dev psql staging
        compass-dev psql prod --connection-string
        compass-dev psql staging --host-only
    """
    config = get_database_config(environment)

    if host_only:
        click.echo(config["host"])
        return

    try:
        password = get_database_password(environment)
    except RuntimeError as e:
        raise click.ClickException(str(e))

    if connection_string:
        from .database_config import build_connection_string

        conn_str = build_connection_string(environment, password)
        click.echo(conn_str)
        return

    if not read_only:
        click.echo("""
         ☠️  WARNING! ☠️
      READ-WRITE MODE ACTIVE!

Pro-tip: use transactions
1) BEGIN;
2) do your UPDATE
3) check your UPDATE
4) COMMIT; or ROLLBACK;
    """)

    with tempfile.NamedTemporaryFile() as psqlrc:
        # Build psql command
        psql_cmd = [
            "psql",
            f"--host={config['host']}",
            "--port=5432",
            f"--username={config['user']}",
            f"--dbname={config['database']}",
        ]

        read_marker = "ro" if read_only else "rw"
        prompt = f"%/:{config['host']}:{read_marker}%R%x%# "
        psqlrc.write(b"\\set QUIET 1\n")
        psqlrc.write(f"\\set PROMPT1 '{prompt}'\n".encode())
        psqlrc.write(rf"\set PROMPT2 '{prompt}'".encode())
        psqlrc.write(b"\n\\set QUIET 0")
        psqlrc.seek(0)

        # Build environment variables
        env = {**os.environ, "PGPASSWORD": password, "PSQLRC": psqlrc.name}

        # Use PGOPTIONS to set connection-level options that persist across reconnects
        # This ensures readonly mode and lock_timeout apply even after \c or reconnection
        if read_only:
            env["PGOPTIONS"] = "-c default_transaction_read_only=on -c lock_timeout=250"
        else:
            env["PGOPTIONS"] = "-c lock_timeout=250"

        result = subprocess.run(psql_cmd, env=env)
        sys.exit(result.returncode)
