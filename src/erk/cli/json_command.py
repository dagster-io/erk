"""JSON command harness for CLI commands (input + output).

Adds a --json flag to Click commands with:
- JSON error serialization (catches UserFacingCliError)
- JSON input from stdin (when piped, maps keys to Click params)
- emit_json_result() for structured output via to_json_dict() protocol

Commands return a result object with to_json_dict() or as a dataclass;
the decorator auto-serializes it via emit_json_result() when --json is active.
Commands may also call emit_json()/emit_json_result() inline and return None.
"""

import dataclasses
import json
import sys
from typing import Any, overload

import click

from erk.cli.ensure import UserFacingCliError


@overload
def json_command(cmd: click.Command) -> click.Command: ...


@overload
def json_command(
    *,
    exclude_json_input: frozenset[str] = ...,
    required_json_input: frozenset[str] = ...,
) -> Any: ...


def json_command(
    cmd: click.Command | None = None,
    *,
    exclude_json_input: frozenset[str] | None = None,
    required_json_input: frozenset[str] | None = None,
) -> click.Command | Any:
    """Add --json flag, JSON input mapping, and JSON error handling to a Click command.

    Must be applied ABOVE @click.command (i.e., listed above it in the
    decorator stack). This is because decorators are applied bottom-to-top,
    so @json_command runs AFTER @click.command creates the Command object.

    Supports two forms:
        @json_command                           # no config
        @json_command(exclude_json_input=...)   # with config

    When --json is passed:
    - If stdin is piped (not a TTY), reads JSON object and maps keys to kwargs
    - UserFacingCliError is caught and serialized as JSON to stdout
    - SystemExit and other exceptions pass through unchanged

    When --json is not passed:
    - Delegates to the original callback unchanged

    Args:
        cmd: Click Command object (when used as bare decorator)
        exclude_json_input: Param names to skip when mapping JSON input
        required_json_input: Param names that must be present and non-None in JSON input
    """
    resolved_exclude = exclude_json_input if exclude_json_input is not None else frozenset()
    resolved_required = required_json_input if required_json_input is not None else frozenset()

    if cmd is not None:
        return _apply_json_command(cmd, resolved_exclude, resolved_required)

    def decorator(cmd: click.Command) -> click.Command:
        return _apply_json_command(cmd, resolved_exclude, resolved_required)

    return decorator


def read_stdin_json() -> dict[str, Any] | None:
    """Read a JSON object from stdin if piped. Returns None if stdin is a TTY or empty.

    Raises:
        json.JSONDecodeError: If stdin contains invalid JSON
        ValueError: If stdin JSON is not an object
    """
    if sys.stdin.isatty():
        return None
    raw = sys.stdin.read()
    if not raw.strip():
        return None
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("JSON input must be an object")
    return data


def _apply_json_command(
    cmd: click.Command,
    exclude_json_input: frozenset[str],
    required_json_input: frozenset[str],
) -> click.Command:
    """Apply the json_command behavior to a Click command."""
    json_option = click.Option(
        ["--json", "json_mode"],
        is_flag=True,
        help="Output results as JSON",
    )
    cmd.params.append(json_option)

    original_callback = cmd.callback
    if original_callback is None:
        return cmd

    # Collect valid param names from the command for input validation
    valid_param_names = frozenset(p.name for p in cmd.params if p.name is not None)

    def wrapped_callback(**kwargs: Any) -> Any:
        json_mode = kwargs.pop("json_mode", False)
        kwargs["json_mode"] = json_mode
        if not json_mode:
            return original_callback(**kwargs)

        # JSON input: read from stdin when piped
        try:
            input_data = read_stdin_json()
        except json.JSONDecodeError as exc:
            error_data = {
                "success": False,
                "error_type": "invalid_json_input",
                "message": f"Invalid JSON: {exc}",
            }
            click.echo(json.dumps(error_data))
            raise SystemExit(1) from None
        except ValueError as exc:
            error_data = {
                "success": False,
                "error_type": "invalid_json_input",
                "message": str(exc),
            }
            click.echo(json.dumps(error_data))
            raise SystemExit(1) from None

        if input_data is not None:
            # Validate keys
            skip_keys = exclude_json_input | {"json_mode"}
            for key in input_data:
                if key not in valid_param_names or key in skip_keys:
                    error_data = {
                        "success": False,
                        "error_type": "invalid_json_input",
                        "message": f"Unknown key: {key}",
                    }
                    click.echo(json.dumps(error_data))
                    raise SystemExit(1)

            # Map JSON keys to kwargs (override defaults only)
            for key, value in input_data.items():
                if key not in skip_keys:
                    kwargs[key] = value

        # Validate required fields
        for field in required_json_input:
            if kwargs.get(field) is None:
                error_data = {
                    "success": False,
                    "error_type": "invalid_json_input",
                    "message": f"Missing required field: {field}",
                }
                click.echo(json.dumps(error_data))
                raise SystemExit(1)

        try:
            result = original_callback(**kwargs)
            if result is not None:
                emit_json_result(result)
            return result
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


def emit_json_result(result: Any) -> None:
    """Emit a structured result as JSON.

    Calls result.to_json_dict() if available, falls back to
    dataclasses.asdict() for plain dataclasses.

    Raises:
        TypeError: If result has no to_json_dict() and is not a dataclass
    """
    if hasattr(result, "to_json_dict"):
        data = result.to_json_dict()
    elif dataclasses.is_dataclass(result) and not isinstance(result, type):
        data = dataclasses.asdict(result)
    else:
        raise TypeError(
            f"Cannot serialize {type(result).__name__}: no to_json_dict() and not a dataclass"
        )
    emit_json(data)
