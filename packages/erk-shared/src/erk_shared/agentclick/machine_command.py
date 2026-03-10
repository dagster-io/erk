"""Machine command decorator for agent-optimized JSON-in/JSON-out CLI commands.

Machine commands are always JSON-in (stdin) / JSON-out (stdout). They have no
human-facing Click options — the input schema is derived from a request dataclass,
not from Click parameters.

Usage:

    @machine_command(
        request_type=MyRequest,
        result_types=(MyResult,),
        name="my_tool",
        description="Does something useful",
    )
    @click.command("my-tool")
    @click.pass_obj
    def my_tool(ctx: ErkContext, *, request: MyRequest) -> MyResult:
        ...
"""

import dataclasses
import json
from dataclasses import dataclass
from typing import Any

import click

from erk_shared.agentclick.errors import AgentCliError


@dataclass(frozen=True)
class MachineCommandMeta:
    """Metadata stored on Command objects decorated with @machine_command."""

    request_type: type
    result_types: tuple[type, ...]
    name: str
    description: str


def machine_command(
    *,
    request_type: type,
    result_types: tuple[type, ...],
    name: str,
    description: str,
) -> Any:
    """Mark a Click command as a machine (JSON-in/JSON-out) command.

    Must be applied ABOVE @click.command in the decorator stack.

    The decorated command receives a ``request`` keyword argument containing
    the deserialized request dataclass. The command returns a result dataclass
    (or None). The decorator handles JSON serialization of the result and
    error envelopes.

    Adds a ``--schema`` flag that short-circuits to emit the schema document.

    Args:
        request_type: Frozen dataclass type for the request
        result_types: Tuple of result dataclass types for schema generation
        name: MCP tool name
        description: MCP tool description
    """

    def decorator(cmd: click.Command) -> click.Command:
        return _apply_machine_command(cmd, request_type, result_types, name, description)

    return decorator


def _apply_machine_command(
    cmd: click.Command,
    request_type: type,
    result_types: tuple[type, ...],
    name: str,
    description: str,
) -> click.Command:
    """Apply machine_command behavior to a Click command."""
    meta = MachineCommandMeta(
        request_type=request_type,
        result_types=result_types,
        name=name,
        description=description,
    )
    cmd._machine_command_meta = meta  # type: ignore[attr-defined]

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

            schema_doc = build_machine_schema_document(meta)
            click.echo(json.dumps(schema_doc, indent=2))
            return None

        # Read JSON from stdin
        request_data = _read_stdin_request()

        # Deserialize to request dataclass
        try:
            request = _deserialize_request(request_type, request_data)
        except (TypeError, KeyError) as exc:
            _emit_error("invalid_request", f"Failed to deserialize request: {exc}")
            raise SystemExit(1) from None

        # Inject request into kwargs, remove schema_mode
        kwargs["request"] = request

        try:
            result = original_callback(**kwargs)
            if result is not None:
                _emit_result(result)
            return result
        except AgentCliError as exc:
            _emit_error(exc.error_type, exc.format_message())
            raise SystemExit(1) from None
        except click.ClickException as exc:
            error_type = getattr(exc, "error_type", "cli_error")
            _emit_error(error_type, exc.format_message())
            raise SystemExit(1) from None
        except SystemExit:
            raise

    wrapped_callback.__name__ = getattr(original_callback, "__name__", "wrapped")
    wrapped_callback.__doc__ = getattr(original_callback, "__doc__", None)
    cmd.callback = wrapped_callback

    return cmd


def _read_stdin_request() -> dict[str, Any]:
    """Read JSON request from stdin. Returns empty dict if stdin is a TTY or empty."""
    stdin = click.get_text_stream("stdin")
    if stdin.isatty():
        return {}
    raw = stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        _emit_error("invalid_json", f"Invalid JSON: {exc}")
        raise SystemExit(1) from None
    if not isinstance(data, dict):
        _emit_error("invalid_json", "JSON input must be an object")
        raise SystemExit(1) from None
    return data


def _deserialize_request(request_type: type, data: dict[str, Any]) -> Any:
    """Deserialize a dict into a request dataclass.

    Only passes keys that match dataclass field names, so extra keys are ignored.
    Missing fields with no default will raise TypeError from the dataclass constructor.
    """
    field_names = {f.name for f in dataclasses.fields(request_type)}
    filtered = {k: v for k, v in data.items() if k in field_names}
    return request_type(**filtered)


def _emit_result(result: Any) -> None:
    """Emit a structured result as JSON with success=True."""
    if hasattr(result, "to_json_dict"):
        data = result.to_json_dict()
    elif dataclasses.is_dataclass(result) and not isinstance(result, type):
        data = dataclasses.asdict(result)
    else:
        type_name = type(result).__name__
        raise TypeError(f"Cannot serialize {type_name}: no to_json_dict() and not a dataclass")
    data["success"] = True
    click.echo(json.dumps(data, indent=2))


def _emit_error(error_type: str, message: str) -> None:
    """Emit a JSON error envelope."""
    error_data = {
        "success": False,
        "error_type": error_type,
        "message": message,
    }
    click.echo(json.dumps(error_data, indent=2))
