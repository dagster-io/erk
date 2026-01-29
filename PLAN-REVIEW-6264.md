# Consolidate Reminder Hooks

## Problem

Currently there are two separate UserPromptSubmit hook entries in `settings.json`:

1. `user-prompt-hook` (Python) — emits session context + capability-gated reminders (devrun, dignified-python, tripwires, explore-docs)
2. `fake-driven-testing-reminder.sh` (shell script) — emits a static "load fake-driven-testing" nudge

Additionally, the `dignified-python` reminder fires on **every prompt** via `user-prompt-hook`, but the new `pre-tool-use-hook` already provides a targeted just-in-time reminder when editing `.py` files. The per-prompt reminder is now redundant.

## Changes

### 1. Absorb `fake-driven-testing` into `user-prompt-hook.py`

Add a `build_fake_driven_testing_reminder()` pure function and wire it into the hook's capability check loop.

**File:** `src/erk/cli/commands/exec/scripts/user_prompt_hook.py`

- Add `build_fake_driven_testing_reminder()` returning the static reminder string
- Add `if is_reminder_installed(hook_ctx.repo_root, "fake-driven-testing"):` block in the hook

### 2. Remove `dignified-python` reminder from `user-prompt-hook.py`

Since `pre-tool-use-hook` provides the just-in-time reminder on `.py` edits, remove:

- `build_dignified_python_reminder()` function
- The `is_reminder_installed(..., "dignified-python")` block in the hook

**File:** `src/erk/cli/commands/exec/scripts/user_prompt_hook.py`

### 3. Delete the shell script

**Delete:** `.claude/hooks/fake-driven-testing-reminder.sh`

### 4. Update `settings.json`

Remove the second UserPromptSubmit hook entry (the shell script). Result:

```json
"UserPromptSubmit": [
  {
    "matcher": "*",
    "hooks": [
      {
        "type": "command",
        "command": "ERK_HOOK_ID=user-prompt-hook erk exec user-prompt-hook",
        "timeout": 30
      }
    ]
  }
]
```

### 5. Update `state.toml` reminders list

Add `fake-driven-testing` to the installed reminders list. Remove `dignified-python` (it's now PreToolUse-only, doesn't need to be in the per-prompt list — but keep it installed since the pre-tool-use-hook still checks it).

Actually: keep `dignified-python` in state.toml since `pre-tool-use-hook` still reads it. Just add `fake-driven-testing`:

```toml
[reminders]
installed = [
    "devrun",
    "dignified-python",
    "fake-driven-testing",
    "tripwires",
]
```

### 6. Update tests

**File:** `tests/unit/cli/commands/exec/scripts/test_user_prompt_hook.py`

- Remove `build_dignified_python_reminder` imports and tests
- Add `build_fake_driven_testing_reminder` tests
- Update `_setup_reminders` helper to accept `fake_driven_testing` instead of `dignified_python`
- Update integration tests that check for dignified-python output → check for fake-driven-testing instead

### 7. Update AGENTS.md

Remove the mention of dignified-python from the "three-tier context system" description (it's now two tiers: ambient in AGENTS.md + just-in-time PreToolUse). Update the "Skill Loading Behavior" or "Just-in-time context injection" section to clarify the current architecture.

## Files Modified

- `src/erk/cli/commands/exec/scripts/user_prompt_hook.py` — add fake-driven-testing, remove dignified-python
- `.claude/settings.json` — remove shell script hook entry
- `.claude/hooks/fake-driven-testing-reminder.sh` — **delete**
- `.erk/state.toml` — add `fake-driven-testing` to installed list
- `tests/unit/cli/commands/exec/scripts/test_user_prompt_hook.py` — update tests
- `AGENTS.md` — update hook architecture description

## Verification

1. Run `devrun` agent: `pytest tests/unit/cli/commands/exec/scripts/test_user_prompt_hook.py`
2. Run `devrun` agent: `pytest tests/unit/cli/commands/exec/scripts/test_pre_tool_use_hook.py` (should still pass unchanged)
3. Run `devrun` agent: `ruff check src/erk/cli/commands/exec/scripts/user_prompt_hook.py`
4. Run `devrun` agent: `ty check src/erk/cli/commands/exec/scripts/user_prompt_hook.py`
