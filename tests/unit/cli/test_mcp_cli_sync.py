"""Parity tests: every @mcp_exposed command is discovered and has correct schema."""

from __future__ import annotations

import asyncio

from erk.cli.cli import cli
from erk_mcp.server import _build_machine_command_tools, create_mcp
from erk_shared.agentclick.json_schema import command_input_schema
from erk_shared.agentclick.mcp_exposed import discover_mcp_commands


def test_every_mcp_exposed_command_is_registered_as_mcp_tool() -> None:
    """Every command with _mcp_meta in the Click tree appears as an MCP tool."""
    discovered = discover_mcp_commands(cli, _parent_path=())
    assert len(discovered) > 0, "No @mcp_exposed commands found — check CLI imports"

    server = create_mcp()
    tools = asyncio.run(server.list_tools())
    tool_names = {t.name for t in tools}

    for _cmd, meta, path in discovered:
        assert path[0] == "json"
        assert meta.name in tool_names, f"@mcp_exposed '{meta.name}' not registered as MCP tool"


def test_mcp_tool_schema_matches_click_derived_schema() -> None:
    """Each MCP tool's schema matches command_input_schema(cmd)."""
    discovered = discover_mcp_commands(cli, _parent_path=())

    built_tools = _build_machine_command_tools()
    tool_by_name = {t.name: t for t in built_tools}

    for cmd, meta, _path in discovered:
        assert meta.name in tool_by_name, f"Tool '{meta.name}' not built"
        expected_schema = command_input_schema(cmd)
        actual_schema = tool_by_name[meta.name].parameters
        assert actual_schema == expected_schema, (
            f"Schema mismatch for '{meta.name}':\n"
            f"  expected: {expected_schema}\n"
            f"  actual:   {actual_schema}"
        )


def test_every_mcp_machine_command_tool_has_corresponding_mcp_exposed_command() -> None:
    """Every MachineCommandTool corresponds to a real @mcp_exposed command."""
    discovered = discover_mcp_commands(cli, _parent_path=())
    discovered_names = {meta.name for _cmd, meta, _path in discovered}

    built_tools = _build_machine_command_tools()
    for tool in built_tools:
        assert tool.name in discovered_names, (
            f"MachineCommandTool '{tool.name}' has no corresponding @mcp_exposed command"
        )


def test_mcp_exposed_commands_have_machine_command_meta() -> None:
    """Every @mcp_exposed command must also be a machine command."""
    discovered = discover_mcp_commands(cli, _parent_path=())
    for cmd, meta, _path in discovered:
        assert hasattr(cmd, "_machine_command_meta"), (
            f"@mcp_exposed '{meta.name}' on '{cmd.name}' is missing @machine_command"
        )
