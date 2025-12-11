import os
from pathlib import Path
from typing import TYPE_CHECKING

from aiohttp import web

from csbot.slackbot.webapp.add_connections.all_routes import add_onboarding_connections_routes
from csbot.slackbot.webapp.add_connections.dataset_sync import add_dataset_sync_routes
from csbot.slackbot.webapp.billing.routes import add_billing_routes
from csbot.slackbot.webapp.channels.routes import add_channels_routes
from csbot.slackbot.webapp.connections.routes import add_connections_routes
from csbot.slackbot.webapp.context_governance.routes import add_context_governance_routes
from csbot.slackbot.webapp.github_auth import add_github_auth_routes
from csbot.slackbot.webapp.html_threads import (
    create_thread_api_handler,
)
from csbot.slackbot.webapp.onboarding import (
    create_onboarding_process_api_handler,
    create_onboarding_status_handler,
    create_onboarding_submit_api_handler,
)
from csbot.slackbot.webapp.onboarding.complete_prospector import (
    create_complete_prospector_handler,
)
from csbot.slackbot.webapp.referral.referral import set_referral_token_cookie_from_token
from csbot.slackbot.webapp.referral.routes import add_referral_routes
from csbot.slackbot.webapp.security import ensure_auth_token_cookie_from_token
from csbot.slackbot.webapp.user_profile import create_user_profile_handler
from csbot.slackbot.webapp.users.routes import add_org_users_routes

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer


async def serve_favicon(request: web.Request) -> web.FileResponse:
    """Serve the favicon.ico file."""
    favicon_path = os.path.join(os.path.dirname(__file__), "favicon.ico")
    return web.FileResponse(favicon_path)


async def serve_static_image(request: web.Request) -> web.FileResponse:
    """Serve static image files from the webapp directory."""
    filename = request.match_info["filename"]

    # Security check: prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise web.HTTPNotFound()

    # Only allow common image extensions
    allowed_extensions = {".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico"}
    if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
        raise web.HTTPNotFound()

    image_path = os.path.join(os.path.dirname(__file__), "static", filename)

    # Check if file exists
    if not os.path.exists(image_path):
        raise web.HTTPNotFound()

    return web.FileResponse(image_path)


async def serve_static_css(request: web.Request) -> web.FileResponse:
    """Serve CSS files from the webapp static directory."""
    filename = request.match_info["filename"]

    # Security check: prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise web.HTTPNotFound()

    # Only allow CSS files
    allowed_extensions = {".css", ".css.map"}
    if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
        raise web.HTTPNotFound()

    css_path = os.path.join(os.path.dirname(__file__), "static", filename)

    # Check if file exists
    if not os.path.exists(css_path):
        raise web.HTTPNotFound()

    return web.FileResponse(css_path)


def create_react_app_handler(bot_server: "CompassBotServer"):
    """Create handler for serving React SPA with JWT token-to-cookie conversion."""

    async def serve_react_app(request: web.Request) -> web.Response:
        """Serve the React SPA for client-side routing with dynamic config injection."""
        await ensure_auth_token_cookie_from_token(request, bot_server)
        set_referral_token_cookie_from_token(request, bot_server)

        # React build is in packages/ui/dist relative to the repo root
        # This file is in packages/csbot/src/csbot/slackbot/webapp/routes.py
        # Navigate: routes.py -> webapp -> slackbot -> csbot -> src -> csbot -> packages -> repo_root
        current_file = Path(__file__)
        repo_root = current_file.parent.parent.parent.parent.parent.parent.parent
        react_dist = repo_root / "packages" / "ui" / "dist"
        index_path = react_dist / "index.html"

        if not index_path.exists():
            raise web.HTTPNotFound(text="React app not built. Run 'yarn build' in packages/ui/")

        with open(index_path, encoding="utf-8") as f:
            html_content = f.read()

        # Replace placeholders with actual values (similar to Dagster's approach)
        env_name = os.getenv("COMPASS_ENV", "")
        html_content = html_content.replace("__ENV_NAME__", env_name)

        return web.Response(text=html_content, content_type="text/html")

    return serve_react_app


def add_webapp_routes(app: web.Application, bot_server: "CompassBotServer"):
    # Create React app handler with bot_server in closure
    react_app_handler = create_react_app_handler(bot_server)

    # Add favicon route
    app.router.add_get("/favicon.ico", serve_favicon)

    # Add static file routes
    app.router.add_get("/static/{filename}", serve_static_image)  # For images
    app.router.add_get(
        "/css/{filename}", serve_static_css
    )  # For CSS files (served from static/ dir)

    # Serve React app static assets (JS, CSS, etc.)
    current_file = Path(__file__)
    repo_root = current_file.parent.parent.parent.parent.parent.parent.parent
    react_dist = repo_root / "packages" / "ui" / "dist"
    if react_dist.exists():
        app.router.add_static("/assets", react_dist / "assets", name="react-assets")

    # Thread viewer endpoint (React)
    app.router.add_get("/thread/{team_id}/{channel_id}/{thread_ts}", react_app_handler)

    # Thread API endpoint for React frontend
    app.router.add_get(
        "/api/thread/{team_id}/{channel_id}/{thread_ts}", create_thread_api_handler(bot_server)
    )

    # Onboarding endpoint (React) - forms submit to /api/onboarding/process
    app.router.add_get("/onboarding", react_app_handler)

    # JSON API endpoints for React frontend
    app.router.add_post("/api/onboarding/submit", create_onboarding_submit_api_handler(bot_server))
    app.router.add_post(
        "/api/onboarding/process", create_onboarding_process_api_handler(bot_server)
    )
    app.router.add_post("/api/onboarding-status", create_onboarding_status_handler(bot_server))
    app.router.add_get("/api/onboarding-status", create_onboarding_status_handler(bot_server))

    # Prospector onboarding at /signup (React) - both prospector and standard use same handler
    app.router.add_get("/signup", react_app_handler)

    # Redirect old prospector URLs to /signup for backward compatibility
    async def redirect_old_prospector_url(request: web.Request) -> web.Response:
        """Redirect /onboarding/prospector to /signup."""
        return web.HTTPMovedPermanently(location="/signup")

    app.router.add_get("/onboarding/prospector", redirect_old_prospector_url)
    app.router.add_post("/onboarding/prospector", redirect_old_prospector_url)

    # Both /api/signup and /api/onboarding/process use same handler for minimal onboarding
    app.router.add_post("/api/signup", create_onboarding_process_api_handler(bot_server))

    # Complete prospector setup after data type selection
    app.router.add_post(
        "/api/onboarding/prospector/complete", create_complete_prospector_handler(bot_server)
    )

    # User profile endpoint
    app.router.add_get("/api/user/profile", create_user_profile_handler(bot_server))

    # Add specialized routes
    add_billing_routes(app, bot_server)
    add_connections_routes(app, bot_server)
    add_referral_routes(app, bot_server)
    add_channels_routes(app, bot_server)
    add_context_governance_routes(app, bot_server)
    add_github_auth_routes(app, bot_server)
    add_onboarding_connections_routes(app, bot_server)  # API routes for React connection wizard
    add_dataset_sync_routes(app, bot_server)  # Dataset sync status tracking endpoints
    add_org_users_routes(app, bot_server)  # Org users management routes

    # React app routes (serve SPA for client-side routing)
    app.router.add_get("/billing", react_app_handler)
    app.router.add_get("/connections", react_app_handler)
    app.router.add_get("/referral", react_app_handler)
    app.router.add_get("/connections/add-connection", react_app_handler)
    app.router.add_get("/channels", react_app_handler)
    app.router.add_get("/context-governance", react_app_handler)
    app.router.add_get("/onboarding/connections", react_app_handler)
    app.router.add_get("/dataset-sync", react_app_handler)
    app.router.add_get("/users", react_app_handler)
