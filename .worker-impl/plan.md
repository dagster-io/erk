# Plan: Add Emoji Prefix to Learn Plan Issue in TUI

## Summary

Add an emoji prefix (📋) to the `completed_with_plan` status display in the erk dash TUI's "lrn" column, making it consistent with other statuses like `plan_completed` (✓) and `pending_review` (🚧).

## Current Behavior

When `learn_status == "completed_with_plan"`, the lrn column shows just `#456` (the plan issue number).

## Desired Behavior

Show `📋 #456` with an emoji prefix, similar to how `plan_completed` shows `✓ #789`.

## Files to Modify

### 1. `src/erk/tui/data/provider.py`

Update both formatting functions:

- `_format_learn_display()` (line 649): Change `f"#{learn_plan_issue}"` to `f"📋 #{learn_plan_issue}"`
- `_format_learn_display_icon()` (line 686): Change `f"#{learn_plan_issue}"` to `f"📋 #{learn_plan_issue}"`

Also update the docstrings in both functions to reflect the new format.

### 2. `tests/fakes/plan_data_provider.py`

Update `make_plan_row()` helper (lines 223-225):

- Change `learn_display = f"#{learn_plan_issue}"` to `learn_display = f"📋 #{learn_plan_issue}"`
- Change `learn_display_icon = f"#{learn_plan_issue}"` to `learn_display_icon = f"📋 #{learn_plan_issue}"`

### 3. `tests/tui/test_plan_table.py`

Update test assertions:

- Line 122: Change `assert row.learn_display == "#456"` to `assert row.learn_display == "📋 #456"`

### 4. `tests/tui/data/test_provider.py`

Update test assertion:

- Line 909: Change `assert row.learn_display == "#456"` to `assert row.learn_display == "📋 #456"`

## Verification

1. Run targeted tests: `uv run pytest tests/tui/data/test_provider.py tests/tui/test_plan_table.py -k learn`
2. Run broader TUI tests: `uv run pytest tests/tui/`
3. Manual verification: `erk dash -i` and check lrn column displays "📋 #NNN" for plans with completed learn analysis