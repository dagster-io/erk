"""Parity tests: every @mcp_exposed command is discovered and has correct schema."""

from __future__ import annotations

import asyncio

from erk.cli.cli import cli
from erk.cli.json_schema import command_input_schema
from erk.cli.mcp_exposed import discover_mcp_commands
from erk_mcp.server import _build_json_command_tools, create_mcp


def test_every_mcp_exposed_command_is_registered_as_mcp_tool() -> None:
    """Every command with _mcp_meta in the Click tree appears as an MCP tool."""
    discovered = discover_mcp_commands(cli)
    assert len(discovered) > 0, "No @mcp_exposed commands found — check CLI imports"

    server = create_mcp()
    tools = asyncio.run(server.list_tools())
    tool_names = {t.name for t in tools}

    for _cmd, meta in discovered:
        assert meta.name in tool_names, f"@mcp_exposed '{meta.name}' not registered as MCP tool"


def test_mcp_tool_schema_matches_click_derived_schema() -> None:
    """Each MCP tool's schema matches command_input_schema(cmd)."""
    discovered = discover_mcp_commands(cli)

    built_tools = _build_json_command_tools()
    tool_by_name = {t.name: t for t in built_tools}

    for cmd, meta in discovered:
        assert meta.name in tool_by_name, f"Tool '{meta.name}' not built"
        expected_schema = command_input_schema(cmd)
        actual_schema = tool_by_name[meta.name].parameters
        assert actual_schema == expected_schema, (
            f"Schema mismatch for '{meta.name}':\n"
            f"  expected: {expected_schema}\n"
            f"  actual:   {actual_schema}"
        )


def test_every_mcp_json_command_tool_has_corresponding_mcp_exposed_command() -> None:
    """Every JsonCommandTool corresponds to a real @mcp_exposed command (no orphans)."""
    discovered = discover_mcp_commands(cli)
    discovered_names = {meta.name for _cmd, meta in discovered}

    built_tools = _build_json_command_tools()
    for tool in built_tools:
        assert tool.name in discovered_names, (
            f"JsonCommandTool '{tool.name}' has no corresponding @mcp_exposed command"
        )


def test_mcp_exposed_commands_have_json_command_meta() -> None:
    """Every @mcp_exposed command must also have @json_command."""
    discovered = discover_mcp_commands(cli)
    for cmd, meta in discovered:
        assert hasattr(cmd, "_json_command_meta"), (
            f"@mcp_exposed '{meta.name}' on '{cmd.name}' is missing @json_command"
        )
