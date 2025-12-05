# Plan: Create `touch-scratch-marker` Kit CLI Command

## Overview

Push down scratch directory creation and marker file operations from raw bash instructions to a proper kit CLI command, following the predicate push-down pattern.

## Current State

`exit_plan_mode_hook.py` lines 173-176 output raw bash commands for agents to execute:
```bash
mkdir -p .erk/scratch/{session_id} && touch .erk/scratch/{session_id}/skip-plan-save
```

The hook also has duplicate `_get_scratch_dir()` logic (lines 55-74) that duplicates `erk_shared.scratch.get_scratch_dir()`.

## Implementation Steps

### Step 1: Create the kit CLI command

**File:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/touch_scratch_marker.py`

```python
@click.command(name="touch-scratch-marker")
@click.option("--session-id", required=True, help="Claude session ID")
@click.option("--marker", default=None, help="Marker filename to create (optional)")
def touch_scratch_marker(session_id: str, marker: str | None) -> None:
    """Create scratch directory and optional marker file.

    Creates .erk/scratch/<session-id>/ directory (idempotent) and optionally
    creates a marker file within it.

    Output: JSON with scratch_dir path and optional marker_path.
    """
```

Key behaviors:
- Uses `erk_shared.scratch.get_scratch_dir(session_id)` for directory creation
- If `--marker` provided, creates empty marker file
- Returns JSON: `{"scratch_dir": "...", "marker_path": "..." or null}`
- Exit 0 on success, exit 1 with JSON error on failure

### Step 2: Register command in kit.yaml

**File:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit.yaml`

Add to `kit_cli_commands` list:
```yaml
  - name: touch-scratch-marker
    path: kit_cli_commands/erk/touch_scratch_marker.py
    description: Create scratch directory and optional marker file for session
```

### Step 3: Update exit_plan_mode_hook.py instructions

**File:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/exit_plan_mode_hook.py`

Update `_output_blocking_message()` (lines 170-177) to output:
```
dot-agent kit-command erk touch-scratch-marker --session-id {session_id} --marker skip-plan-save
```

Instead of:
```
mkdir -p .erk/scratch/{session_id} && touch .erk/scratch/{session_id}/skip-plan-save
```

### Step 4: Create unit test

**File:** `packages/dot-agent-kit/tests/unit/kit_cli_commands/erk/test_touch_scratch_marker.py`

Test cases:
- Creates scratch directory when it doesn't exist
- Creates marker file when `--marker` specified
- Returns correct JSON output
- Works when directory already exists (idempotent)
- Fails gracefully when not in git repo

## Files to Modify

1. **Create:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/touch_scratch_marker.py`
2. **Edit:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit.yaml`
3. **Edit:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/exit_plan_mode_hook.py`
4. **Create:** `packages/dot-agent-kit/tests/unit/kit_cli_commands/erk/test_touch_scratch_marker.py`

## Related Skills to Load

- `dignified-python-313` - For Python code patterns
- `fake-driven-testing` - For test structure