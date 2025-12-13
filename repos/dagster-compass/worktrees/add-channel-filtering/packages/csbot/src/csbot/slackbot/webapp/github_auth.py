"""GitHub OAuth authentication routes for user account association."""

import secrets
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import aiohttp
import structlog
from aiohttp import web

from csbot.slackbot.webapp.htmlstring import HtmlString
from csbot.slackbot.webapp.security import (
    _is_test_environment,
)

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer

logger = structlog.get_logger(__name__)


async def exchange_code_for_token(client_id: str, client_secret: str, code: str) -> dict:
    """Exchange authorization code for GitHub user access token."""
    async with aiohttp.ClientSession() as session:
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
        }
        headers = {
            "Accept": "application/json",
            "User-Agent": "Compass-Bot",
        }

        async with session.post(
            "https://github.com/login/oauth/access_token",
            data=data,
            headers=headers,
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise ValueError(
                    f"Failed to exchange code for token: {response.status} - {error_text}"
                )

            return await response.json()


async def get_github_user(access_token: str) -> dict:
    """Get GitHub user information using access token."""
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Compass-Bot",
        }

        async with session.get("https://api.github.com/user", headers=headers) as response:
            if response.status != 200:
                error_text = await response.text()
                raise ValueError(f"Failed to get user info: {response.status} - {error_text}")

            return await response.json()


async def invite_user_to_repo(
    repo_owner: str, repo_name: str, username: str, bot_token: str
) -> bool:
    """Invite a GitHub user as a collaborator to the repository."""
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {bot_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Compass-Bot",
        }

        data = {
            "permission": "write"  # Write access to the repository
        }

        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/collaborators/{username}"

        async with session.put(url, json=data, headers=headers) as response:
            if response.status in (201, 204):  # Created or already exists
                logger.info(
                    "Successfully invited user to repo",
                    username=username,
                    repo=f"{repo_owner}/{repo_name}",
                )
                return True
            else:
                error_text = await response.text()
                logger.error(
                    "Failed to invite user to repo",
                    username=username,
                    repo=f"{repo_owner}/{repo_name}",
                    status=response.status,
                    error=error_text,
                )
                return False


async def accept_repo_invitation(repo_owner: str, repo_name: str, user_access_token: str) -> bool:
    """Accept a repository invitation on behalf of the user."""
    async with aiohttp.ClientSession() as session:
        # First, get the list of repository invitations for the user
        headers = {
            "Authorization": f"Bearer {user_access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Compass-Bot",
        }

        # List repository invitations for the authenticated user
        async with session.get(
            "https://api.github.com/user/repository_invitations", headers=headers
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(
                    "Failed to get repository invitations",
                    repo=f"{repo_owner}/{repo_name}",
                    status=response.status,
                    error=error_text,
                )
                return False

            invitations = await response.json()

        # Find the invitation for this specific repository
        invitation_id = None
        for invitation in invitations:
            if invitation.get("repository", {}).get("full_name") == f"{repo_owner}/{repo_name}":
                invitation_id = invitation.get("id")
                break

        if not invitation_id:
            logger.info(
                "No pending invitation found for repo",
                repo=f"{repo_owner}/{repo_name}",
            )
            return True  # No invitation to accept, consider it successful

        # Accept the invitation
        accept_url = f"https://api.github.com/user/repository_invitations/{invitation_id}"
        async with session.patch(accept_url, headers=headers) as response:
            if response.status == 204:  # No Content - success
                logger.info(
                    "Successfully accepted repository invitation",
                    repo=f"{repo_owner}/{repo_name}",
                    invitation_id=invitation_id,
                )
                return True
            else:
                error_text = await response.text()
                logger.error(
                    "Failed to accept repository invitation",
                    repo=f"{repo_owner}/{repo_name}",
                    invitation_id=invitation_id,
                    status=response.status,
                    error=error_text,
                )
                return False


def github_auth_unauthorized_error() -> HtmlString:
    """Error message for unauthorized GitHub auth access."""
    return HtmlString(
        "Your GitHub authentication session has expired or is invalid. "
        "Please return to Slack and try the GitHub integration again."
    )


def create_github_auth_link(bot) -> str:
    """
    Create a direct GitHub OAuth authorization URL.

    Always redirects back to the governance page after authentication.

    Args:
        bot: The CompassChannelBotInstance

    Returns:
        A direct GitHub OAuth URL that initiates the auth flow
    """

    # Get GitHub client ID from server config
    github_config = bot.server_config.github
    if not github_config.client_id:
        raise ValueError("GitHub client_id not configured in server config")

    # Generate state parameter for OAuth security
    state = secrets.token_urlsafe(32)

    # Store state and bot context for callback validation
    # We'll use a stateless approach by encoding the bot key in the state
    bot_key_encoded = f"{bot.key.team_id}:{bot.key.channel_name}"

    # Simplified state payload - always redirect to governance
    state_payload = f"{state}|{bot_key_encoded}"

    # Build direct GitHub OAuth URL
    oauth_params = {
        "client_id": github_config.client_id,
        "redirect_uri": f"{bot.server_config.public_url}/auth/github/callback",
        "scope": "user:email",
        "state": state_payload,
    }

    return f"https://github.com/login/oauth/authorize?{urlencode(oauth_params)}"


def create_github_callback_handler(bot_server: "CompassBotServer"):
    """Create handler for GitHub OAuth callback."""

    async def github_callback_handler(request: web.Request) -> web.Response:
        """Handle GitHub OAuth callback and initiate account association."""
        github_config = bot_server.config.github

        # Validate configuration
        if not github_config.client_id or not github_config.client_secret:
            logger.error("GitHub client_id or client_secret not configured")
            return web.HTTPInternalServerError(text="GitHub OAuth not properly configured")

        # Validate state parameter
        state_from_query = request.query.get("state")

        if not state_from_query or "|" not in state_from_query:
            logger.warning("Invalid state parameter format", state=state_from_query)
            return web.HTTPBadRequest(text="Invalid state parameter format")

        # Parse simplified state (just state token and bot key)
        state_parts = state_from_query.split("|")
        if len(state_parts) < 2:
            logger.warning("Invalid state parameter format", state=state_from_query)
            return web.HTTPBadRequest(text="Invalid state parameter format")

        _, bot_key_encoded = state_parts[0], state_parts[1]

        # Get authorization code
        code = request.query.get("code")
        error = request.query.get("error")

        if error:
            logger.warning("GitHub OAuth error", error=error)
            return web.HTTPBadRequest(text="GitHub OAuth error")

        if not code:
            logger.warning("Missing authorization code in callback")
            return web.HTTPBadRequest(text="Missing authorization code")

        try:
            # Parse bot key from encoded string (either state or cookie)
            team_id, channel_name = bot_key_encoded.split(":", 1)
            from csbot.slackbot.bot_server.bot_server import BotKey

            bot_key = BotKey(team_id=team_id, channel_name=channel_name)

            # Get bot instance
            bot = bot_server.bots.get(bot_key)
            if not bot:
                logger.error("Bot not found for key", bot_key=bot_key)
                return web.HTTPBadRequest(text="Bot context not found")

            # Exchange code for access token
            logger.info("Exchanging authorization code for access token")
            token_response = await exchange_code_for_token(
                github_config.client_id, github_config.client_secret.get_secret_value(), code
            )

            if "error" in token_response:
                logger.error("Token exchange failed", error=token_response)
                return web.HTTPBadRequest(text="Token exchange failed")

            access_token = token_response.get("access_token")
            if not access_token:
                logger.error("No access token in response", response=token_response)
                return web.HTTPBadRequest(text="No access token received from GitHub")

            # Get user information
            logger.info("Fetching GitHub user information")
            user_info = await get_github_user(access_token)
            username = user_info.get("login")
            user_id = user_info.get("id")

            if not username or not user_id:
                logger.error("Invalid user info received", user_info=user_info)
                return web.HTTPBadRequest(text="Failed to get valid user information from GitHub")

            logger.info("GitHub OAuth successful", username=username, user_id=user_id)

            # Get bot's GitHub repository and invite user as collaborator
            contextstore_repo = bot.bot_config.contextstore_github_repo
            if not contextstore_repo:
                raise ValueError("No context repository configured for this bot")

            repo_owner, repo_name = contextstore_repo.split("/", 1)

            # Get bot's GitHub token from bot server
            bot_github_token = bot_server.github_auth_source.get_token()
            if not bot_github_token:
                raise ValueError("No GitHub token configured for this bot")

            if not await invite_user_to_repo(repo_owner, repo_name, username, bot_github_token):
                raise ValueError(f"Failed to invite user to repository {repo_owner}/{repo_name}")

            accept_success = await accept_repo_invitation(repo_owner, repo_name, access_token)
            if not accept_success:
                bot.logger.error(
                    f"Failed to accept repository invitation for {repo_owner}/{repo_name}"
                )

            # Always redirect back to governance page after auth
            redirect_url = f"{bot.server_config.public_url}/context-governance"
            response = web.HTTPFound(redirect_url)

            # Set GitHub authorization cookie (no expiration)
            # Use secure cookies only in production environments (HTTPS)
            is_secure = not _is_test_environment(bot_server)
            response.set_cookie(
                "github_authorized",
                f"{username}:{user_id}",
                httponly=False,  # Allow JavaScript access for UI updates
                secure=is_secure,
                samesite="Lax",
                path="/",
            )

            return response

        except Exception as e:
            logger.error("GitHub OAuth callback failed", error=str(e), exc_info=True)
            return web.HTTPInternalServerError(text="OAuth callback failed")

    return github_callback_handler


def add_github_auth_routes(app: web.Application, bot_server: "CompassBotServer"):
    """Add GitHub authentication routes to the webapp."""
    app.router.add_get("/auth/github/callback", create_github_callback_handler(bot_server))
