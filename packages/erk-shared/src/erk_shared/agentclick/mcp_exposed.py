"""Decorator and discovery for auto-exposing @json_command CLIs as MCP tools."""

from collections.abc import Callable
from dataclasses import dataclass

import click


@dataclass(frozen=True)
class McpMeta:
    """MCP metadata attached to a Click command by @mcp_exposed."""

    name: str
    description: str


_MCP_REGISTRY: dict[click.Command, McpMeta] = {}



def mcp_exposed(*, name: str, description: str) -> Callable[[click.Command], click.Command]:
    """Mark a @json_command for automatic MCP exposure.

    Apply above @json_command in the decorator stack:

        @mcp_exposed(name="one_shot", description="...")
        @json_command(...)
        @click.command("one-shot")

    Args:
        name: MCP tool name
        description: MCP tool description
    """

    def decorator(cmd: click.Command) -> click.Command:
        _MCP_REGISTRY[cmd] = McpMeta(name=name, description=description)
        return cmd

    return decorator


def discover_mcp_commands(group: click.Command) -> list[tuple[click.Command, McpMeta]]:
    """Walk the Click command tree and return commands with MCP metadata.

    Args:
        group: Root Click group to walk

    Returns:
        List of (command, McpMeta) tuples for all @mcp_exposed commands
    """
    result: list[tuple[click.Command, McpMeta]] = []
    meta = _MCP_REGISTRY.get(group)
    if meta is not None:
        result.append((group, meta))
    if isinstance(group, click.Group):
        for cmd in group.commands.values():
            result.extend(discover_mcp_commands(cmd))
    return result
