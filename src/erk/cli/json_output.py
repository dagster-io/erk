"""JSON output decorator for CLI commands.

Adds a --json flag to Click commands and handles error serialization.
Commands handle success JSON inline via emit_json(); the decorator only
handles the error path uniformly by catching UserFacingCliError.
"""

import json
from typing import Any

import click

from erk.cli.ensure import UserFacingCliError


def json_output(cmd: click.Command) -> click.Command:
    """Add --json flag and JSON error handling to a Click command.

    Must be applied ABOVE @click.command (i.e., listed above it in the
    decorator stack). This is because decorators are applied bottom-to-top,
    so @json_output runs AFTER @click.command creates the Command object.

    When --json is passed:
    - UserFacingCliError is caught and serialized as JSON to stdout
    - SystemExit and other exceptions pass through unchanged

    When --json is not passed:
    - Delegates to the original callback unchanged

    Usage:
        @json_output
        @click.command("my-cmd")
        @click.pass_obj
        def my_cmd(ctx, *, json_mode: bool, ...):
            if json_mode:
                emit_json({"key": "value"})
                return
            # normal human output
    """
    json_option = click.Option(
        ["--json", "json_mode"],
        is_flag=True,
        default=False,
        help="Output results as JSON",
    )
    cmd.params.append(json_option)

    original_callback = cmd.callback
    if original_callback is None:
        return cmd

    def wrapped_callback(**kwargs: Any) -> Any:
        json_mode = kwargs.pop("json_mode", False)
        kwargs["json_mode"] = json_mode
        if not json_mode:
            return original_callback(**kwargs)

        try:
            return original_callback(**kwargs)
        except UserFacingCliError as exc:
            error_data = {
                "success": False,
                "error_type": exc.error_type,
                "message": exc.format_message(),
            }
            click.echo(json.dumps(error_data))
            raise SystemExit(1) from None
        except SystemExit:
            raise

    wrapped_callback.__name__ = getattr(original_callback, "__name__", "wrapped")
    wrapped_callback.__doc__ = getattr(original_callback, "__doc__", None)
    cmd.callback = wrapped_callback

    return cmd


def emit_json(data: dict[str, Any]) -> None:
    """Emit a JSON success result to stdout. Adds success=True automatically."""
    data["success"] = True
    click.echo(json.dumps(data))
