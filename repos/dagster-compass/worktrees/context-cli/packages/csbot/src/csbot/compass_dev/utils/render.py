"""Render CLI utilities for compass_dev."""

import os
import subprocess

from ..database_config import (
    Environment,
    get_database_config,
    get_database_password,
)

# get_database_id is now imported from database_config


def execute_sql_query(tier: Environment, query: str) -> str:
    """Execute a SQL query against the specified tier's database using psql directly.

    Uses the same logic as psql.py - connects directly via Tailscale hostnames
    and authenticates using the Render API password.

    Args:
        tier: Either 'prod' or 'staging' to specify which database to query
        query: The SQL query to execute

    Returns:
        The output from the SQL query execution

    Raises:
        RuntimeError: If database connection or query execution fails
    """
    config = get_database_config(tier)

    try:
        # Get password using the shared database_config module
        password = get_database_password(tier)
    except Exception as e:
        raise RuntimeError(f"Failed to get database password for {tier}: {e}") from e

    # Build psql command matching psql.py logic
    psql_cmd = [
        "psql",
        f"--host={config['host']}",
        "--port=5432",
        f"--username={config['user']}",
        f"--dbname={config['database']}",
        "-c",
        query,
        "--no-psqlrc",  # Don't load .psqlrc to avoid custom prompts/settings
    ]

    try:
        # Set environment with password, matching psql.py
        env = {**os.environ, "PGPASSWORD": password}

        # Execute the SQL query using psql directly
        result = subprocess.run(
            psql_cmd,
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to execute SQL query against {tier} (exit code {e.returncode})\n"
        error_msg += f"Command: {' '.join(psql_cmd)}\n"
        error_msg += f"Query: {query}\n"

        if e.stdout:
            error_msg += f"Output: {e.stdout.strip()}\n"
        if e.stderr:
            error_msg += f"Error: {e.stderr.strip()}\n"

        error_msg += "\nThis usually means:\n"
        error_msg += "  • Database connection failed (check Tailscale connection)\n"
        error_msg += "  • Authentication failed (check Render API key)\n"
        error_msg += "  • SQL syntax error in the query\n"
        error_msg += "  • Database permissions issue"

        raise RuntimeError(error_msg) from e
    except FileNotFoundError as e:
        raise RuntimeError(
            "PostgreSQL psql client not found. Please install PostgreSQL client tools."
        ) from e
