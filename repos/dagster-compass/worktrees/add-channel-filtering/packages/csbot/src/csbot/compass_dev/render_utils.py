"""Render utilities for managing secrets and services."""

import asyncio
import json
import os
import re
from pathlib import Path

import click
import httpx

from csbot.slackbot.slackbot_secrets import RenderSecretStore
from csbot.slackbot.webapp.add_connections.models import JsonConfig


async def get_secret_impl(
    org_id: int,
    secret_key: str,
    render_service_id: str,
    render_api_key: str,
    encryption_key: str,
    outfile: str,
) -> None:
    """Get a secret from Render secret store.

    Args:
        org_id: Organization ID
        secret_key: Secret key name
        render_service_id: Render service ID
        render_api_key: Render API key
        encryption_key: Secret encryption key
    """
    # Set encryption key in environment
    old_key = os.environ.get("SECRET_ENCRYPTION_KEY")
    os.environ["SECRET_ENCRYPTION_KEY"] = encryption_key

    try:
        secret_store = RenderSecretStore(render_service_id, render_api_key)
        contents = await secret_store.get_secret_contents(org_id, secret_key)

        click.echo("✅ Secret retrieved successfully")
        click.echo("=" * 80)
        click.echo(f"Organization ID: {org_id}")
        click.echo(f"Secret Key:      {secret_key}")
        click.echo()
        click.echo("Contents:")
        click.echo("-" * 80)

        # Try to parse and prettify as JsonConfig
        try:
            if contents.startswith("jsonconfig:"):
                config = JsonConfig.from_url(contents)
                click.echo(f"Type: {config.type}")
                click.echo()
                click.echo("Config:")
                click.echo(json.dumps(config.config, indent=2))
            else:
                click.echo(contents)
        except Exception:
            # If parsing fails, just show raw contents
            click.echo(contents)

        if outfile:
            with open(outfile, "w") as f:
                f.write(contents)

    finally:
        # Restore previous encryption key
        if old_key is None:
            os.environ.pop("SECRET_ENCRYPTION_KEY", None)
        else:
            os.environ["SECRET_ENCRYPTION_KEY"] = old_key


async def get_env_var_impl(
    env_var_key: str,
    render_service_id: str,
    render_api_key: str,
) -> None:
    """Get an environment variable from Render.

    Args:
        env_var_key: Environment variable key name
        render_service_id: Render service ID
        render_api_key: Render API key
    """
    url = f"https://api.render.com/v1/services/{render_service_id}/env-vars/{env_var_key}"
    headers = {
        "Authorization": f"Bearer {render_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        env_var_data = response.json()

    click.echo("✅ Environment variable retrieved successfully")
    click.echo("=" * 80)
    click.echo(f"Key:   {env_var_data.get('key', env_var_key)}")
    click.echo(f"Value: {env_var_data.get('value', 'N/A')}")
    click.echo("=" * 80)


async def get_env_var_value(
    env_var_key: str,
    render_service_id: str,
    render_api_key: str,
) -> str:
    """Get an environment variable value from Render.

    Args:
        env_var_key: Environment variable key name
        render_service_id: Render service ID
        render_api_key: Render API key

    Returns:
        The environment variable value
    """
    url = f"https://api.render.com/v1/services/{render_service_id}/env-vars/{env_var_key}"
    headers = {
        "Authorization": f"Bearer {render_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        env_var_data = response.json()

    return env_var_data.get("value", "")


def extract_env_vars_from_config(config_file: Path) -> set[str]:
    """Extract all environment variable names from a config file.

    Looks for patterns like:
    - env('VARIABLE_NAME')
    - secret('name', 'ENV_VAR_NAME')

    Args:
        config_file: Path to the config file

    Returns:
        Set of environment variable names
    """
    content = config_file.read_text()

    env_vars = set()

    env_pattern = r"env\(['\"]([A-Z_0-9]+)['\"]\)"
    env_matches = re.findall(env_pattern, content)
    env_vars.update(env_matches)

    secret_pattern = r"secret\(['\"][^'\"]+['\"]\s*,\s*['\"]([A-Z_0-9]+)['\"]\)"
    secret_matches = re.findall(secret_pattern, content)
    env_vars.update(secret_matches)

    return env_vars


async def dump_env_vars_impl(
    config_file: Path,
    render_service_id: str,
    render_api_key: str,
    output_file: Path,
) -> None:
    """Extract env vars from config file and dump them to a file.

    Args:
        config_file: Path to the config file
        render_service_id: Render service ID
        render_api_key: Render API key
        output_file: Path to output file
    """
    env_vars = extract_env_vars_from_config(config_file)

    click.echo(f"Found {len(env_vars)} environment variables in {config_file}")
    click.echo()

    env_values = {}

    for env_var in sorted(env_vars):
        click.echo(f"Fetching {env_var}...")
        try:
            value = await get_env_var_value(env_var, render_service_id, render_api_key)
            env_values[env_var] = value
            click.echo("  ✅ Retrieved")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                click.echo("  ⚠️  Not found in Render (skipping)")
            else:
                click.echo(f"  ❌ Error: {e}")
                raise

    with output_file.open("w") as f:
        for key in sorted(env_values.keys()):
            value = env_values[key]
            f.write(f"{key}={value}\n")

    click.echo()
    click.echo(f"✅ Wrote {len(env_values)} environment variables to {output_file}")
    click.echo(f"   Skipped {len(env_vars) - len(env_values)} variables not found in Render")


@click.group()
def render():
    """Render utility commands for managing secrets and services."""
    pass


@render.command()
@click.option(
    "--org-id",
    type=int,
    required=True,
    help="Organization ID",
)
@click.option(
    "--secret-key",
    required=True,
    help="Secret key name (e.g., 'snowflake_prod_url.txt')",
)
@click.option(
    "--render-service-id",
    required=True,
    help="Render service ID",
)
@click.option(
    "--render-api-key",
    required=True,
    help="Render API key",
)
@click.option(
    "--encryption-key",
    required=True,
    help="Secret encryption key",
)
@click.option(
    "--out-file",
    required=False,
)
def get_secret(
    org_id: int,
    secret_key: str,
    render_service_id: str,
    render_api_key: str,
    encryption_key: str,
    out_file: str,
) -> None:
    """Get and decrypt a secret from Render.

    Example:
        compass-dev render get-secret \\
            --org-id 42 \\
            --secret-key snowflake_prod_url.txt \\
            --render-service-id srv-xxx \\
            --render-api-key rnd_xxx \\
            --encryption-key key123
    """
    try:
        asyncio.run(
            get_secret_impl(
                org_id, secret_key, render_service_id, render_api_key, encryption_key, out_file
            )
        )
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@render.command()
@click.option(
    "--env-var-key",
    required=True,
    help="Environment variable key name (e.g., 'DATABASE_URL')",
)
@click.option(
    "--render-service-id",
    required=True,
    help="Render service ID",
)
@click.option(
    "--render-api-key",
    required=True,
    help="Render API key",
)
def get_env_var(
    env_var_key: str,
    render_service_id: str,
    render_api_key: str,
) -> None:
    """Get an environment variable from Render.

    Example:
        compass-dev render get-env-var \\
            --env-var-key DATABASE_URL \\
            --render-service-id srv-xxx \\
            --render-api-key rnd_xxx
    """
    try:
        asyncio.run(get_env_var_impl(env_var_key, render_service_id, render_api_key))
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@render.command()
@click.option(
    "--config-file",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to config file (e.g., staging.csbot.config.yaml)",
)
@click.option(
    "--render-service-id",
    required=True,
    help="Render service ID",
)
@click.option(
    "--render-api-key",
    required=True,
    help="Render API key",
)
@click.option(
    "--output-file",
    type=click.Path(path_type=Path),
    required=True,
    help="Output file path (e.g., .env.staging)",
)
def dump_env_vars(
    config_file: Path,
    render_service_id: str,
    render_api_key: str,
    output_file: Path,
) -> None:
    """Extract env vars from config file and retrieve them from Render.

    This command:
    1. Parses the config file for env() and secret() references
    2. Retrieves each environment variable from Render
    3. Writes them to an output file in ENV_VAR=VALUE format

    Example:
        compass-dev render dump-env-vars \\
            --config-file staging.csbot.config.yaml \\
            --render-service-id srv-xxx \\
            --render-api-key rnd_xxx \\
            --output-file .env.staging
    """
    try:
        asyncio.run(dump_env_vars_impl(config_file, render_service_id, render_api_key, output_file))
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()
