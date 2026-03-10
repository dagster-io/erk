"""Machine command decorator for pure-JSON CLI commands.

Provides @machine_command for commands that:
- Accept JSON input from stdin (not Click params)
- Return structured JSON output
- Use frozen dataclass request types for strict validation
- Support --schema flag for introspection

Unlike @json_command (which adds --json/--schema to human commands),
@machine_command creates dedicated machine-only commands with no
Click-based input parsing. The request type IS the input schema.
"""

import json
from dataclasses import dataclass
from typing import Any

import click

from erk_shared.agentclick.dataclass_json import (
    emit_json_error,
    emit_json_success,
    parse_dataclass_from_json,
    read_json_stdin,
    serialize_to_json_dict,
)


@dataclass(frozen=True)
class MachineCommandMeta:
    """Metadata stored on Command objects decorated with @machine_command."""

    request_type: type
    output_types: tuple[type, ...]


@dataclass(frozen=True)
class MachineCommandError:
    """Structured error result from a machine command."""

    error_type: str
    message: str


def machine_command(
    *,
    request_type: type,
    output_types: tuple[type, ...],
) -> Any:
    """Decorator for machine-only CLI commands with dataclass-based input.

    Must be applied ABOVE @click.command in the decorator stack.

    Adds --schema flag. Reads JSON from stdin, validates against request_type,
    and passes the constructed request to the callback. The callback receives
    the request as a keyword argument named 'request'.

    The callback should return a result object (dataclass or object with
    to_json_dict()) or a MachineCommandError. The decorator handles
    serialization.

    Args:
        request_type: Frozen dataclass type for input validation
        output_types: Result types for schema generation
    """

    def decorator(cmd: click.Command) -> click.Command:
        return _apply_machine_command(cmd, request_type, output_types)

    return decorator


def read_machine_command_input() -> dict[str, Any] | None:
    """Read JSON input from stdin for machine commands.

    Returns None if stdin is a TTY (interactive) or empty.

    Raises:
        json.JSONDecodeError: If stdin contains invalid JSON
        ValueError: If stdin JSON is not an object
    """
    return read_json_stdin()


def parse_machine_request(request_type: type, data: dict[str, Any]) -> Any:
    """Parse a JSON dict into a frozen dataclass request.

    Checks for from_json_dict() classmethod first. Falls back to
    generic dataclass construction with strict validation.

    Args:
        request_type: The frozen dataclass type
        data: JSON dict from stdin

    Returns:
        Instance of request_type

    Raises:
        ValueError: On validation errors (unknown fields, missing required, type mismatch)
    """
    return parse_dataclass_from_json(request_type, data)


def emit_machine_error(error: MachineCommandError) -> None:
    """Emit a structured error to stdout."""
    emit_json_error(error_type=error.error_type, message=error.message)


def emit_machine_result(result: Any) -> None:
    """Emit a structured success result to stdout."""
    data = serialize_to_json_dict(result)
    emit_json_success(data)


def _apply_machine_command(
    cmd: click.Command,
    request_type: type,
    output_types: tuple[type, ...],
) -> click.Command:
    """Wire up the machine_command behavior on a Click command."""
    cmd._machine_command_meta = MachineCommandMeta(  # type: ignore[attr-defined]
        request_type=request_type,
        output_types=output_types,
    )

    # Add --schema flag
    schema_option = click.Option(
        ["--schema", "schema_mode"],
        is_flag=True,
        default=False,
        help="Output JSON Schema for this command's input/output shapes",
    )
    cmd.params.append(schema_option)

    original_callback = cmd.callback
    if original_callback is None:
        return cmd

    def wrapped_callback(**kwargs: Any) -> Any:
        schema_mode = kwargs.pop("schema_mode", False)
        if schema_mode:
            from erk_shared.agentclick.machine_schema import build_machine_schema_document

            meta = MachineCommandMeta(request_type=request_type, output_types=output_types)
            schema_doc = build_machine_schema_document(meta)
            click.echo(json.dumps(schema_doc, indent=2))
            return None

        # Read JSON from stdin
        try:
            input_data = read_machine_command_input()
        except json.JSONDecodeError as exc:
            emit_machine_error(
                MachineCommandError(
                    error_type="invalid_json_input",
                    message=f"Invalid JSON: {exc}",
                )
            )
            raise SystemExit(1) from None
        except ValueError as exc:
            emit_machine_error(
                MachineCommandError(
                    error_type="invalid_json_input",
                    message=str(exc),
                )
            )
            raise SystemExit(1) from None

        if input_data is None:
            input_data = {}

        # Parse into request dataclass
        try:
            request = parse_machine_request(request_type, input_data)
        except ValueError as exc:
            emit_machine_error(
                MachineCommandError(
                    error_type="invalid_request",
                    message=str(exc),
                )
            )
            raise SystemExit(1) from None

        # Call the original callback with the request
        kwargs["request"] = request
        try:
            result = original_callback(**kwargs)
            if isinstance(result, MachineCommandError):
                emit_machine_error(result)
                raise SystemExit(1)
            if result is not None:
                emit_machine_result(result)
            return result
        except click.ClickException as exc:
            error_type_attr = getattr(exc, "error_type", None)
            if error_type_attr is not None:
                emit_machine_error(
                    MachineCommandError(
                        error_type=str(error_type_attr),
                        message=exc.format_message(),
                    )
                )
                raise SystemExit(1) from None
            raise
        except SystemExit:
            raise

    wrapped_callback.__name__ = getattr(original_callback, "__name__", "wrapped")
    wrapped_callback.__doc__ = getattr(original_callback, "__doc__", None)
    cmd.callback = wrapped_callback

    return cmd
