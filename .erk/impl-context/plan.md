# Fix: erk-mcp one_shot fails on detached HEAD (#9250)

## Context

`erk json one-shot` emits raw Click usage errors instead of structured JSON when `resolve_dispatch_ref()` raises `click.UsageError` (detached HEAD + `ref_current=true`, or conflicting `dispatch_ref` + `ref_current`).

**Root cause**: `resolve_dispatch_ref()` raises `click.UsageError` (no `error_type` attr). The `machine_command` wrapper catches `click.ClickException` but only converts to `MachineCommandError` if it has an `error_type` attribute (line 194-203 of `machine_command.py`). Plain `click.UsageError` lacks this, so it gets re-raised as raw Click error text.

## TDD Plan

### Step 1: Write failing tests

Add two tests to `tests/commands/one_shot/test_one_shot_json.py`, following the existing pattern in that file:

**`test_json_error_detached_head_ref_current`**
- `FakeGit` with NO `current_branches` entry (detached HEAD)
- Machine input: `{"prompt": "fix bug", "ref_current": true}`
- Assert: exit 1, JSON `success: false`, `error_type: "cli_error"`, message matches "detached HEAD"

**`test_json_error_conflicting_ref_flags`**
- Machine input: `{"prompt": "fix bug", "dispatch_ref": "some-branch", "ref_current": true}`
- Assert: exit 1, JSON `success: false`, `error_type: "cli_error"`, message matches "mutually exclusive"

### Step 2: Implement fix

In `src/erk/cli/commands/one_shot/operation.py` (lines 110-113), wrap the `resolve_dispatch_ref()` call:

```python
# Before (raises click.UsageError through to caller):
ref = resolve_dispatch_ref(
    ctx, dispatch_ref=request.dispatch_ref, ref_current=request.ref_current
)

# After (catches and converts to MachineCommandError):
try:
    ref = resolve_dispatch_ref(
        ctx, dispatch_ref=request.dispatch_ref, ref_current=request.ref_current
    )
except click.UsageError as exc:
    return MachineCommandError(error_type="cli_error", message=str(exc))
```

Add `import click` to the imports.

Both consumers handle `MachineCommandError` returns correctly:
- **Machine path** (`json_cli.py`): `machine_command` wrapper emits JSON error at line 188-190
- **Human path** (`cli.py`): Already handles at line 144-146 with styled error output

### Step 3: Run tests

```bash
uv run pytest tests/commands/one_shot/test_one_shot_json.py -v
uv run pytest tests/commands/one_shot/test_one_shot.py -v
```

## Files to modify

1. `tests/commands/one_shot/test_one_shot_json.py` — add 2 tests (write FIRST)
2. `src/erk/cli/commands/one_shot/operation.py` — catch `click.UsageError`, add `import click`
