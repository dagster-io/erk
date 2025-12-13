"""Main application module for the Compass Admin Panel."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from aiohttp import web
from csbot.slackbot.slackbot_core import load_bot_server_config_from_path
from csbot.slackbot.storage.factory import create_connection_factory, create_storage
from csbot.slackbot.storage.sqlite import SqliteConnectionFactory
from csbot.utils.time import system_seconds_now

from compass_admin_panel.api_routes import (
    create_token_api,
    get_onboarding_details_api,
    get_plan_types_api,
    get_thread_detail_api,
    list_analytics_api,
    list_onboarding_states_api,
    list_organizations_api,
    list_threads_api,
    list_tokens_api,
    search_organizations_api,
)
from compass_admin_panel.organizations import (
    convert_to_design_partner,
    convert_to_free_plan,
    convert_to_starter_plan,
    convert_to_team_plan,
)
from compass_admin_panel.types import AdminPanelContext


def create_app(config_path: str | None = None) -> web.Application:
    """Factory function to create the admin panel application."""
    app = web.Application()

    # Initialize context with default values
    context = AdminPanelContext(config=None, storage=None, stripe_client=None)

    # Load configuration
    if config_path:
        print(f"Loading admin panel configuration from: {config_path}")
        try:
            config = load_bot_server_config_from_path(config_path)
            print(
                f"Configuration loaded successfully. Database URI: {getattr(config, 'database_uri', 'NOT SET')}"
            )
            context.config = config
            conn_factory = create_connection_factory(config.db_config)
            storage = create_storage(conn_factory, config.db_config.kek_config)
            context.storage = storage
            print(f"Storage created successfully. Type: {type(storage).__name__}")

            # Initialize Stripe client if Stripe config is available
            if hasattr(config, "stripe"):
                try:
                    from csbot.stripe.stripe_client import StripeClient

                    stripe_client = StripeClient(api_key=config.stripe.token.get_secret_value())
                    context.stripe_client = stripe_client
                    print("Stripe client initialized successfully")
                except Exception as e:
                    print(f"Warning: Could not initialize Stripe client: {e}")
            else:
                print("Warning: No Stripe configuration found")
        except Exception as e:
            print(f"ERROR: Could not load configuration from {config_path}: {e}")
            print(f"ERROR: Exception type: {type(e).__name__}")
            import traceback

            print(f"ERROR: Full traceback: {traceback.format_exc()}")
            # Continue without storage - will show empty organizations
    else:
        print("WARNING: No config path provided to admin panel - organizations will be empty")

    # Store the context in the app
    app["context"] = context

    # JSON API routes (must be registered before catch-all React route)
    app.router.add_get("/api/organizations", list_organizations_api)
    app.router.add_get("/api/organizations/search", search_organizations_api)
    app.router.add_get("/api/plan-types", get_plan_types_api)
    app.router.add_get("/api/tokens", list_tokens_api)
    app.router.add_post("/api/tokens", create_token_api)
    app.router.add_get("/api/onboarding", list_onboarding_states_api)
    app.router.add_get("/api/onboarding/{org_id}/details", get_onboarding_details_api)
    app.router.add_get("/api/analytics", list_analytics_api)
    app.router.add_get("/api/threads", list_threads_api)
    app.router.add_get("/api/thread/{team_id}/{channel_id}/{thread_ts}", get_thread_detail_api)

    # Plan conversion endpoints
    app.router.add_post("/api/convert-to-design-partner", convert_to_design_partner)
    app.router.add_post("/api/convert-to-free-plan", convert_to_free_plan)
    app.router.add_post("/api/convert-to-starter-plan", convert_to_starter_plan)
    app.router.add_post("/api/convert-to-team-plan", convert_to_team_plan)

    # Health check
    app.router.add_get("/health", health_check)

    # Serve React admin UI (must be last - catch-all route)
    admin_ui_dist = Path(__file__).parent.parent.parent.parent / "admin-ui" / "dist"
    if not admin_ui_dist.exists() or not (admin_ui_dist / "index.html").exists():
        print(
            f"ERROR: React admin UI not found at {admin_ui_dist}. "
            f"Please build the React app first: cd packages/admin-ui && npm run build"
        )
        raise FileNotFoundError(
            "React admin UI build not found. Run: cd packages/admin-ui && npm run build"
        )

    print(f"Serving React admin UI from: {admin_ui_dist}")
    # Serve static assets
    app.router.add_static("/assets", admin_ui_dist / "assets", name="assets")
    # Serve index.html for root and all React routes (catch-all)
    app.router.add_get("/", serve_react_app)
    app.router.add_get("/{path:.*}", serve_react_app)

    return app


async def serve_react_app(request: web.Request) -> web.Response:
    """Serve React app for all non-API routes (React Router)."""
    admin_ui_dist = Path(__file__).parent.parent.parent.parent / "admin-ui" / "dist"
    return web.FileResponse(admin_ui_dist / "index.html")


async def health_check(request: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.json_response({"status": "healthy", "service": "compass-admin-panel"})


def create_sqlite_connection_factory_with_writes(db_path: str) -> SqliteConnectionFactory:
    """Create a SQLite connection factory for admin panel that supports writes."""

    @contextmanager
    def db_path_context():
        # Open with write access for token creation
        try:
            if not Path(db_path).exists():
                raise FileNotFoundError(f"Database file not found: {db_path}")
            conn = sqlite3.connect(db_path)
            try:
                yield conn
            finally:
                conn.close()
        except sqlite3.OperationalError as e:
            raise FileNotFoundError(f"Cannot open database file {db_path}: {e}") from e

    return SqliteConnectionFactory(db_path_context, system_seconds_now)
