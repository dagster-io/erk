---
title: "Machine Command Architecture"
read_when:
  - "adding @machine_command decorator to a CLI command"
  - "creating structured JSON CLI output"
  - "understanding the erk json command tree"
  - "implementing output_types validation"
  - "working with MachineCommandError error handling"
  - "adding @json_command decorator to a CLI command"
tripwires:
  - action: "applying @machine_command below @click.command in the decorator stack"
    warning: "@machine_command must be applied ABOVE @click.command. The correct order is @mcp_exposed > @machine_command > @click.command."
  - action: "adding --json flag to a human-facing command"
    warning: "Machine JSON output lives in the `erk json` command tree, not as a flag on human commands. Create a json_cli.py machine adapter in the command's subpackage."
  - action: "putting business logic in the machine adapter"
    warning: "Machine adapters should be thin wrappers. Put shared logic in *_operation.py files."
  - action: "returning MachineCommandError without raising SystemExit"
    warning: "The @machine_command decorator handles serialization and exit codes. Just return MachineCommandError from the callback."
---

# Machine Command Architecture

The `erk json` command tree provides machine-readable JSON commands for agent consumption. Human-facing commands live separately with rich terminal output.

## Architecture Overview

```
src/erk/cli/commands/
├── one_shot/
│   ├── __init__.py
│   ├── cli.py               # Human command (Click options, rich output)
│   ├── operation.py          # Shared operation (transport-independent)
│   └── json_cli.py           # Machine adapter (@machine_command)
└── pr/
    ├── list/
    │   ├── __init__.py
    │   ├── cli.py            # Human command
    │   ├── operation.py      # Shared operation
    │   └── json_cli.py       # Machine adapter
    └── view/
        ├── __init__.py
        ├── cli.py            # Human command
        ├── operation.py      # Shared operation
        └── json_cli.py       # Machine adapter
```

The pattern is:

1. **Operation file** (`*_operation.py`): Contains `Request` dataclass, `Result` dataclass, and `run_*()` function
2. **Human command**: Click options, rich output, delegates to operation
3. **Machine adapter** (`json_cli.py`): `@machine_command` + `@mcp_exposed`, thin wrapper around operation

## @machine_command Decorator

**Source**: `packages/erk-shared/src/erk_shared/agentclick/machine_command.py`

<!-- Source: src/erk/cli/commands/one_shot/json_cli.py, json_one_shot -->

See `json_one_shot()` in `src/erk/cli/commands/one_shot/json_cli.py` for the canonical example. The decorator stack is `@mcp_exposed` > `@machine_command` > `@click.command` > `@click.pass_obj`, and the callback receives a typed `request` keyword argument.

### Decorator Parameters

| Parameter      | Type               | Purpose                                 |
| -------------- | ------------------ | --------------------------------------- |
| `request_type` | `type`             | Frozen dataclass for input validation   |
| `output_types` | `tuple[type, ...]` | Result types for JSON Schema generation |

### What it does

- Adds `--schema` flag for introspection
- Reads JSON from stdin, validates against `request_type` dataclass
- Passes constructed request as `request` keyword argument to callback
- Serializes return value (or `MachineCommandError`) as JSON to stdout
- Handles `ClickException` with `error_type` attribute

### Decorator Stack Order

```
@mcp_exposed(...)      # MCP exposure (optional, outermost)
@machine_command(...)   # Machine command infrastructure
@click.command(...)     # Click command
@click.pass_obj         # Context passing (innermost)
```

## Request Types

Frozen dataclasses with strict validation:

<!-- Source: src/erk/cli/commands/one_shot/operation.py, OneShotRequest -->

See `OneShotRequest` in `src/erk/cli/commands/one_shot/operation.py` for the canonical example (8 fields: `prompt`, `model`, `dry_run`, `plan_only`, `slug`, `dispatch_ref`, `ref_current`, `target_repo`).

- Fields without defaults are required in JSON input
- Unknown fields are rejected
- Type coercion is applied (bool, int, str, X | None unions)

## Result Types

Result dataclasses implement `to_json_dict()` for custom serialization:

<!-- Source: src/erk/cli/commands/one_shot_remote_dispatch.py, OneShotDispatchResult -->

See `OneShotDispatchResult` in `src/erk/cli/commands/one_shot_remote_dispatch.py` for the canonical example — a frozen dataclass with a `to_json_dict()` method that controls which fields appear in JSON output and how they're serialized.

Falls back to `dataclasses.asdict()` if no `to_json_dict()` is defined.

## Error Handling

`MachineCommandError` is a frozen dataclass (not an exception):

<!-- Source: packages/erk-shared/src/erk_shared/agentclick/machine_command.py, MachineCommandError -->

See `MachineCommandError` in `packages/erk-shared/src/erk_shared/agentclick/machine_command.py`. It is a frozen dataclass with `error_type: str` and `message: str` fields.

Return it from the operation function — the decorator handles serialization:

```json
{
  "success": false,
  "error_type": "invalid_input",
  "message": "Prompt must not be empty"
}
```

## Schema Output

`--schema` returns a document with input, output, and error schemas:

```json
{
  "input_schema": { ... },
  "output_schema": { ... },
  "error_schema": { ... }
}
```

**Source**: `packages/erk-shared/src/erk_shared/agentclick/machine_schema.py`

## Testing Machine Commands

Mock `read_machine_command_input` to inject JSON input:

```python
with patch(
    "erk_shared.agentclick.machine_command.read_machine_command_input",
    return_value={"prompt": "fix bug"},
):
    result = runner.invoke(cli, ["json", "one-shot"], obj=ctx)
data = json.loads(result.output)
assert data["success"] is True
```

## Legacy @json_command

The `@json_command` decorator in `json_command.py` is deprecated. It added `--json`/`--schema` flags to human commands. New commands should use the `@machine_command` pattern with a separate command in the `erk json` tree.

**Source**: `packages/erk-shared/src/erk_shared/agentclick/json_command.py` (deprecated)
