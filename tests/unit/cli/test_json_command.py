"""Tests for @machine_command that depend on the erk CLI tree."""

import click

from erk.cli.cli import cli
from erk_shared.agentclick.machine_command import MachineCommandMeta


def test_machine_commands_have_result_types() -> None:
    """Every @machine_command has result_types matching its return annotation."""

    def _collect_machine_commands(group: click.BaseCommand) -> list[click.BaseCommand]:
        """Recursively collect all commands with _machine_command_meta."""
        result = []
        if hasattr(group, "_machine_command_meta"):
            result.append(group)
        if isinstance(group, click.Group):
            for cmd in group.commands.values():
                result.extend(_collect_machine_commands(cmd))
        return result

    commands = _collect_machine_commands(cli)
    assert len(commands) > 0, "No @machine_command commands found — check CLI imports"

    for cmd in commands:
        meta = cmd._machine_command_meta  # type: ignore[attr-defined]
        assert isinstance(meta, MachineCommandMeta), (
            f"Command '{cmd.name}' has wrong meta type: {type(meta)}"
        )
        assert len(meta.result_types) > 0 or meta.result_types == (), (
            f"Command '{cmd.name}' has no result_types"
        )
