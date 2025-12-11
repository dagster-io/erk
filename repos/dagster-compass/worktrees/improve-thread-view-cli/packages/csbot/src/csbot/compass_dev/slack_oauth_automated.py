"""
Automated Slack OAuth flow with ngrok and manifest management.

This module automates the entire OAuth token acquisition process:
1. Pulls down existing manifest from Slack
2. Starts ngrok tunnel
3. Updates manifest with ngrok redirect URI
4. Generates enterprise OAuth URL
5. Opens browser for user authorization
6. Runs OAuth callback server
7. Captures and displays the OAuth token
"""

import asyncio
import json
import os
import subprocess
import time
import urllib.parse
import webbrowser
from pathlib import Path

import click
import httpx
import structlog
import yaml

from csbot.compass_dev.slack_oauth import (
    OAuthCallbackHandler,
    OAuthServer,
    exchange_code_for_token,
)

logger = structlog.get_logger(__name__)

ENTERPRISE_SLACK_URL = "https://dagsterio.enterprise.slack.com"


class NgrokTunnel:
    """Manages ngrok tunnel lifecycle."""

    def __init__(self, port: int):
        self.port = port
        self.process = None
        self.public_url = None

    def start(self) -> str:
        """Start ngrok tunnel and return the public URL."""
        click.echo(f"Starting ngrok tunnel on port {self.port}...")

        self.process = subprocess.Popen(
            ["ngrok", "http", str(self.port), "--log=stdout"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        timeout = 10
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = httpx.get("http://localhost:4040/api/tunnels", timeout=1.0)
                if response.status_code == 200:
                    data = response.json()
                    tunnels = data.get("tunnels", [])
                    if tunnels:
                        for tunnel in tunnels:
                            if tunnel.get("proto") == "https":
                                self.public_url = tunnel["public_url"]
                                click.echo(f"✅ Ngrok tunnel established: {self.public_url}")
                                return self.public_url
            except (httpx.RequestError, httpx.TimeoutException):
                time.sleep(0.5)
                continue

        if self.process:
            self.process.terminate()
        raise RuntimeError("Failed to start ngrok tunnel within timeout")

    def stop(self):
        """Stop the ngrok tunnel."""
        if self.process:
            click.echo("Stopping ngrok tunnel...")
            self.process.terminate()
            self.process.wait()
            self.process = None
            self.public_url = None


def load_app_config(manifest_filename: str) -> dict:
    """Load app configuration from app_config.yaml."""
    config_path = Path("infra/slack_bot_manifests/app_config.yaml")
    if not config_path.exists():
        raise click.ClickException(f"App config file not found: {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    apps = config.get("apps", {})
    if manifest_filename not in apps:
        raise click.ClickException(
            f"Manifest '{manifest_filename}' not found in app_config.yaml. "
            f"Available manifests: {list(apps.keys())}"
        )

    app_config = apps[manifest_filename]
    app_id = app_config.get("app_id")
    client_id = app_config.get("client_id")

    if not app_id:
        raise click.ClickException(f"app_id not configured for {manifest_filename}")

    if not client_id:
        raise click.ClickException(
            f"client_id not configured for {manifest_filename}. Please add it to {config_path}"
        )

    # Ensure client_id is a string to preserve full precision
    client_id = str(client_id)
    app_config["client_id"] = client_id

    # Validate client_id format (should be like "123456789.987654321")
    if "." not in client_id or not all(part.isdigit() for part in client_id.split(".")):
        raise click.ClickException(
            f"Invalid client_id format in {config_path}. "
            f'Expected format: "123456789.987654321" (must be quoted as a string in YAML)'
        )

    return app_config


async def fetch_current_manifest(config_token: str, app_id: str) -> dict:
    """Fetch the current manifest from Slack API."""
    click.echo(f"Fetching current manifest for app {app_id}...")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://slack.com/api/apps.manifest.export",
            params={"app_id": app_id},
            headers={"Authorization": f"Bearer {config_token}"},
            timeout=30.0,
        )

        result = response.json()

        if not result.get("ok"):
            error = result.get("error", "Unknown error")
            raise click.ClickException(f"Failed to fetch manifest: {error}")

        manifest = result.get("manifest")
        if not manifest:
            raise click.ClickException("No manifest data in response")

        # Handle both dict and string responses from Slack API
        if isinstance(manifest, str):
            manifest = json.loads(manifest)

        click.echo("✅ Manifest fetched successfully")
        return manifest


async def update_manifest_redirect(
    config_token: str,
    app_id: str,
    manifest: dict,
    redirect_url: str,
) -> bool:
    """Update Slack app manifest to include OAuth redirect URL."""
    click.echo(f"Updating manifest with redirect URL: {redirect_url}")

    if "oauth_config" not in manifest:
        manifest["oauth_config"] = {}

    if "redirect_urls" not in manifest["oauth_config"]:
        manifest["oauth_config"]["redirect_urls"] = []

    redirect_urls = manifest["oauth_config"]["redirect_urls"]
    if redirect_url not in redirect_urls:
        redirect_urls.append(redirect_url)
        click.echo("Added redirect URL to manifest")
    else:
        click.echo("Redirect URL already present in manifest")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/apps.manifest.update",
            headers={
                "Authorization": f"Bearer {config_token}",
                "Content-Type": "application/json",
            },
            json={
                "app_id": app_id,
                "manifest": manifest,
            },
            timeout=30.0,
        )

        result = response.json()

        if not result.get("ok"):
            error = result.get("error", "Unknown error")
            errors = result.get("errors", [])
            click.echo(click.style(f"❌ Failed to update manifest: {error}", fg="red"))
            if errors:
                click.echo(click.style(f"Errors: {json.dumps(errors, indent=2)}", fg="red"))
            return False

        click.echo(click.style("✅ Manifest updated successfully", fg="green"))
        return True


def generate_enterprise_oauth_url(
    client_id: str,
    redirect_uri: str,
    scopes: list[str],
    user_scopes: list[str] | None = None,
) -> str:
    """Generate the enterprise-specific OAuth URL for dagsterio.enterprise.slack.com."""
    base_url = f"{ENTERPRISE_SLACK_URL}/oauth"

    params = {
        "client_id": client_id,
        "scope": ",".join(scopes),
        "user_scope": ",".join(user_scopes) if user_scopes else "",
        "redirect_uri": redirect_uri,
        "state": "",
        "granular_bot_scope": "1",
        "single_channel": "0",
        "install_redirect": "",
        "tracked": "1",
        "user_default": "0",
    }

    return f"{base_url}?{urllib.parse.urlencode(params)}"


@click.command(name="reinstall-to-enterprise-grid")
@click.option(
    "--manifest",
    required=True,
    type=click.Path(exists=True),
    help="Path to Slack manifest.json file (e.g., infra/slack_bot_manifests/prod_manifest.json)",
)
@click.option(
    "--client-secret",
    help="Slack app client secret (or will prompt if not provided)",
)
@click.option(
    "--config-token",
    help="Slack configuration token (or set SLACK_CONFIG_TOKEN env var)",
)
@click.option(
    "--port",
    default=8080,
    help="Local port for OAuth callback server (default: 8080)",
)
def oauth_automated_command(
    manifest: str,
    client_secret: str | None,
    config_token: str | None,
    port: int,
):
    """Automated Slack OAuth flow for Enterprise Grid with ngrok and manifest management.

    This command automates the entire OAuth token acquisition process for Enterprise Grid:
    1. Loads app_id and client_id from app_config.yaml based on manifest filename
    2. Fetches current manifest from Slack API
    3. Starts ngrok tunnel
    4. Updates manifest with ngrok redirect URI
    5. Generates enterprise OAuth URL for dagsterio.enterprise.slack.com
    6. Opens browser for authorization
    7. Runs OAuth callback server
    8. Captures and displays the OAuth token

    Example:
        compass-dev reinstall-to-enterprise-grid \\
            --manifest infra/slack_bot_manifests/prod_manifest.json
    """
    ngrok = None

    try:
        token = config_token or os.environ.get("SLACK_CONFIG_TOKEN")
        if not token:
            token = click.prompt(
                "Enter Slack config token (https://api.slack.com/apps → bottom of page → "
                "Generate Your App Configuration Token → select 'dagsterlabs' workspace)",
                hide_input=True,
            )

        # Validate token doesn't contain invalid characters
        token = token.strip()
        if not token or any(ord(c) > 127 for c in token):
            raise click.ClickException(
                "Invalid config token. Please ensure you're using a valid Slack configuration token "
                "from https://api.slack.com/apps (at the bottom of the page)."
            )

        manifest_path = Path(manifest)
        manifest_filename = manifest_path.name

        app_config = load_app_config(manifest_filename)
        app_id = app_config["app_id"]
        client_id = app_config["client_id"]
        env_name = app_config.get("env_name", "unknown")

        click.echo(f"Environment: {env_name}")
        click.echo(f"App ID: {app_id}")
        click.echo(f"Client ID: {client_id}")

        # Prompt for client secret if not provided
        if not client_secret:
            client_secret = click.prompt(
                f"Enter Slack app client secret (https://api.slack.com/apps/{app_id}/general → "
                "App Credentials section → Client Secret → Show → Copy)",
                hide_input=True,
            )

        client_secret = (client_secret or "").strip()
        if not client_secret:
            raise click.ClickException("Client secret is required")

        current_manifest = asyncio.run(fetch_current_manifest(token, app_id))

        bot_scopes = current_manifest.get("oauth_config", {}).get("scopes", {}).get("bot", [])
        user_scopes = current_manifest.get("oauth_config", {}).get("scopes", {}).get("user")

        if not bot_scopes:
            raise click.ClickException("No bot scopes found in manifest")

        click.echo(f"Loaded {len(bot_scopes)} bot scopes from manifest")

        ngrok = NgrokTunnel(port)
        public_url = ngrok.start()

        redirect_url = f"{public_url}/callback"

        updated = asyncio.run(
            update_manifest_redirect(token, app_id, current_manifest, redirect_url)
        )

        if not updated:
            raise click.ClickException("Failed to update Slack manifest")

        oauth_url = generate_enterprise_oauth_url(client_id, redirect_url, bot_scopes, user_scopes)

        click.echo("\n" + "=" * 60)
        click.echo("🔗 Opening OAuth URL in browser...")
        click.echo(f"URL: {oauth_url}")
        click.echo("=" * 60)
        click.echo(
            "\nIf the browser doesn't open automatically, please copy and paste the URL above."
        )
        click.echo("Note: The OAuth flow is for dagsterio.enterprise.slack.com\n")

        webbrowser.open(oauth_url)

        click.echo(f"⏳ Waiting for OAuth callback on {public_url}/callback...")
        click.echo("Please authorize the app in your browser.\n")

        server = OAuthServer(("localhost", port), OAuthCallbackHandler)

        try:
            server.handle_request()
            callback_result = server.oauth_result
        finally:
            server.server_close()

        if "error" in callback_result:
            error_desc = callback_result.get("error_description", "Unknown error")
            click.echo(
                click.style(f"❌ OAuth failed: {callback_result['error']} - {error_desc}", fg="red")
            )
            return

        if "code" not in callback_result:
            click.echo(click.style("❌ No authorization code received", fg="red"))
            return

        click.echo("🔄 Exchanging authorization code for access token...")

        token_response = asyncio.run(
            exchange_code_for_token(client_id, client_secret, callback_result["code"], redirect_url)
        )

        if not token_response.get("ok"):
            click.echo(
                click.style(
                    f"❌ Token exchange failed: {token_response.get('error', 'Unknown error')}",
                    fg="red",
                )
            )
            return

        click.echo(click.style("\n✅ OAuth successful!", fg="green", bold=True))
        click.echo("=" * 60)
        click.echo(f"Team:     {token_response.get('team', {}).get('name', 'Unknown')}")
        click.echo(f"Team ID:  {token_response.get('team', {}).get('id', 'Unknown')}")

        if "access_token" in token_response:
            click.echo(f"\n🤖 Bot Token:\n{token_response['access_token']}")

        if "authed_user" in token_response and "access_token" in token_response["authed_user"]:
            click.echo(f"\n👤 User Token:\n{token_response['authed_user']['access_token']}")

        click.echo("\n" + "=" * 60)
        click.echo("\n📋 Next steps:")
        click.echo(
            "1. Set the bot token as SLACK_BOT_TOKEN_ENTERPRISE_GRID_LOCAL_DEV in your environment"
        )
        click.echo(
            "2. Go to Slack config > integrations > installed apps and add to existing workspaces"
        )
        click.echo("3. Enable 'add to future workspaces by default' in the integration settings")

    except KeyboardInterrupt:
        click.echo("\n\n⚠️  OAuth flow interrupted by user")
    except Exception as e:
        click.echo(click.style(f"\n❌ Error during OAuth flow: {e}", fg="red"))
        logger.exception("OAuth flow failed")
    finally:
        if ngrok:
            ngrok.stop()
