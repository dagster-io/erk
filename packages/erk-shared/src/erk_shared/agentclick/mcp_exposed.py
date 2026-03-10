"""Discovery for auto-exposing @machine_command CLIs as MCP tools.

MCP metadata (name, description) is stored directly in MachineCommandMeta
by the @machine_command decorator. Discovery walks the Click command tree
to find commands with _machine_command_meta.
"""

import click

from erk_shared.agentclick.machine_command import MachineCommandMeta


def discover_machine_commands(
    group: click.Command,
    *,
    _parent_path: tuple[str, ...] = (),
) -> list[tuple[click.Command, MachineCommandMeta, tuple[str, ...]]]:
    """Walk the Click command tree and return commands with MachineCommandMeta.

    Args:
        group: Root Click group to walk
        _parent_path: Internal accumulator for the command path (do not pass)

    Returns:
        List of (command, MachineCommandMeta, command_path) tuples.
        command_path is the tuple of Click command names from root to the command
        (excluding the root group itself), e.g. ("json", "pr", "list").
    """
    result: list[tuple[click.Command, MachineCommandMeta, tuple[str, ...]]] = []
    meta = getattr(group, "_machine_command_meta", None)
    if isinstance(meta, MachineCommandMeta):
        result.append((group, meta, _parent_path))
    if isinstance(group, click.Group):
        for cmd in group.commands.values():
            child_path = (*_parent_path, cmd.name) if cmd.name is not None else _parent_path
            result.extend(discover_machine_commands(cmd, _parent_path=child_path))
    return result
