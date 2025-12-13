"""
Slack OAuth CLI tool for generating tokens for new workspaces.
"""

import asyncio
import json
import logging
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import cast

import click
import httpx
import structlog
from pydantic import ValidationError

from csbot.slack_manifest import SlackBotManifest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = structlog.get_logger(__name__)


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""

    def do_GET(self):
        """Handle GET request for OAuth callback."""
        # Parse the URL and query parameters
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # Extract code or error
        oauth_result: dict[str, str] = {}
        if "code" in query_params:
            oauth_result["code"] = query_params["code"][0]
            response_body = """
            <html>
                <body>
                    <h1>Authorization Successful!</h1>
                    <p>You can close this tab and return to your terminal.</p>
                </body>
            </html>
            """
            self.send_response(200)
        elif "error" in query_params:
            error = query_params["error"][0]
            error_description = query_params.get("error_description", ["Unknown error"])[0]
            oauth_result["error"] = error
            oauth_result["error_description"] = error_description
            response_body = f"""
            <html>
                <body>
                    <h1>Authorization Failed</h1>
                    <p>Error: {error}</p>
                    <p>Description: {error_description}</p>
                    <p>You can close this tab and return to your terminal.</p>
                </body>
            </html>
            """
            self.send_response(400)
        else:
            response_body = """
            <html>
                <body>
                    <h1>Unknown Response</h1>
                    <p>You can close this tab and return to your terminal.</p>
                </body>
            </html>
            """
            self.send_response(400)

        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(response_body.encode())

        # Store result in server instance
        cast("OAuthServer", self.server).oauth_result = oauth_result

    def log_message(self, format, *args):
        """Suppress HTTP server logs."""
        pass


class OAuthServer(HTTPServer):
    """HTTP server that stores OAuth results."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.oauth_result: dict[str, str] = {}


async def exchange_code_for_token(
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict:
    """Exchange authorization code for access token."""
    token_url = "https://slack.com/api/oauth.v2.access"

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        response.raise_for_status()
        return response.json()


def start_oauth_flow(
    client_id: str,
    redirect_uri: str,
    scopes: list[str],
    user_scopes: list[str] | None = None,
) -> str:
    """Generate OAuth authorization URL and open in browser."""
    base_url = "https://slack.com/oauth/v2/authorize"

    params = {
        "client_id": client_id,
        "scope": ",".join(scopes),
        "redirect_uri": redirect_uri,
        "response_type": "code",
    }

    if user_scopes:
        params["user_scope"] = ",".join(user_scopes)

    auth_url = f"{base_url}?" + urllib.parse.urlencode(params)

    click.echo(f"Opening authorization URL: {auth_url}")
    webbrowser.open(auth_url)

    return auth_url


def wait_for_callback(base_url: str, port: int) -> dict[str, str]:
    """Start local server and wait for OAuth callback."""
    server = OAuthServer(("localhost", port), OAuthCallbackHandler)
    click.echo(f"Waiting for OAuth callback on {base_url}:{port}/callback")

    try:
        # Handle one request (the callback)
        server.handle_request()
        return server.oauth_result
    finally:
        server.server_close()


def load_scopes_from_manifest(manifest_path: str) -> tuple[list[str], list[str] | None]:
    """Load bot and user scopes from Slack manifest file."""
    path = Path(manifest_path)
    if not path.exists():
        raise click.ClickException(f"Manifest file not found: {manifest_path}")

    try:
        with open(path) as f:
            manifest_data = json.load(f)
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON in manifest file: {e}")

    try:
        manifest = SlackBotManifest.model_validate(manifest_data)
    except ValidationError as e:
        raise click.ClickException(f"Invalid manifest structure: {e}")

    bot_scopes = manifest.oauth_config.scopes.bot
    if not bot_scopes:
        raise click.ClickException("No bot scopes found in manifest file")

    user_scopes = manifest.oauth_config.scopes.user

    return bot_scopes, user_scopes


@click.command(name="slack-oauth")
@click.option(
    "--client-id",
    required=True,
    help="Slack app client ID",
)
@click.option(
    "--client-secret",
    required=True,
    help="Slack app client secret",
)
@click.option(
    "--ngrok-url",
    required=True,
    help="Public-facing NGROK URL for OAuth redirect (e.g., https://2f19a9e5ced6.ngrok-free.app)\n"
    "Add this to your Slack app's Redirect URLs.",
)
@click.option(
    "--port",
    default=8080,
    help="Local port for OAuth callback server (default: 8080)",
)
@click.option(
    "--manifest",
    required=True,
    type=click.Path(exists=True),
    help=(
        "Path to Slack manifest.json file (e.g., @infra/slack_bot_manifests/staging_manifest.json)"
    ),
)
def oauth_command(
    client_id: str,
    client_secret: str,
    ngrok_url: str,
    manifest: str,
    port: int,
):
    """Generate Slack OAuth token for new workspace."""

    # Load scopes from manifest file
    try:
        bot_scopes, user_scopes = load_scopes_from_manifest(manifest)
        click.echo(f"Loaded {len(bot_scopes)} bot scopes from manifest: {manifest}")
        if user_scopes:
            click.echo(f"Loaded {len(user_scopes)} user scopes from manifest")
    except Exception as e:
        raise click.ClickException(f"Error loading manifest: {e}")

    # Use local callback URL for development
    redirect_uri = f"{ngrok_url}/callback"

    try:
        # Start OAuth flow
        start_oauth_flow(client_id, redirect_uri, bot_scopes, user_scopes)

        # Wait for callback
        callback_result = wait_for_callback(ngrok_url, port)

        if "error" in callback_result:
            error_desc = callback_result.get("error_description", "Unknown error")
            click.echo(
                click.style(
                    f"OAuth failed: {callback_result['error']} - {error_desc}",
                    fg="red",
                )
            )
            return

        if "code" not in callback_result:
            click.echo(click.style("No authorization code received", fg="red"))
            return

        # Exchange code for token
        click.echo("Exchanging authorization code for access token...")

        async def get_token():
            return await exchange_code_for_token(
                client_id, client_secret, callback_result["code"], redirect_uri
            )

        token_response = asyncio.run(get_token())

        if not token_response.get("ok"):
            click.echo(
                click.style(
                    f"Token exchange failed: {token_response.get('error', 'Unknown error')}",
                    fg="red",
                )
            )
            return

        print(token_response)
        # Display results
        click.echo(click.style("\n✅ OAuth successful!", fg="green"))
        click.echo(f"Team: {token_response.get('team', {}).get('name', 'Unknown')}")
        click.echo(f"Team ID: {token_response.get('team', {}).get('id', 'Unknown')}")

        if "access_token" in token_response:
            click.echo(f"\n🤖 Bot Token: {token_response['access_token']}")

        if "authed_user" in token_response and "access_token" in token_response["authed_user"]:
            click.echo(f"👤 User Token: {token_response['authed_user']['access_token']}")

    except Exception as e:
        click.echo(click.style(f"Error during OAuth flow: {e}", fg="red"))
        logger.exception("OAuth flow failed")
