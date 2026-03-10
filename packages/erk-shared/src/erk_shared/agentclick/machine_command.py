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

import dataclasses
import json
import sys
from dataclasses import dataclass, fields
from typing import Any, Literal, get_args, get_origin

import click


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
    if sys.stdin.isatty():
        return None
    raw = sys.stdin.read()
    if not raw.strip():
        return None
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("JSON input must be an object")
    return data


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
    from_json = getattr(request_type, "from_json_dict", None)
    if from_json is not None:
        return from_json(data)
    return _build_dataclass_request(request_type, data)


def _build_dataclass_request(request_type: type, data: dict[str, Any]) -> Any:
    """Build a dataclass from JSON dict with strict validation.

    - Rejects unknown keys
    - Applies type coercion
    - Fills in defaults for missing fields
    """
    valid_fields = {f.name: f for f in fields(request_type)}

    # Reject unknown keys
    for key in data:
        if key not in valid_fields:
            raise ValueError(f"Unknown field: {key}")

    kwargs: dict[str, Any] = {}
    for name, field in valid_fields.items():
        if name in data:
            kwargs[name] = _coerce_value(data[name], field.type)
        elif field.default is not dataclasses.MISSING:
            kwargs[name] = field.default
        elif field.default_factory is not dataclasses.MISSING:
            kwargs[name] = field.default_factory()
        else:
            raise ValueError(f"Missing required field: {name}")

    return request_type(**kwargs)


def _coerce_value(value: Any, target_type: Any) -> Any:
    """Coerce a JSON value to the expected Python type.

    Handles: Literal, tuple, list, dict, bool, int, float, str,
    X | None unions, and passes through unrecognized types.
    """
    origin = get_origin(target_type)
    args = get_args(target_type)

    # Literal validation
    if origin is Literal:
        if value not in args:
            raise ValueError(f"Invalid value {value!r}, expected one of {args}")
        return value

    # tuple[X, ...] from JSON arrays
    if origin is tuple and len(args) == 2 and args[1] is Ellipsis:
        if isinstance(value, list):
            return tuple(_coerce_value(v, args[0]) for v in value)
        return value

    # list[X]
    if origin is list and len(args) == 1:
        if isinstance(value, list):
            return [_coerce_value(v, args[0]) for v in value]
        return value

    # dict[K, V]
    if origin is dict:
        return value

    # Union types (X | None)
    import types

    if origin is types.UnionType:
        if value is None and type(None) in args:
            return None
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _coerce_value(value, non_none[0])
        return value

    # bool must be checked before int (bool is subclass of int)
    if target_type is bool:
        if isinstance(value, bool):
            return value
        raise ValueError(f"Expected boolean, got {type(value).__name__}")

    if target_type is int:
        if isinstance(value, bool):
            raise ValueError("Expected integer, got boolean")
        if isinstance(value, int):
            return value
        return value

    if target_type is float:
        if isinstance(value, (int, float)):
            return float(value)
        return value

    if target_type is str:
        if isinstance(value, str):
            return value
        return value

    return value


def _serialize_machine_result(result: Any) -> dict[str, Any]:
    """Serialize a result to a JSON-compatible dict.

    Checks for to_json_dict() protocol first, falls back to
    dataclasses.asdict() for plain dataclasses.
    """
    if hasattr(result, "to_json_dict"):
        return result.to_json_dict()
    if dataclasses.is_dataclass(result) and not isinstance(result, type):
        return dataclasses.asdict(result)
    raise TypeError(
        f"Cannot serialize {type(result).__name__}: no to_json_dict() and not a dataclass"
    )


def emit_machine_error(error: MachineCommandError) -> None:
    """Emit a structured error to stdout."""
    data = {"success": False, "error_type": error.error_type, "message": error.message}
    click.echo(json.dumps(data, indent=2))


def emit_machine_result(result: Any) -> None:
    """Emit a structured success result to stdout."""
    data = _serialize_machine_result(result)
    data["success"] = True
    click.echo(json.dumps(data, indent=2))


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
