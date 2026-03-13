"""FastMCP server exposing erk capabilities as MCP tools."""

from __future__ import annotations

import json
import os
import subprocess
from typing import TYPE_CHECKING, Any

from anyio import to_thread
from fastmcp.tools.tool import Tool, ToolResult
from mcp.server.auth.handlers.metadata import ProtectedResourceMetadataHandler
from mcp.shared.auth import ProtectedResourceMetadata
from starlette.requests import Request
from starlette.responses import Response

from erk_mcp.auth import build_auth_provider_from_env, get_authenticated_github_token
from erk_shared.agentclick.machine_schema import request_schema
from erk_shared.agentclick.mcp_exposed import discover_mcp_commands

if TYPE_CHECKING:
    from fastmcp import FastMCP

DEFAULT_MCP_NAME = "erk"
DEFAULT_MCP_HTTP_PATH = "/mcp"
ROOT_PROTECTED_RESOURCE_METADATA_PATH = "/.well-known/oauth-protected-resource"


def _build_subprocess_error_output(
    command_path: tuple[str, ...],
    *,
    returncode: int,
    stderr: str,
) -> str:
    stderr_lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    if stderr_lines:
        message = stderr_lines[-1]
    else:
        joined_path = " ".join(command_path)
        message = f"erk {joined_path} exited with code {returncode}"

    return json.dumps(
        {
            "success": False,
            "error_type": "cli_subprocess_error",
            "message": message,
        }
    )


def _run_erk_json(
    command_path: tuple[str, ...],
    params: dict[str, Any],
    *,
    env_override: dict[str, str] | None = None,
) -> str:
    """Run erk json command, piping params as JSON stdin.

    Args:
        command_path: Tuple of subcommand names, e.g. ("json", "pr", "list").
        params: JSON-serializable dict piped to stdin.
        env_override: Optional environment dict for the subprocess. None inherits process env.
    """
    result = subprocess.run(
        ["erk", *command_path],
        input=json.dumps(params),
        capture_output=True,
        text=True,
        check=False,
        env=env_override,
    )
    if result.stdout.strip():
        return result.stdout

    if result.returncode != 0:
        return _build_subprocess_error_output(
            command_path,
            returncode=result.returncode,
            stderr=result.stderr,
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
        user_token = get_authenticated_github_token()
        env_override: dict[str, str] | None = None
        if user_token is not None:
            env_override = {**os.environ, "GH_TOKEN": user_token}
        result = await to_thread.run_sync(
            lambda: _run_erk_json(path, params, env_override=env_override)
        )
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


def _build_root_protected_resource_metadata(
    auth: Any,
) -> ProtectedResourceMetadata | None:
    if auth is None or auth.base_url is None:
        return None

    authorization_server = auth.base_url
    if getattr(auth, "issuer_url", None) is not None:
        authorization_server = auth.issuer_url

    return ProtectedResourceMetadata(
        resource=f"{str(auth.base_url).rstrip('/')}{DEFAULT_MCP_HTTP_PATH}",
        authorization_servers=[str(authorization_server)],
        scopes_supported=getattr(auth, "required_scopes", None),
    )


def _add_oauth_compat_routes(server: FastMCP) -> None:
    metadata = _build_root_protected_resource_metadata(server.auth)
    if metadata is None:
        return

    handler = ProtectedResourceMetadataHandler(metadata)

    @server.custom_route(
        ROOT_PROTECTED_RESOURCE_METADATA_PATH,
        methods=["GET"],
        include_in_schema=False,
    )
    async def root_oauth_protected_resource_metadata(
        request: Request,
    ) -> Response:
        return await handler.handle(request)


def create_mcp() -> FastMCP:
    """Create and configure the FastMCP server instance."""
    from fastmcp import FastMCP

    server = FastMCP(DEFAULT_MCP_NAME, auth=build_auth_provider_from_env())
    _add_oauth_compat_routes(server)
    for tool in _build_machine_command_tools():
        server.add_tool(tool)
    return server


# Module-level instance for `fastmcp dev` CLI discovery (used by `make mcp-dev`)
mcp = create_mcp()
