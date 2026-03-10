---
title: "@machine_command Decorator"
read_when:
  - "adding @machine_command to a CLI command"
  - "creating stdin/stdout JSON machine commands"
  - "implementing machine command schema output"
  - "working with MachineCommandError"
tripwires:
  - action: "applying @machine_command below @click.command in the decorator stack"
    warning: "@machine_command must wrap the Click command. Correct order: @mcp_exposed > @machine_command > @click.command."
  - action: "adding human options to an @machine_command command"
    warning: "Machine commands take input from stdin JSON only. Keep human flags on the separate human command."
  - action: "raising click.ClickException expecting structured machine output without MachineCommandError"
    warning: "Return MachineCommandError for operation-layer failures. @machine_command only converts ClickException at the transport boundary."
  - action: "declaring output_types that don't match returned result contracts"
    warning: "Keep output_types aligned with the actual request/result contracts so schema generation and MCP stay correct."
---

# @machine_command Decorator

Explicit transport for machine-facing CLI commands.

**Source**: `packages/erk-shared/src/erk_shared/agentclick/machine_command.py`

This decorator is for commands under `erk json ...`, not human commands. It gives the command a strict machine contract:

- input comes from stdin as a JSON object
- output goes to stdout as a structured JSON envelope
- `--schema` returns the machine-readable schema for the command

## Decorator Stack

Use this order, outermost to innermost:

```python
@mcp_exposed(name="pr_list", description="List plans")
@machine_command(
    request_type=PrListRequest,
    output_types=(PrListResult,),
)
@click.command("list")
@click.pass_obj
def json_pr_list(ctx: ErkContext, *, request: PrListRequest) -> PrListResult | MachineCommandError:
    ...
```

## Request Contract

The request type should usually be a frozen dataclass.

```python
@dataclass(frozen=True)
class PrListRequest:
    state: Literal["open", "closed", "all"] = "open"
    labels: tuple[str, ...] = ()
```

The decorator parses stdin JSON into that contract by:

1. calling `from_json_dict()` if the request type provides it
2. otherwise coercing into the dataclass using resolved type hints

Unknown fields and type mismatches become:

```json
{
  "success": false,
  "error_type": "invalid_json_input",
  "message": "..."
}
```

## Result Contract

`output_types` declares the possible success result types for schema generation.

Success output always looks like:

```json
{
  "success": true,
  "...": "result fields"
}
```

Result serialization uses this protocol:

1. call `to_json_dict()` if present
2. otherwise use `dataclasses.asdict()` for dataclass instances
3. raise `TypeError` for unsupported result objects

Use result dataclasses for stable machine output. Add `json_schema()` only when auto-generated schema is not enough.

## Error Handling

Use `MachineCommandError` for operation-layer failures:

```python
return MachineCommandError(
    error_type="auth_required",
    message="GitHub authentication required.",
)
```

The decorator also catches `click.ClickException` and converts it to the same error envelope. This is a boundary convenience, not the main design. Prefer returning `MachineCommandError` from shared operation functions.

## Metadata Stored on the Click Command

The decorator attaches:

- `_machine_command_meta` with request and output type metadata
- `_machine_command_original_callback` for schema/introspection helpers

`packages/erk-shared/src/erk_shared/agentclick/json_schema.py` reads that metadata to produce the machine schema.

## Testing Pattern

Test machine commands through the actual CLI surface:

```python
result = runner.invoke(
    cli,
    ["json", "pr", "list"],
    input=json.dumps({"state": "open"}),
    obj=ctx,
)
```

Assert on the structured envelope, and add a `--schema` test when the contract changes.
