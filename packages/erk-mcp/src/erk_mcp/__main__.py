from __future__ import annotations

import argparse
import os
from typing import TYPE_CHECKING

import click

from erk_mcp.server import create_mcp

if TYPE_CHECKING:
    from fastmcp import FastMCP


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Erk MCP server.")
    parser.add_argument("--host", default=os.getenv("ERK_MCP_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument(
        "--transport",
        choices=["streamable-http", "stdio"],
        default="streamable-http",
    )
    return parser.parse_args(argv)


def _get_oauth_discovery_url(mcp: FastMCP) -> str | None:
    auth = mcp.auth
    if auth is None or auth.base_url is None:
        return None
    return f"{str(auth.base_url).rstrip('/')}/.well-known/oauth-authorization-server"


def main() -> None:
    args = _parse_args(None)
    try:
        mcp = create_mcp()
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if args.transport == "stdio":
        mcp.run()
    else:
        click.echo(f"Starting erk MCP server on http://{args.host}:{args.port}/mcp")
        oauth_discovery_url = _get_oauth_discovery_url(mcp)
        if oauth_discovery_url is not None:
            click.echo(f"GitHub OAuth discovery available at {oauth_discovery_url}")
        mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
