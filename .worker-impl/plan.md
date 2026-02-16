# Flatten objective CLI help output to single command list

## Context

The `erk objective --help` output currently shows commands split into two sections: "Top-Level Commands" (containing `list` because it matches the global `top_level_commands` list) and "Other" (containing `check`, `close`, `next-plan`, `view`). This is confusing for a subgroup with only 5 commands. The objective group should display all commands in a single flat "Commands:" section with no group headers.

This is a one-line fix. The `ErkCommandGroup` class already supports a `grouped=False` parameter that produces flat output, and 7 other subgroups already use this pattern (e.g., `wt`, `branch`, `slot`, `project`).

## Changes

### File: `src/erk/cli/commands/objective/__init__.py`

**Change**: Add `grouped=False` to the `@click.group` decorator.

**Before** (line 14):
```python
@click.group("objective", cls=ErkCommandGroup)
```

**After**:
```python
@click.group("objective", cls=ErkCommandGroup, grouped=False)
```

This matches the established pattern used by other subgroups:
- `src/erk/cli/commands/wt/__init__.py` - `grouped=False`
- `src/erk/cli/commands/branch/__init__.py` - `grouped=False`
- `src/erk/cli/commands/slot/__init__.py` - `grouped=False`
- `src/erk/cli/commands/project/__init__.py` - `grouped=False`

### How `grouped=False` works

In `src/erk/cli/help_formatter.py` (lines 231-240), the `ErkCommandGroup.format_commands()` method checks `self.grouped`. When `False`, it skips the section categorization logic entirely and renders all commands under a single "Commands:" section header.

## Files NOT changing

- `src/erk/cli/help_formatter.py` - The `ErkCommandGroup` class already supports flat mode; no changes needed.
- Individual command files (`check_cmd.py`, `close_cmd.py`, etc.) - Only the group decorator changes.
- Tests - No existing tests assert on the objective group's help section headers.

## Verification

1. Run `erk objective --help` and confirm output shows a single "Commands:" section containing all 5 commands (`check`, `close`, `list`, `next-plan`, `view`) without "Top-Level Commands" or "Other" headers.
2. Run `ty` type checker to confirm no type errors.
3. Run `ruff` linter to confirm no lint errors.
4. Run `pytest tests/unit/cli/` to confirm no test regressions.