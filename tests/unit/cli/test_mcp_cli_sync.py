"""Parity tests: every @machine_command is discovered and has correct schema."""

from __future__ import annotations

import asyncio

from erk.cli.cli import cli
from erk_mcp.server import _build_machine_command_tools, create_mcp
from erk_shared.agentclick.machine_schema import request_schema
from erk_shared.agentclick.mcp_exposed import discover_machine_commands


def test_every_machine_command_is_registered_as_mcp_tool() -> None:
    """Every command with _machine_command_meta in the Click tree appears as an MCP tool."""
    discovered = discover_machine_commands(cli, _parent_path=())
    assert len(discovered) > 0, "No @machine_command commands found — check CLI imports"

    server = create_mcp()
    tools = asyncio.run(server.list_tools())
    tool_names = {t.name for t in tools}

    for _cmd, meta, _path in discovered:
        assert meta.name in tool_names, f"@machine_command '{meta.name}' not registered as MCP tool"


def test_mcp_tool_schema_matches_request_derived_schema() -> None:
    """Each MCP tool's schema matches request_schema(meta.request_type)."""
    discovered = discover_machine_commands(cli, _parent_path=())

    built_tools = _build_machine_command_tools()
    tool_by_name = {t.name: t for t in built_tools}

    for _cmd, meta, _path in discovered:
        assert meta.name in tool_by_name, f"Tool '{meta.name}' not built"
        expected_schema = request_schema(meta.request_type)
        actual_schema = tool_by_name[meta.name].parameters
        assert actual_schema == expected_schema, (
            f"Schema mismatch for '{meta.name}':\n"
            f"  expected: {expected_schema}\n"
            f"  actual:   {actual_schema}"
        )


def test_every_mcp_tool_has_corresponding_machine_command() -> None:
    """Every MachineCommandTool corresponds to a real @machine_command (no orphans)."""
    discovered = discover_machine_commands(cli, _parent_path=())
    discovered_names = {meta.name for _cmd, meta, _path in discovered}

    built_tools = _build_machine_command_tools()
    for tool in built_tools:
        assert tool.name in discovered_names, (
            f"MachineCommandTool '{tool.name}' has no corresponding @machine_command"
        )
