"""Shared database configuration and authentication for Compass environments."""

import json
import os
import pathlib
import subprocess
import urllib.error
import urllib.request
from typing import Literal

import yaml

Environment = Literal["staging", "prod"]

# Database configurations for both staging and production
DB_CONFIGS = {
    "staging": {
        "host": "staging-compass-db.lemur-bleak.ts.net",
        "database": "compass_bot_db",
        "user": "compass_bot_db_user",
        "render_db_name": "compass-bot-db",
    },
    "prod": {
        "host": "prod-compass-db.lemur-bleak.ts.net",
        "database": "compass_bot_db_65gu",
        "user": "compass_bot_db_user",
        "render_db_name": "prod-compass-bot-db",
    },
}


def get_render_api_key() -> str:
    """Get Render API key from environment or CLI config.

    Returns:
        The Render API key

    Raises:
        RuntimeError: If no API key can be found
    """
    # First try environment variable
    api_key = os.environ.get("RENDER_API_KEY")
    if api_key:
        return api_key

    # Try to get from render CLI YAML config
    config_path = pathlib.Path.home() / ".render" / "cli.yaml"

    if config_path.exists():
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
                api_config = config.get("api", {})
                api_key = api_config.get("key")
                if api_key:
                    return api_key
        except (yaml.YAMLError, KeyError):
            pass

    raise RuntimeError(
        "Render API key not found. Set RENDER_API_KEY environment variable or run 'render login'"
    )


def get_database_password(environment: Environment) -> str:
    """Get database password from Render API.

    Args:
        environment: Either 'prod' or 'staging' to specify which database

    Returns:
        The database password

    Raises:
        RuntimeError: If password cannot be retrieved
    """
    render_db_name = DB_CONFIGS[environment]["render_db_name"]

    try:
        api_key = get_render_api_key()

        # First get all services to find the database ID
        result = subprocess.run(
            ["render", "services", "--output", "json"],
            capture_output=True,
            text=True,
            check=True,
        )

        services = json.loads(result.stdout)

        # Find the database service
        db_id = None
        for service in services:
            if "postgres" in service and service["postgres"]["name"] == render_db_name:
                db_id = service["postgres"]["id"]
                break

        if not db_id:
            raise RuntimeError(f"Database {render_db_name} not found in render services")

        # Use Render API to get database connection info
        req = urllib.request.Request(
            f"https://api.render.com/v1/postgres/{db_id}/connection-info",
            headers={"Authorization": f"Bearer {api_key}"},
        )

        with urllib.request.urlopen(req) as response:
            connection_info = json.loads(response.read().decode())
            password = connection_info.get("password")

            if not password:
                raise RuntimeError(f"Could not retrieve password for {render_db_name}")

            return password

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get database list from render CLI: {e}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse API response: {e}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Failed to connect to Render API: {e}")
    except Exception as e:
        raise RuntimeError(f"API request failed: {e}")


def get_database_id(environment: Environment) -> str | None:
    """Get the database ID for the specified environment from render services.

    Args:
        environment: Either 'prod' or 'staging' to specify which database to find

    Returns:
        The database ID if found, None otherwise

    Raises:
        RuntimeError: If the render command fails or output cannot be parsed
    """
    expected_name = DB_CONFIGS[environment]["render_db_name"]

    try:
        # Run the render services command to get JSON output
        result = subprocess.run(
            ["render", "services", "-o", "json"], capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to list Render services (exit code {e.returncode})\n"
        error_msg += f"Command: {' '.join(e.cmd)}\n"

        if e.stdout:
            error_msg += f"Output: {e.stdout.strip()}\n"
        if e.stderr:
            error_msg += f"Error: {e.stderr.strip()}\n"

        error_msg += "\nThis usually means:\n"
        error_msg += "  • You're not logged into Render CLI (run: render auth login)\n"
        error_msg += "  • You don't have access to the Render account\n"
        error_msg += "  • The render CLI tool is not installed or not in PATH"

        raise RuntimeError(error_msg) from e
    except FileNotFoundError as e:
        raise RuntimeError(
            "Render CLI tool not found. Please install it from https://render.com/docs/cli"
        ) from e

    try:
        # Parse the JSON response
        services = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Failed to parse Render services response as JSON. "
            f"Raw output: {result.stdout[:200]}..."
        ) from e

    # Search for postgres services with the expected name
    for service in services:
        if "postgres" in service and service["postgres"]["name"] == expected_name:
            return service["postgres"]["id"]

    return None


def get_database_config(environment: Environment) -> dict[str, str]:
    """Get database configuration for the specified environment.

    Args:
        environment: Either 'prod' or 'staging'

    Returns:
        Dictionary containing host, database, user, and render_db_name
    """
    return DB_CONFIGS[environment].copy()


def build_connection_string(environment: Environment, password: str) -> str:
    """Build a PostgreSQL connection string for the specified environment.

    Args:
        environment: Either 'prod' or 'staging'
        password: Database password

    Returns:
        PostgreSQL connection string
    """
    config = DB_CONFIGS[environment]
    return f"postgresql://{config['user']}:{password}@{config['host']}:5432/{config['database']}"
