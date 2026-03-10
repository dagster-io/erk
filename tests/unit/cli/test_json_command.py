"""Tests for @machine_command that depend on the erk CLI tree."""

import click

from erk.cli.cli import cli


def test_machine_commands_exist_in_json_tree() -> None:
    """At least one @machine_command exists under erk json."""
    json_group = cli.commands.get("json")
    assert json_group is not None, "erk json group not found in CLI tree"

    def _collect_machine_commands(group: click.Command) -> list[click.Command]:
        result = []
        if hasattr(group, "_machine_command_meta"):
            result.append(group)
        if isinstance(group, click.Group):
            for cmd in group.commands.values():
                result.extend(_collect_machine_commands(cmd))
        return result

    commands = _collect_machine_commands(json_group)
    assert len(commands) > 0, "No @machine_command commands found under erk json"
