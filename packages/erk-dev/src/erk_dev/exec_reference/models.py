"""Data models for exec command introspection."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecParamInfo:
    """Information about a command parameter."""

    name: str
    param_type: str  # "argument" or "option"
    type_hint: str  # e.g., "INTEGER", "TEXT", "FLAG"
    required: bool
    help_text: str
    default_repr: str | None
    option_names: tuple[str, ...] | None  # For options: ("-f", "--force")


@dataclass(frozen=True)
class ExecCommandInfo:
    """Information about an exec command."""

    name: str
    help_text: str
    params: tuple[ExecParamInfo, ...]
    subcommands: tuple["ExecCommandInfo", ...]
