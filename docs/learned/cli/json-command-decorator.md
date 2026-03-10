---
title: "@json_command Decorator"
read_when:
  - "adding @json_command decorator to a CLI command"
  - "creating structured JSON CLI output"
  - "understanding emit_json patterns"
  - "implementing output_types validation"
  - "working with AgentCliError error handling"
tripwires:
  - action: "applying @json_command below @click.command in the decorator stack"
    warning: "@json_command must be applied ABOVE @click.command. The correct order is @mcp_exposed > @json_command > @click.command."
  - action: "using json.dumps without indent=2 in a @json_command context"
    warning: "All json.dumps() calls in @json_command commands use indent=2 for pretty-printing."
  - action: "raising an exception in a @json_command without using AgentCliError"
    warning: "Use AgentCliError(message, error_type=...) to ensure errors serialize as JSON when --json is active."
  - action: "declaring output_types that don't match the return annotation"
    warning: "test_output_types_matches_return_annotation() validates output_types against return type hints. Mismatches fail CI."
---

# @json_command Decorator

Universal CLI JSON infrastructure for agent-optimized command output.

**Source**: `packages/erk-shared/src/erk_shared/agentclick/json_command.py`

## Decorator Parameters

```python
@json_command(
    exclude_json_input=frozenset({"repo_id"}),
    required_json_input=frozenset({"prompt"}),
    output_types=(PrListResult, PrViewResult),
)
```

| Parameter             | Type               | Purpose                                                    |
| --------------------- | ------------------ | ---------------------------------------------------------- |
| `exclude_json_input`  | `frozenset[str]`   | Parameter names to skip when mapping JSON stdin input      |
| `required_json_input` | `frozenset[str]`   | Parameters that must be present and non-None in JSON input |
| `output_types`        | `tuple[type, ...]` | Result types for JSON Schema generation via `--schema`     |

Two usage forms:

- **Bare**: `@json_command` (no configuration needed)
- **Parameterized**: `@json_command(exclude_json_input=..., output_types=...)`

## CLI Flags Added

The decorator adds two flags to the command:

- `--json` — Output structured JSON instead of human-readable text
- `--schema` — Output JSON Schema for the command's result types

## emit_json() and emit_json_result()

Two helpers for producing JSON output:

- `emit_json(dict)` — for ad-hoc dict output; automatically adds `success: True`
- `emit_json_result(result)` — for result dataclass output; calls `to_json_dict()` or falls back to `dataclasses.asdict()`

See `packages/erk-shared/src/erk_shared/agentclick/json_command.py` for current signatures.

**`emit_json_result()` protocol**:

1. Calls `result.to_json_dict()` if method exists
2. Falls back to `dataclasses.asdict()` for plain dataclasses
3. Raises `TypeError` if neither is available

## Error Handling

`AgentCliError` extends `click.ClickException` with an `error_type` parameter. See `packages/erk-shared/src/erk_shared/agentclick/errors.py` for the current class definition.

Import: `from erk_shared.agentclick.errors import AgentCliError`

When `--json` is active, `AgentCliError` serializes as:

```json
{ "success": false, "error_type": "invalid_plan", "message": "Plan not found" }
```

Three error categories:

- **Validation errors**: `error_type: "invalid_json_input"` (bad stdin JSON)
- **Command errors**: Custom `error_type` from `AgentCliError`
- **Passthrough**: `SystemExit` and non-Click exceptions pass through unchanged

## JSON Input Validation

When `--json` is active, the decorator reads from stdin (if piped):

1. Input must be a JSON object (dict), not array
2. All keys must match command parameters and not be in `exclude_json_input`
3. Required fields (from `required_json_input`) must be present and non-None

## output_types Validation

A CI test (`test_output_types_matches_return_annotation()`) enforces consistency:

- Walks the entire CLI tree collecting `@json_command` decorated commands
- Compares declared `output_types` against function return type annotations
- `type(None)` in unions is stripped (represents inline emission or no return)
- Mismatches fail the test with descriptive error messages

**Source**: `tests/unit/cli/test_json_command.py`

## Testing @json_command Commands

Use `CliRunner` with JSON assertions:

```python
result = runner.invoke(my_command, ["--json"])
data = json.loads(result.output)
assert data["success"] is True
```

## Metadata Storage

The decorator stores `JsonCommandMeta` (frozen dataclass) on the Command object and preserves the original callback as `cmd._json_command_original_callback` for schema introspection.
