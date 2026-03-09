"""FastMCP server exposing erk capabilities as MCP tools."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING, Any

from anyio import to_thread
from fastmcp.tools.tool import Tool, ToolResult

from erk_shared.agentclick.json_schema import command_input_schema
from erk_shared.agentclick.mcp_exposed import discover_mcp_commands

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


def _run_erk_json(command_path: tuple[str, ...], params: dict[str, Any]) -> str:
    """Run erk command with --json, piping params as JSON stdin.

    Args:
        command_path: Tuple of subcommand names, e.g. ("pr", "list") or ("one-shot",).
        params: JSON-serializable dict piped to stdin.
    """
    result = subprocess.run(
        ["erk", *command_path, "--json"],
        input=json.dumps(params),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout


class JsonCommandTool(Tool):
    """MCP tool backed by an erk @json_command CLI command.

    Dynamically registers a CLI command as an MCP tool using the command's
    input schema derived from Click parameters. The tool filters out None
    values before piping params as JSON to the CLI.
    """

    cli_command_path: tuple[str, ...]

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        params: dict[str, Any] = {}
        for k, v in arguments.items():
            if v is not None:
                params[k] = v
        path = self.cli_command_path
        result = await to_thread.run_sync(lambda: _run_erk_json(path, params))
        return self.convert_result(result)


def _build_json_command_tools() -> tuple[JsonCommandTool, ...]:
    """Discover @mcp_exposed commands and build JsonCommandTool instances."""
    from erk.cli.cli import cli

    tools: list[JsonCommandTool] = []
    for cmd, meta, command_path in discover_mcp_commands(cli):
        assert cmd.name is not None
        tools.append(
            JsonCommandTool(
                name=meta.name,
                cli_command_path=command_path,
                description=meta.description,
                parameters=command_input_schema(cmd),
            )
        )
    return tuple(tools)


def create_mcp() -> FastMCP:
    """Create and configure the FastMCP server instance."""
    from fastmcp import FastMCP

    server = FastMCP(DEFAULT_MCP_NAME)
    # Auto-discovered @mcp_exposed @json_command tools
    for tool in _build_json_command_tools():
        server.add_tool(tool)
    return server
