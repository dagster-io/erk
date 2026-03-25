---
title: JSON/Dataclass Utilities in erk-shared
read_when:
  - "adding a new exec script with JSON output"
  - "working with @json_command or @machine_command decorators"
  - "implementing JSON deserialization for dataclasses"
  - "generating JSON schemas from dataclass fields"
tripwires:
  - action: "writing manual JSON serialization/deserialization for exec scripts"
    warning: "Use @json_command or the utilities in erk_shared.agentclick.dataclass_json instead. They handle schema generation, type coercion, and error formatting automatically."
---

# JSON/Dataclass Utilities in erk-shared

`erk_shared.agentclick.dataclass_json` provides consolidated utilities for JSON ↔ frozen-dataclass conversion used by exec scripts.

## Source

`packages/erk-shared/src/erk_shared/agentclick/dataclass_json.py`

## Core Functions

### Deserialization

**`parse_dataclass_from_json(cls, data)`** — Parse a JSON dict into a frozen dataclass:

- Checks for `from_json_dict()` classmethod first (custom deserialization)
- Falls back to generic construction with strict validation:
  - Rejects unknown keys
  - Applies type coercion via `coerce_json_value()`
  - Raises `ValueError` for missing required fields

**`coerce_json_value(value, target_type)`** — Type coercion with full support for:

- `Literal` (validates against allowed values)
- `tuple[X, ...]` and `list[X]` (recursive coercion)
- `X | None` unions
- `bool`, `int`, `float`, `str` (with bool-before-int safety)

### Serialization

**`serialize_to_json_dict(result)`** — Dataclass → JSON dict:

- Checks for `to_json_dict()` protocol first (custom serialization)
- Falls back to `dataclasses.asdict()` for plain dataclasses

### Schema Generation

**`dataclass_result_schema(cls)`** — Auto-generate JSON Schema from dataclass fields:

- Maps Python types to JSON Schema types via `python_type_to_json_schema()`
- Always includes `success: true` (output schema convention)

**`python_type_to_json_schema(type_hint)`** — Python type → JSON Schema:

- Handles `Literal`, `tuple[X,...]`, `list[X]`, `dict`, `X | None`, primitives

### I/O Helpers

**`read_json_stdin()`** — Read JSON from stdin (returns `None` if TTY or empty)

**`emit_json_success(data)`** — Print success JSON to stdout (adds `success: True`)

**`emit_json_error(error_type, message)`** — Print error JSON to stdout

## Usage via @json_command

Most exec scripts use the `@json_command` decorator which orchestrates these utilities:

```python
from erk_shared.agentclick.json_command import json_command

@json_command(output_types=(MyResultType,))
@click.option("--pr-number", required=True, type=int)
def my_exec_script(*, pr_number: int) -> MyResultType | ErrorResult:
    ...
```

The decorator handles JSON input parsing, output serialization, schema generation, and error formatting automatically.

## Error Schema

All commands that use these utilities share the same error envelope:

```json
{
  "success": false,
  "error_type": "string",
  "message": "string"
}
```

## Related Documentation

- [Exec Script Testing Patterns](exec-script-testing.md) — Testing exec scripts
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) — Error return patterns
