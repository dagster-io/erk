# Agent-DX Framework: Output Envelope Helpers + Describe Command + First Port

**Objective:** #8760 — Agent-DX for Erk Exec Commands
**Nodes:** 1.1 (output envelope helpers), 1.2 (describe command), 1.3 (port get-pr-feedback)

## Context

Erk's `exec` command group (~89 scripts) is consumed almost exclusively by AI agents (skills, hooks, CI). The output patterns are inconsistent: ~75 scripts exit 1 on error (with JSON), while `script_output.exit_with_error()` correctly exits 0. There's no runtime schema introspection. This PR establishes the framework conventions and proves them on one representative script.

## Plan

### Step 1: Extend `script_output.py` with envelope helpers (Node 1.1)

**File:** `src/erk/cli/script_output.py`

Add three helpers alongside the existing `exit_with_error` and `handle_non_ideal_exit`:

```python
def success_json(data: dict[str, Any], **kwargs: Any) -> NoReturn:
    """Output JSON success envelope and exit 0."""
    click.echo(json.dumps({"success": True, **data, **kwargs}))
    raise SystemExit(0)

def error_json(error_type: str, message: str, **details: Any) -> NoReturn:
    """Output JSON error envelope and exit 0. Replaces ad-hoc patterns."""
    click.echo(json.dumps({"success": False, "error_type": error_type, "message": message, **details}))
    raise SystemExit(0)

def dry_run_json(action: str, **details: Any) -> NoReturn:
    """Output JSON dry-run envelope and exit 0."""
    click.echo(json.dumps({"success": True, "dry_run": True, "action": action, **details}))
    raise SystemExit(0)
```

**Design notes:**
- `error_json` is functionally identical to existing `exit_with_error` but with a name matching the new convention. Keep `exit_with_error` as-is (backwards compat for existing callers) — Phase 2 will migrate callers
- All three exit 0 (the core agent-DX principle)
- `**kwargs`/`**details` allows command-specific fields without a proliferation of TypedDicts
- No indent by default (single-line JSON is more machine-friendly and saves context window tokens)

### Step 2: Add `erk exec describe` command (Node 1.2)

**New file:** `src/erk/cli/commands/exec/scripts/describe.py`

Uses Click introspection to emit parameter schema as JSON. Implementation:

```python
@click.command(name="describe")
@click.argument("command_name")
@click.pass_context
def describe(ctx: click.Context, command_name: str) -> None:
    """Describe an exec command's parameters as JSON schema."""
    # Walk up to the exec group and look up the command
    exec_group = ctx.parent.command  # The exec Click.Group
    cmd = exec_group.get_command(ctx, command_name)
    if cmd is None:
        error_json("command-not-found", f"No exec command named '{command_name}'")

    params = []
    for param in cmd.params:
        param_info = {
            "name": param.name,
            "type": _click_type_to_str(param.type),
            "required": param.required,
            "is_flag": isinstance(param, click.Option) and param.is_flag,
        }
        if isinstance(param, click.Option):
            param_info["opts"] = param.opts  # e.g. ["--pr", "-p"]
        if isinstance(param, click.Argument):
            param_info["kind"] = "argument"
        else:
            param_info["kind"] = "option"
        if param.help:
            param_info["help"] = param.help
        if param.default is not None:
            param_info["default"] = param.default
        if isinstance(param.type, click.Choice):
            param_info["choices"] = list(param.type.choices)
        params.append(param_info)

    success_json({
        "command": command_name,
        "help": cmd.get_short_help_str(),
        "params": params,
    })
```

Helper `_click_type_to_str` maps Click types to JSON-friendly strings: `click.INT` → `"int"`, `click.STRING` → `"string"`, `click.BOOL` → `"bool"`, `click.Path` → `"path"`, `click.Choice` → `"choice"`, etc.

**Register in group.py:** `exec_group.add_command(describe, name="describe")`

### Step 3: Port `get-pr-feedback` (Node 1.3)

**File:** `src/erk/cli/commands/exec/scripts/get_pr_feedback.py`

Current state: Already uses `exit_with_error` and `handle_non_ideal_exit`. Output is JSON with `"success": True`. The main change is the explicit `raise SystemExit(0)` → use `success_json()` instead.

Changes:
1. Replace `click.echo(json.dumps(result, indent=2)); raise SystemExit(0)` with `success_json(result_without_success_key)`
2. The script already uses `exit_with_error` for error cases — these already conform (exit 0 with JSON error)
3. Update the docstring Exit Codes section: `0: Always (success or error communicated via JSON)`

This is a minimal port — the script is already close to conforming. The main value is proving the `success_json` helper works end-to-end.

### Step 4: Tests

**New file:** `tests/unit/cli/commands/exec/scripts/test_describe.py`

Tests for describe command:
- `test_describe_existing_command`: describe get-pr-feedback → returns params with correct types
- `test_describe_nonexistent_command`: describe bogus → returns error JSON
- `test_describe_shows_choices`: describe a command with Choice params → choices in output
- `test_describe_shows_flags`: describe a command with is_flag → is_flag: true

**New file:** `tests/unit/cli/test_script_output.py`

Tests for new helpers:
- `test_success_json_outputs_envelope`: verify JSON structure and exit 0
- `test_error_json_outputs_envelope`: verify error structure and exit 0
- `test_dry_run_json_outputs_envelope`: verify dry_run structure and exit 0

**Existing file:** `tests/unit/cli/commands/exec/scripts/test_get_pr_feedback.py`

Existing tests should pass unchanged since the output structure doesn't change (`success_json` produces the same envelope). Verify no regressions.

## Files to Modify

| File | Action |
|------|--------|
| `src/erk/cli/script_output.py` | Add `success_json`, `error_json`, `dry_run_json` |
| `src/erk/cli/commands/exec/scripts/describe.py` | **New** — describe command |
| `src/erk/cli/commands/exec/group.py` | Register describe command |
| `src/erk/cli/commands/exec/scripts/get_pr_feedback.py` | Use `success_json`, update docstring |
| `tests/unit/cli/test_script_output.py` | **New** — tests for envelope helpers |
| `tests/unit/cli/commands/exec/scripts/test_describe.py` | **New** — tests for describe |

## Verification

1. Run `pytest tests/unit/cli/test_script_output.py` — new helper tests pass
2. Run `pytest tests/unit/cli/commands/exec/scripts/test_describe.py` — describe tests pass
3. Run `pytest tests/unit/cli/commands/exec/scripts/test_get_pr_feedback.py` — existing tests pass (no regression)
4. Manual: `erk exec describe get-pr-feedback` outputs JSON schema
5. Run `make fast-ci` — full unit test suite passes
