"""Tests for machine commands in the erk CLI tree."""

from __future__ import annotations

import types
import typing

import click

from erk.cli.cli import cli
from erk_shared.agentclick.machine_command import MachineCommandError


def test_machine_command_output_types_match_return_annotation() -> None:
    """Every machine command's output_types must match its return annotation."""

    def _collect_machine_commands(
        group: click.BaseCommand,
        *,
        path: tuple[str, ...],
    ) -> list[tuple[click.BaseCommand, tuple[str, ...]]]:
        result: list[tuple[click.BaseCommand, tuple[str, ...]]] = []
        if hasattr(group, "_machine_command_meta"):
            result.append((group, path))
        if isinstance(group, click.Group):
            for name, cmd in group.commands.items():
                result.extend(_collect_machine_commands(cmd, path=(*path, name)))
        return result

    def _unwrap_return_types(annotation: typing.Any) -> set[type]:
        origin = typing.get_origin(annotation)
        if origin is typing.Union or isinstance(annotation, types.UnionType):
            return set(typing.get_args(annotation))
        return {annotation}

    commands = _collect_machine_commands(cli, path=())
    assert commands, "No machine commands found"

    failures = []
    for cmd, path in commands:
        assert path[0] == "json", f"Machine command is not rooted under erk json: {path}"
        meta = cmd._machine_command_meta  # type: ignore[attr-defined]
        original_callback = cmd._machine_command_original_callback  # type: ignore[attr-defined]
        if original_callback is None:
            continue

        hints = typing.get_type_hints(original_callback)
        return_annotation = hints.get("return", type(None))
        return_types = _unwrap_return_types(return_annotation)
        return_types_no_error = return_types - {MachineCommandError, type(None)}
        declared_types = set(meta.output_types)

        if return_types_no_error != declared_types:
            failures.append(
                f"{path}: return annotation types {return_types_no_error}"
                f" != output_types {declared_types}"
            )

    assert not failures, "output_types mismatch:\n" + "\n".join(failures)


def test_human_commands_do_not_expose_machine_flags() -> None:
    one_shot = cli.commands["one-shot"]
    pr_group = cli.commands["pr"]
    assert isinstance(pr_group, click.Group)
    pr_list = pr_group.commands["list"]
    pr_view = pr_group.commands["view"]

    for cmd in (one_shot, pr_list, pr_view):
        param_names = {param.name for param in cmd.params if param.name is not None}
        assert "schema_mode" not in param_names
        assert "json_stdout" not in param_names
        assert "stdin_json" not in param_names
