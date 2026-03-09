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


def discover_mcp_commands(
    group: click.Command,
    *,
    _parent_path: tuple[str, ...] = (),
) -> list[tuple[click.Command, McpMeta, tuple[str, ...]]]:
    """Walk the Click command tree and return commands with MCP metadata.

    Args:
        group: Root Click group to walk
        _parent_path: Internal accumulator for the command path (do not pass)

    Returns:
        List of (command, McpMeta, command_path) tuples for all @mcp_exposed commands.
        command_path is the tuple of Click command names from root to the command
        (excluding the root group itself), e.g. ("pr", "list") for ``erk pr list``.
    """
    result: list[tuple[click.Command, McpMeta, tuple[str, ...]]] = []
    meta = _MCP_REGISTRY.get(group)
    if meta is not None:
        result.append((group, meta, _parent_path))
    if isinstance(group, click.Group):
        for cmd in group.commands.values():
            child_path = (*_parent_path, cmd.name) if cmd.name is not None else _parent_path
            result.extend(discover_mcp_commands(cmd, _parent_path=child_path))
    return result
