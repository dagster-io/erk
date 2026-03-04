"""FastMCP server exposing erk capabilities as MCP tools."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

DEFAULT_MCP_NAME = "erk"


def _run_erk(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run an erk CLI command and return the result."""
    result = subprocess.run(
        ["erk", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f"erk {' '.join(args)} failed (exit {result.returncode}): {stderr}")
    return result


def plan_list(state: str | None = None) -> str:
    """List erk plans with their status, labels, and metadata.

    Returns structured JSON from the erk dashboard.
    Use the state parameter to filter by 'open' or 'closed'.
    """
    args = ["exec", "dash-data"]
    if state is not None:
        args.extend(["--state", state])
    result = _run_erk(args)
    return result.stdout


def plan_view(plan_id: int) -> str:
    """View a specific plan's metadata and body content.

    Returns the plan's title, state, labels, and full markdown body.
    """
    result = _run_erk(["exec", "get-plan-info", str(plan_id), "--include-body"])
    return result.stdout


def one_shot(prompt: str) -> str:
    """Submit a task for fully autonomous remote execution.

    Creates a branch, draft PR, and dispatches a GitHub Actions workflow
    where Claude autonomously explores, plans, implements, and submits.

    Returns after dispatch (~10-30s) with PR and workflow run URLs.
    """
    result = _run_erk(["one-shot", prompt])
    return result.stdout


def create_mcp() -> FastMCP:
    """Create and configure the FastMCP server instance."""
    from fastmcp import FastMCP

    server = FastMCP(DEFAULT_MCP_NAME)
    server.tool()(plan_list)
    server.tool()(plan_view)
    server.tool()(one_shot)
    return server
