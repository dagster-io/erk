---
title: "Machine and JSON Command Infrastructure"
read_when:
  - "adding @machine_command decorator to a CLI command"
  - "creating structured JSON CLI output"
  - "understanding emit_json patterns"
  - "working with AgentCliError error handling"
  - "creating a machine-readable command under erk json"
tripwires:
  - action: "applying @machine_command below @click.command in the decorator stack"
    warning: "@machine_command must be applied ABOVE @click.command. The correct order is @machine_command > @click.command."
  - action: "using json.dumps without indent=2 in a @machine_command context"
    warning: "All json.dumps() calls in @machine_command commands use indent=2 for pretty-printing."
  - action: "raising an exception in a @machine_command without using AgentCliError"
    warning: "Use AgentCliError(message, error_type=...) to ensure errors serialize as JSON."
  - action: "adding Click options to a @machine_command"
    warning: "Machine commands derive input from a request dataclass, not Click options. Only @click.pass_obj is allowed."
---

# Machine and JSON Command Infrastructure

## Architecture: Three-Layer Pattern

Commands now follow a three-layer architecture:

1. **Core operation** — Pure business logic in `*_operation.py` files. Takes a request dataclass, returns a result dataclass.
2. **Human CLI adapter** — Click command with options, calls core operation, renders human-readable output.
3. **Machine CLI adapter** — `@machine_command` under `erk json ...`, reads JSON from stdin, calls core operation, emits JSON.

## @machine_command Decorator

**Source**: `packages/erk-shared/src/erk_shared/agentclick/machine_command.py`

Machine commands are JSON-in (stdin) / JSON-out (stdout). Input schema is derived from a request dataclass, not Click parameters.

```python
@machine_command(
    request_type=OneShotRequest,
    result_types=(OneShotDispatchResult, OneShotDryRunResult),
    name="one_shot",
    description="Submit a task for autonomous remote execution",
)
@click.command("one-shot")
@click.pass_obj
def json_one_shot(ctx: ErkContext, *, request: OneShotRequest) -> ...:
    return run_one_shot(request, ctx=ctx)
```

### Decorator Parameters

| Parameter      | Type               | Purpose                              |
| -------------- | ------------------ | ------------------------------------ |
| `request_type` | `type`             | Frozen dataclass type for JSON input |
| `result_types` | `tuple[type, ...]` | Result types for schema generation   |
| `name`         | `str`              | MCP tool name                        |
| `description`  | `str`              | MCP tool description                 |

### Behavior

- Reads JSON from stdin via `click.get_text_stream("stdin")`
- Deserializes into request dataclass (extra keys ignored, missing optional fields use defaults)
- Injects as `request` keyword argument
- Serializes result as JSON with `success: True`
- Serializes errors as JSON with `success: False`
- `--schema` flag outputs input/output/error schemas without executing

### Metadata

Stores `MachineCommandMeta` on the command object as `cmd._machine_command_meta`.

## Utility Functions (Legacy)

**Source**: `packages/erk-shared/src/erk_shared/agentclick/json_command.py`

Utility functions still available for ad-hoc use:

- `emit_json(dict)` — outputs dict with `success: True`
- `emit_json_result(result)` — outputs result dataclass as JSON
- `read_stdin_json()` — reads JSON from stdin

## Error Handling

`AgentCliError` extends `click.ClickException` with an `error_type` parameter.

Import: `from erk_shared.agentclick.errors import AgentCliError`

Machine commands serialize errors as:

```json
{ "success": false, "error_type": "invalid_plan", "message": "Plan not found" }
```

Error categories:

- **Validation errors**: `error_type: "invalid_json"` or `"invalid_request"`
- **Command errors**: Custom `error_type` from `AgentCliError`
- **Passthrough**: `SystemExit` passes through unchanged

## Testing @machine_command Commands

Use `CliRunner` with `input` parameter for stdin:

```python
runner = CliRunner()
result = runner.invoke(cmd, [], input='{"prompt": "hello"}')
data = json.loads(result.output)
assert data["success"] is True
```

Schema tests:

```python
result = runner.invoke(cmd, ["--schema"])
doc = json.loads(result.output)
assert "input_schema" in doc
```
