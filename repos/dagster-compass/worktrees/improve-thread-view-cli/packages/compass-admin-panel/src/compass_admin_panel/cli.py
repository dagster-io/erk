"""CLI module for running the Compass Admin Panel server."""

import argparse

import structlog
from aiohttp import web
from csbot.utils.cli_utils import cli_context

from compass_admin_panel.app import create_app

logger = structlog.get_logger(__name__)


def run_server(host: str = "localhost", port: int = 8080, config_path: str | None = None) -> None:
    """Run the Compass Admin Panel server."""
    logger.info("Initializing Compass Admin Panel...")

    try:
        app = create_app(config_path=config_path)

        logger.info(f"Starting server on http://{host}:{port}")
        web.run_app(app, host=host, port=port)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Compass Admin Panel Server")
    parser.add_argument(
        "--host", default="localhost", help="Host to bind the server to (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Port to bind the server to (default: 8080)"
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to csbot configuration file (e.g., local.csbot.config.yaml)",
    )

    args = parser.parse_args()
    with cli_context():
        run_server(args.host, args.port, args.config)


if __name__ == "__main__":
    main()
