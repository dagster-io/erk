"""Tests for @json_command that depend on the erk CLI tree."""

import types
import typing

import click

from erk.cli.cli import cli

# -- output_types validation test --


def test_output_types_matches_return_annotation() -> None:
    """Every @json_command's output_types must match its return annotation."""

    def _collect_json_commands(group: click.BaseCommand) -> list[click.BaseCommand]:
        """Recursively collect all commands with _json_command_meta."""
        result = []
        if hasattr(group, "_json_command_meta"):
            result.append(group)
        if isinstance(group, click.Group):
            for cmd in group.commands.values():
                result.extend(_collect_json_commands(cmd))
        return result

    def _unwrap_return_types(annotation: typing.Any) -> set[type]:
        """Decompose A | B unions into member types."""
        origin = typing.get_origin(annotation)
        if origin is typing.Union or isinstance(annotation, types.UnionType):
            return set(typing.get_args(annotation))
        return {annotation}

    commands = _collect_json_commands(cli)
    assert len(commands) > 0, "No @json_command commands found — check CLI import"

    failures = []
    for cmd in commands:
        meta = cmd._json_command_meta  # type: ignore[attr-defined]
        original_callback = cmd._json_command_original_callback  # type: ignore[attr-defined]
        if original_callback is None:
            continue

        hints = typing.get_type_hints(original_callback)
        return_annotation = hints.get("return", type(None))

        if return_annotation is type(None):
            # -> None means output_types must be ()
            if meta.output_types != ():
                failures.append(f"{cmd.name}: return None but output_types={meta.output_types!r}")
        else:
            return_types = _unwrap_return_types(return_annotation)
            declared_types = set(meta.output_types)
            # NoneType in the union is allowed (means "command emitted JSON
            # inline or returned nothing"); strip it before comparing.
            return_types_no_none = return_types - {type(None)}
            if return_types_no_none != declared_types:
                failures.append(
                    f"{cmd.name}: return annotation types {return_types_no_none}"
                    f" != output_types {declared_types}"
                )

    assert not failures, "output_types mismatch:\n" + "\n".join(failures)
