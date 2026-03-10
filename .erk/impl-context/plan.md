# Decouple JSON Input and Output in agentclick

## Context

Currently `--json` is a single toggle that controls both JSON output serialization AND JSON input from stdin. This couples two independent concerns — a command that wants JSON output must also accept stdin JSON, and vice versa. We want to vary them independently:

- `--json` → JSON **output** only (error serialization, `emit_json`, auto-return-value serialization)
- `--stdin-json` → JSON **input** from stdin (read JSON object, map keys to kwargs, validate)
- Either, both, or neither can be used

## Renames

- `json_mode` → `json_stdout` everywhere (param name, kwarg, internal references)
- New param: `stdin_json`

## Files to Modify

1. **`packages/erk-shared/src/erk_shared/agentclick/json_command.py`** — Core changes
2. **`packages/erk-shared/src/erk_shared/agentclick/json_schema.py`** — Update `_INTERNAL_PARAMS` (`json_mode` → `json_stdout`, add `stdin_json`)
3. **`packages/erk-shared/tests/unit/agentclick/test_json_command.py`** — Update tests
4. **`packages/erk-shared/tests/unit/agentclick/test_json_schema.py`** — Verify both internal params excluded from schema
5. **All `@json_command` consumers** — Rename `json_mode` → `json_stdout` in function signatures

## Implementation

### Step 1: Rename `json_mode` → `json_stdout` in `json_command.py`

Update the `--json` option to use `json_stdout` as the param name:

```python
json_option = click.Option(
    ["--json", "json_stdout"],
    is_flag=True,
    help="Output results as JSON",
)
```

Update all internal references: `kwargs["json_mode"]` → `kwargs["json_stdout"]`, etc.

### Step 2: Add `--stdin-json` flag in `json_command.py`

In `_apply_json_command`, add a new Click option:

```python
stdin_json_option = click.Option(
    ["--stdin-json", "stdin_json"],
    is_flag=True,
    help="Read input parameters as JSON from stdin",
)
cmd.params.append(stdin_json_option)
```

### Step 3: Split the wrapped callback logic

Current flow: `--json` → read stdin + JSON output + JSON error handling.

New flow:
- `--stdin-json` → read stdin JSON, map to kwargs, validate keys/required fields
- `--json` → JSON output mode (error serialization, auto-return-value serialization)
- Stdin validation errors: use JSON format if `--json` is active, otherwise raise `click.UsageError`

In `wrapped_callback`:
```python
stdin_json = kwargs.pop("stdin_json", False)
json_stdout = kwargs.pop("json_stdout", False)
kwargs["json_stdout"] = json_stdout

# JSON input: read from stdin when --stdin-json is passed
if stdin_json:
    # ... existing stdin reading/validation logic, but triggered by stdin_json
    # Error output format depends on json_stdout

# Command execution: error handling depends on json_stdout (unchanged)
if not json_stdout:
    return original_callback(**kwargs)
# ... existing JSON error handling ...
```

### Step 4: Update `_INTERNAL_PARAMS` in `json_schema.py`

```python
_INTERNAL_PARAMS = frozenset({"json_stdout", "schema_mode", "stdin_json", "ctx"})
```

### Step 5: Update `skip_keys` in validation

Currently: `skip_keys = exclude_json_input | {"json_mode"}`
New: `skip_keys = exclude_json_input | {"json_stdout", "stdin_json"}`

### Step 6: Rename `json_mode` → `json_stdout` in all consumers

Every command with `@json_command` has `json_mode: bool` in its signature. Rename to `json_stdout: bool`. This is a mechanical rename across all consumer files.

### Step 7: Update tests

- **Rename**: `json_mode` → `json_stdout` in all test command signatures
- **Existing JSON input tests**: Add `--stdin-json` flag to invocations that test stdin behavior
- **New test**: `--json` without `--stdin-json` does NOT read stdin
- **New test**: `--stdin-json` without `--json` reads stdin but outputs human format
- **New test**: `--stdin-json --json` together works (both input and output)
- **Schema test**: Verify `stdin_json` and `json_stdout` not in schema output

### Step 8: Update real command callers (if needed)

Callers that currently pass `--json` and pipe stdin will need to add `--stdin-json`. This is a breaking change but acceptable per project constraints ("no backwards compatibility").

## Verification

1. Run unit tests: `pytest packages/erk-shared/tests/unit/agentclick/`
2. Run full test suite to catch any integration breakage
3. Verify `--schema` output excludes both `json_stdout` and `stdin_json` params
