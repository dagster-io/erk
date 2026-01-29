# Remove Redundant dignified-python Per-Prompt Reminder

## Problem

The `dignified-python` reminder fires on **every prompt** via `user-prompt-hook`, but the `pre-tool-use-hook` already provides a targeted just-in-time reminder when editing `.py` files. The per-prompt reminder is now redundant.

The `fake-driven-testing-reminder.sh` shell script hook remains as-is — it is intentionally kept separate.

## Changes

### 1. Remove `dignified-python` reminder from `user-prompt-hook.py`

Since `pre-tool-use-hook` provides the just-in-time reminder on `.py` edits, remove:

- `build_dignified_python_reminder()` function
- The `is_reminder_installed(..., "dignified-python")` block in the hook

**File:** `src/erk/cli/commands/exec/scripts/user_prompt_hook.py`

### 2. Update tests

**File:** `tests/unit/cli/commands/exec/scripts/test_user_prompt_hook.py`

- Remove `build_dignified_python_reminder` imports and tests
- Update `_setup_reminders` helper: remove `dignified_python` parameter
- Update integration tests that check for dignified-python output

### 3. Update AGENTS.md

Update the "Just-in-time context injection" section to reflect that dignified-python reminders are now only delivered via the PreToolUse hook (no longer per-prompt).

## Files Modified

- `src/erk/cli/commands/exec/scripts/user_prompt_hook.py` — remove dignified-python reminder
- `tests/unit/cli/commands/exec/scripts/test_user_prompt_hook.py` — update tests
- `AGENTS.md` — update hook architecture description

## Verification

1. Run `devrun` agent: `pytest tests/unit/cli/commands/exec/scripts/test_user_prompt_hook.py`
2. Run `devrun` agent: `pytest tests/unit/cli/commands/exec/scripts/test_pre_tool_use_hook.py` (should still pass unchanged)
3. Run `devrun` agent: `ruff check src/erk/cli/commands/exec/scripts/user_prompt_hook.py`
4. Run `devrun` agent: `ty check src/erk/cli/commands/exec/scripts/user_prompt_hook.py`
