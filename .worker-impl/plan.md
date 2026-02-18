# Add "codespace run objective plan" to objectives menu

## Context

The TUI objectives command palette (accessed via the search/command menu in the Objectives tab) needs a new action item to run `erk codespace run objective plan <issue_number>`. This runs an objective plan remotely on a GitHub Codespace via SSH. The CLI command already exists at `src/erk/cli/commands/codespace/run/objective/plan_cmd.py`.

## Changes

### 1. `src/erk/tui/commands/registry.py`

**Add display name generator** (after `_display_close_objective` ~line 133):

```python
def _display_codespace_run_plan(ctx: CommandContext) -> str:
    """Display name for codespace_run_plan command."""
    return f"erk codespace run objective plan {ctx.row.issue_number}"
```

**Add CommandDefinition** in the OBJECTIVE ACTIONS section (after `close_objective`, ~line 245):

```python
CommandDefinition(
    id="codespace_run_plan",
    name="Codespace Run Plan",
    description="codespace",
    category=CommandCategory.ACTION,
    shortcut=None,
    is_available=lambda ctx: _is_objectives_view(ctx),
    get_display_name=_display_codespace_run_plan,
),
```

### 2. `src/erk/tui/app.py`

**Add execution handler** after the `close_objective` handler (~line 978):

```python
elif command_id == "codespace_run_plan":
    self._push_streaming_detail(
        row=row,
        command=[
            "erk", "codespace", "run", "objective", "plan",
            str(row.issue_number),
        ],
        title=f"Codespace Run Plan #{row.issue_number}",
        timeout=600.0,
    )
```

Uses `_push_streaming_detail` (same as `one_shot_plan`) with a 600s timeout since codespace startup + remote plan execution takes time.

## Verification

- Run `devrun` with `make fast-ci` to check lint/type/tests pass