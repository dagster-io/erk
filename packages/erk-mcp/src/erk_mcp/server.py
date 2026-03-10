"""FastMCP server exposing erk capabilities as MCP tools."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING, Any

from anyio import to_thread
from fastmcp.tools.tool import Tool, ToolResult

from erk_shared.agentclick.machine_schema import request_schema
from erk_shared.agentclick.mcp_exposed import discover_mcp_commands

if TYPE_CHECKING:
    from fastmcp import FastMCP

DEFAULT_MCP_NAME = "erk"


def _run_erk_json(command_path: tuple[str, ...], params: dict[str, Any]) -> str:
    """Run erk json command, piping params as JSON stdin.

    Args:
        command_path: Tuple of subcommand names, e.g. ("json", "pr", "list").
        params: JSON-serializable dict piped to stdin.
    """
    result = subprocess.run(
        ["erk", *command_path],
        input=json.dumps(params),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout


class MachineCommandTool(Tool):
    """MCP tool backed by an erk @machine_command CLI command.

    Dynamically registers a CLI command as an MCP tool using the
    command's request_type for input schema. The tool filters out
    None values before piping params as JSON to the CLI.
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


def _build_machine_command_tools() -> tuple[MachineCommandTool, ...]:
    """Discover @mcp_exposed commands and build MachineCommandTool instances."""
    from erk.cli.cli import cli

    tools: list[MachineCommandTool] = []
    for cmd, meta, command_path in discover_mcp_commands(cli, _parent_path=()):
        assert cmd.name is not None
        machine_meta = getattr(cmd, "_machine_command_meta", None)
        if machine_meta is None:
            continue
        tools.append(
            MachineCommandTool(
                name=meta.name,
                cli_command_path=command_path,
                description=meta.description,
                parameters=request_schema(machine_meta.request_type),
            )
        )
    return tuple(tools)


def create_mcp() -> FastMCP:
    """Create and configure the FastMCP server instance."""
    from fastmcp import FastMCP

    server = FastMCP(DEFAULT_MCP_NAME)
    for tool in _build_machine_command_tools():
        server.add_tool(tool)
    return server


# Module-level instance for `fastmcp dev` CLI discovery (used by `make mcp-dev`)
mcp = create_mcp()
