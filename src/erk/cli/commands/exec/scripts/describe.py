"""Describe an exec command's parameters as JSON schema.

Usage:
    erk exec describe get-pr-feedback
    erk exec describe setup-impl

Output:
    JSON with command name, help text, and parameter schema

Exit Codes:
    0: Always (success or error communicated via JSON)
"""

import click

from erk.cli.script_output import error_json, success_json

_SINGLETON_TYPE_NAMES: dict[int, str] = {
    id(click.STRING): "string",
    id(click.INT): "int",
    id(click.FLOAT): "float",
    id(click.BOOL): "bool",
}


def _click_type_to_str(param_type: click.ParamType) -> str:
    """Map Click parameter types to JSON-friendly strings."""
    label = _SINGLETON_TYPE_NAMES.get(id(param_type))
    if label is not None:
        return label

    if isinstance(param_type, click.Path):
        return "path"
    if isinstance(param_type, click.Choice):
        return "choice"
    if isinstance(param_type, click.IntRange):
        return "int"
    if isinstance(param_type, click.FloatRange):
        return "float"

    return param_type.name


@click.command(name="describe")
@click.argument("command_name")
@click.pass_context
def describe(ctx: click.Context, command_name: str) -> None:
    """Describe an exec command's parameters as JSON schema."""
    if ctx.parent is None:
        error_json("no-parent-context", "describe must be invoked as a subcommand of exec")
    exec_group = ctx.parent.command
    if not isinstance(exec_group, click.Group):
        error_json("invalid-parent", "Parent command is not a Click group")
    cmd = exec_group.get_command(ctx, command_name)
    if cmd is None:
        error_json("command-not-found", f"No exec command named '{command_name}'")

    params = []
    for param in cmd.params:
        param_info: dict[str, object] = {
            "name": param.name,
            "type": _click_type_to_str(param.type),
            "required": param.required,
            "is_flag": isinstance(param, click.Option) and param.is_flag,
        }
        if isinstance(param, click.Option):
            param_info["opts"] = param.opts
            param_info["kind"] = "option"
        elif isinstance(param, click.Argument):
            param_info["kind"] = "argument"

        if isinstance(param, click.Option) and param.help:
            param_info["help"] = param.help
        if param.default is not None and isinstance(param.default, (str, int, float, bool)):
            param_info["default"] = param.default
        if isinstance(param.type, click.Choice):
            param_info["choices"] = list(param.type.choices)
        params.append(param_info)

    success_json(
        {
            "command": command_name,
            "help": cmd.get_short_help_str(),
            "params": params,
        }
    )
