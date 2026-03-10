"""Machine command harness for explicit stdin/stdout JSON CLIs.

Machine commands are transport adapters over request/result contracts:

- Input comes from stdin as a JSON object
- Output goes to stdout as a structured JSON envelope
- ``--schema`` exposes the machine contract without executing the command

Human Click commands stay separate and do not share these transport flags.
"""

from __future__ import annotations

import dataclasses
import json
import sys
import types
from dataclasses import MISSING, dataclass
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

import click


@dataclass(frozen=True)
class MachineCommandError:
    """Structured machine-command failure."""

    error_type: str
    message: str


@dataclass(frozen=True)
class MachineCommandMeta:
    """Metadata stored on Click commands decorated with ``@machine_command``."""

    request_type: type
    output_types: tuple[type, ...]


def machine_command(
    *,
    request_type: type,
    output_types: tuple[type, ...],
) -> Any:
    """Attach machine-command transport behavior to a Click command."""

    def decorator(cmd: click.Command) -> click.Command:
        return _apply_machine_command(
            cmd,
            request_type=request_type,
            output_types=output_types,
        )

    return decorator


def emit_machine_error(error: MachineCommandError) -> None:
    """Emit a structured error envelope."""

    click.echo(
        json.dumps(
            {
                "success": False,
                "error_type": error.error_type,
                "message": error.message,
            },
            indent=2,
        )
    )


def emit_machine_result(result: Any) -> None:
    """Emit a structured success envelope."""

    click.echo(json.dumps(_serialize_machine_result(result), indent=2))


def parse_machine_request(
    request_type: type,
    data: dict[str, Any],
) -> Any | MachineCommandError:
    """Parse machine JSON into the declared request contract."""

    request_builder = getattr(request_type, "from_json_dict", None)
    if callable(request_builder):
        return request_builder(data)

    if not dataclasses.is_dataclass(request_type):
        return MachineCommandError(
            error_type="invalid_machine_contract",
            message=f"Request type {request_type.__name__} must be a dataclass",
        )

    return _build_dataclass_request(request_type, data)


def read_machine_command_input() -> dict[str, Any] | MachineCommandError:
    """Read machine input from stdin.

    Empty stdin is treated as an empty object so commands with all-optional
    request fields can still execute.
    """

    if sys.stdin.isatty():
        return {}

    raw = sys.stdin.read()
    if not raw.strip():
        return {}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return MachineCommandError(
            error_type="invalid_json_input",
            message=f"Invalid JSON: {exc}",
        )

    if not isinstance(data, dict):
        return MachineCommandError(
            error_type="invalid_json_input",
            message="JSON input must be an object",
        )

    return data


def _apply_machine_command(
    cmd: click.Command,
    *,
    request_type: type,
    output_types: tuple[type, ...],
) -> click.Command:
    cmd._machine_command_meta = MachineCommandMeta(  # type: ignore[attr-defined]
        request_type=request_type,
        output_types=output_types,
    )

    schema_option = click.Option(
        ["--schema", "schema_mode"],
        is_flag=True,
        default=False,
        help="Output JSON Schema for this machine command",
    )
    cmd.params.append(schema_option)

    original_callback = cmd.callback
    cmd._machine_command_original_callback = original_callback  # type: ignore[attr-defined]
    if original_callback is None:
        return cmd

    def wrapped_callback(**kwargs: Any) -> Any:
        schema_mode = kwargs.pop("schema_mode", False)
        if schema_mode:
            from erk_shared.agentclick.json_schema import build_schema_document

            click.echo(json.dumps(build_schema_document(cmd), indent=2))
            return None

        input_result = read_machine_command_input()
        if isinstance(input_result, MachineCommandError):
            emit_machine_error(input_result)
            return input_result

        request_result = parse_machine_request(request_type, input_result)
        if isinstance(request_result, MachineCommandError):
            emit_machine_error(request_result)
            return request_result

        kwargs["request"] = request_result

        try:
            result = original_callback(**kwargs)
        except click.ClickException as exc:
            error = MachineCommandError(
                error_type=_click_exception_error_type(exc),
                message=exc.format_message(),
            )
            emit_machine_error(error)
            return error

        if isinstance(result, MachineCommandError):
            emit_machine_error(result)
            return result

        emit_machine_result(result)
        return result

    wrapped_callback.__name__ = getattr(original_callback, "__name__", "wrapped")
    wrapped_callback.__doc__ = getattr(original_callback, "__doc__", None)
    cmd.callback = wrapped_callback
    return cmd


def _build_dataclass_request(
    request_type: type,
    data: dict[str, Any],
) -> Any | MachineCommandError:
    field_map = {field.name: field for field in dataclasses.fields(request_type)}
    field_types = _dataclass_field_types(request_type)

    for key in data:
        if key not in field_map:
            return MachineCommandError(
                error_type="invalid_json_input",
                message=f"Unknown field: {key}",
            )

    values: dict[str, Any] = {}
    for field in dataclasses.fields(request_type):
        field_type = field_types.get(field.name, field.type)
        if field.name in data:
            value_result = _coerce_value(data[field.name], field_type, field_name=field.name)
            if isinstance(value_result, MachineCommandError):
                return value_result
            values[field.name] = value_result
            continue

        if field.default is not MISSING:
            values[field.name] = field.default
            continue

        if field.default_factory is not MISSING:
            values[field.name] = field.default_factory()
            continue

        if _allows_none(field_type):
            values[field.name] = None
            continue

        return MachineCommandError(
            error_type="invalid_json_input",
            message=f"Missing required field: {field.name}",
        )

    return request_type(**values)


def _coerce_value(
    value: Any,
    type_hint: Any,
    *,
    field_name: str,
) -> Any | MachineCommandError:
    if type_hint is Any:
        return value

    origin = get_origin(type_hint)
    args = get_args(type_hint)

    if origin is Literal:
        if value not in args:
            return MachineCommandError(
                error_type="invalid_json_input",
                message=f"Invalid value for {field_name}: {value!r}",
            )
        return value

    if origin in (list, tuple):
        item_type = args[0] if args else Any
        if not isinstance(value, list):
            return MachineCommandError(
                error_type="invalid_json_input",
                message=f"Field {field_name} must be an array",
            )
        items: list[Any] = []
        for item in value:
            item_result = _coerce_value(item, item_type, field_name=field_name)
            if isinstance(item_result, MachineCommandError):
                return item_result
            items.append(item_result)
        if origin is tuple:
            return tuple(items)
        return items

    if origin is dict:
        if not isinstance(value, dict):
            return MachineCommandError(
                error_type="invalid_json_input",
                message=f"Field {field_name} must be an object",
            )
        return value

    if _is_union_type(type_hint):
        if value is None and type(None) in args:
            return None
        for subtype in args:
            if subtype is type(None):
                continue
            subtype_result = _coerce_value(value, subtype, field_name=field_name)
            if not isinstance(subtype_result, MachineCommandError):
                return subtype_result
        return MachineCommandError(
            error_type="invalid_json_input",
            message=f"Invalid value for {field_name}: {value!r}",
        )

    if type_hint is bool:
        if isinstance(value, bool):
            return value
        return MachineCommandError(
            error_type="invalid_json_input",
            message=f"Field {field_name} must be a boolean",
        )

    if type_hint is int:
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        return MachineCommandError(
            error_type="invalid_json_input",
            message=f"Field {field_name} must be an integer",
        )

    if type_hint is float:
        if isinstance(value, int) and not isinstance(value, bool):
            return float(value)
        if isinstance(value, float):
            return value
        return MachineCommandError(
            error_type="invalid_json_input",
            message=f"Field {field_name} must be a number",
        )

    if type_hint is str:
        if isinstance(value, str):
            return value
        return MachineCommandError(
            error_type="invalid_json_input",
            message=f"Field {field_name} must be a string",
        )

    return value


def _allows_none(type_hint: Any) -> bool:
    if _is_union_type(type_hint):
        return type(None) in get_args(type_hint)
    return False


def _is_union_type(type_hint: Any) -> bool:
    origin = get_origin(type_hint)
    return origin in (types.UnionType, Union)


def _dataclass_field_types(cls: type) -> dict[str, Any]:
    return get_type_hints(cls, include_extras=True)


def _click_exception_error_type(exc: click.ClickException) -> str:
    if not hasattr(exc, "error_type"):
        return "cli_error"

    error_type = exc.error_type
    if isinstance(error_type, str):
        return error_type
    return "cli_error"


def _serialize_machine_result(result: Any) -> dict[str, Any]:
    if hasattr(result, "to_json_dict"):
        data = result.to_json_dict()
    elif dataclasses.is_dataclass(result) and not isinstance(result, type):
        data = dataclasses.asdict(result)
    elif result is None:
        data = {}
    else:
        type_name = type(result).__name__
        raise TypeError(f"Cannot serialize {type_name}: no to_json_dict() and not a dataclass")

    data["success"] = True
    return data
