"""Introspection and generation logic for exec command reference documentation."""

import click

from erk.cli.commands.exec.group import exec_group
from erk_dev.exec_reference.models import ExecCommandInfo, ExecParamInfo


def _extract_param_info(param: click.Parameter) -> ExecParamInfo:
    """Extract parameter information from a Click parameter."""
    if isinstance(param, click.Argument):
        param_type = "argument"
        option_names = None
        # Arguments are required unless nargs allows 0
        required = param.required
    else:
        # Option
        param_type = "option"
        option_names = tuple(param.opts) if param.opts else None
        required = param.required

    # Determine type hint
    if isinstance(param, click.Option) and param.is_flag:
        type_hint = "FLAG"
    elif param.type is not None:
        type_hint = param.type.name.upper()
    else:
        type_hint = "TEXT"

    # Default representation
    default_repr = None
    if isinstance(param, click.Option) and param.default is not None and not param.is_flag:
        default_repr = repr(param.default)

    return ExecParamInfo(
        name=param.name or "",
        param_type=param_type,
        type_hint=type_hint,
        required=required,
        help_text=getattr(param, "help", None) or "",
        default_repr=default_repr,
        option_names=option_names,
    )


def _extract_command_info(
    *,
    cmd: click.Command,
    name: str,
) -> ExecCommandInfo:
    """Extract command information from a Click command."""
    # Get help text (first line of docstring)
    help_text = cmd.help or ""
    if "\n" in help_text:
        help_text = help_text.split("\n")[0].strip()

    # Extract parameters
    params: list[ExecParamInfo] = []
    for param in cmd.params:
        # Skip --help option
        if isinstance(param, click.Option) and "--help" in (param.opts or []):
            continue
        params.append(_extract_param_info(param))

    # Extract subcommands if this is a group
    subcommands: list[ExecCommandInfo] = []
    if isinstance(cmd, click.Group):
        for subcmd_name, subcmd in sorted(cmd.commands.items()):
            subcommands.append(_extract_command_info(cmd=subcmd, name=subcmd_name))

    return ExecCommandInfo(
        name=name,
        help_text=help_text,
        params=tuple(params),
        subcommands=tuple(subcommands),
    )


def collect_exec_commands() -> list[ExecCommandInfo]:
    """Collect all exec commands by introspecting the exec_group."""
    commands: list[ExecCommandInfo] = []

    for name, cmd in sorted(exec_group.commands.items()):
        commands.append(_extract_command_info(cmd=cmd, name=name))

    return commands


def _format_option_flags(param: ExecParamInfo) -> str:
    """Format option flags for display."""
    if param.option_names:
        return ", ".join(f"`{opt}`" for opt in param.option_names)
    return f"`--{param.name}`"


def _generate_command_section(
    *,
    cmd: ExecCommandInfo,
    prefix: str,
    heading_level: int,
) -> list[str]:
    """Generate markdown section for a command."""
    lines: list[str] = []
    full_name = f"{prefix} {cmd.name}".strip()
    heading = "#" * heading_level

    lines.append(f"{heading} {cmd.name}")
    lines.append("")

    if cmd.help_text:
        lines.append(cmd.help_text)
        lines.append("")

    # Usage line
    usage_parts = [f"`erk exec {full_name}`"]
    for param in cmd.params:
        if param.param_type == "argument":
            if param.required:
                usage_parts.append(f"<{param.name}>")
            else:
                usage_parts.append(f"[{param.name}]")
    lines.append(f"**Usage:** {' '.join(usage_parts)}")
    lines.append("")

    # Arguments table
    arguments = [p for p in cmd.params if p.param_type == "argument"]
    if arguments:
        lines.append("**Arguments:**")
        lines.append("")
        lines.append("| Name | Required | Description |")
        lines.append("|------|----------|-------------|")
        for arg in arguments:
            required = "Yes" if arg.required else "No"
            help_text = arg.help_text or "-"
            lines.append(f"| `{arg.name.upper()}` | {required} | {help_text} |")
        lines.append("")

    # Options table
    options = [p for p in cmd.params if p.param_type == "option"]
    if options:
        lines.append("**Options:**")
        lines.append("")
        lines.append("| Flag | Type | Required | Default | Description |")
        lines.append("|------|------|----------|---------|-------------|")
        for opt in options:
            flags = _format_option_flags(opt)
            required = "Yes" if opt.required else "No"
            default = opt.default_repr or "-"
            help_text = opt.help_text or "-"
            lines.append(f"| {flags} | {opt.type_hint} | {required} | {default} | {help_text} |")
        lines.append("")

    # Subcommands
    for subcmd in cmd.subcommands:
        lines.extend(
            _generate_command_section(
                cmd=subcmd,
                prefix=full_name,
                heading_level=heading_level + 1,
            )
        )

    return lines


SKILL_FRONTMATTER = """\
---
name: erk-exec-reference
description: Reference for all `erk exec` subcommands with flags and usage. Use when looking up erk exec command syntax, flags, or options.
---
"""


def generate_exec_reference(commands: list[ExecCommandInfo]) -> str:
    """Generate markdown reference documentation for exec commands."""
    lines: list[str] = []

    # Frontmatter for skill
    lines.append(SKILL_FRONTMATTER.rstrip())
    lines.append("")

    # Header
    lines.append("<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->")
    lines.append("<!-- Run 'erk-dev gen-exec-reference-docs' to regenerate. -->")
    lines.append("")
    lines.append("# erk exec Commands Reference")
    lines.append("")
    lines.append("Quick reference for all `erk exec` subcommands.")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Command | Description |")
    lines.append("|---------|-------------|")

    def add_summary_row(*, cmd: ExecCommandInfo, prefix: str) -> None:
        full_name = f"{prefix} {cmd.name}".strip() if prefix else cmd.name
        if cmd.subcommands:
            # Group: list subcommands
            for subcmd in cmd.subcommands:
                add_summary_row(cmd=subcmd, prefix=full_name)
        else:
            # Leaf command
            help_text = cmd.help_text or "-"
            lines.append(f"| `{full_name}` | {help_text} |")

    for cmd in commands:
        add_summary_row(cmd=cmd, prefix="")

    lines.append("")

    # Detailed command sections
    lines.append("## Commands")
    lines.append("")

    for cmd in commands:
        lines.extend(
            _generate_command_section(
                cmd=cmd,
                prefix="",
                heading_level=3,
            )
        )

    return "\n".join(lines)
