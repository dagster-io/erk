# Add `copy_land` Command to Command Palette

## Context

The command palette already has an ACTION entry (`land_pr`) that executes `erk land <pr_number>` via a streaming subprocess. The user wants a COPY (📋) entry that simply copies the `erk land <pr_number>` command to the clipboard — mirroring the pattern used by `copy_submit`, `copy_replan`, etc.

## Files to Modify

1. `src/erk/tui/commands/registry.py` — add display name generator + CommandDefinition
2. `src/erk/tui/app.py` — add handler in `execute_palette_command`
3. `src/erk/tui/screens/plan_detail_screen.py` — add handler in `execute_command`

## Implementation Steps

### 1. `registry.py` — Add display name generator

After `_display_copy_replan`, add:

```python
def _display_copy_land(ctx: CommandContext) -> str:
    """Display name for copy_land command."""
    return f"erk land {ctx.row.pr_number}"
```

### 2. `registry.py` — Add CommandDefinition

In the `# === PLAN COPIES ===` section, after the `copy_replan` entry:

```python
CommandDefinition(
    id="copy_land",
    name="erk land",
    description="land",
    category=CommandCategory.COPY,
    shortcut=None,
    is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_number is not None,
    get_display_name=_display_copy_land,
),
```

### 3. `app.py` — Add handler in `execute_palette_command`

After the `copy_replan` block (line ~851), add:

```python
elif command_id == "copy_land":
    if row.pr_number:
        cmd = f"erk land {row.pr_number}"
        self._provider.clipboard.copy(cmd)
        self.notify(f"Copied: {cmd}")
```

### 4. `plan_detail_screen.py` — Add handler in `execute_command`

After the `copy_replan` block (line ~655), add:

```python
elif command_id == "copy_land":
    if row.pr_number:
        cmd = f"erk land {row.pr_number}"
        executor.copy_to_clipboard(cmd)
        executor.notify(f"Copied: {cmd}", severity=None)
```

## Verification

Run `erk dash -i`, select a plan with a PR, open the command palette, and confirm a new `📋 land: erk land <pr_number>` entry appears and copies the correct command to the clipboard.
