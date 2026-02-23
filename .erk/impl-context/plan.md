# Eliminate "Prepare" verbiage from plan-save next-steps output

## Context

The next-steps output shown after saving a plan displays a "Prepare+Implement" line that's confusing. The user wants to remove this line from the output. The "Local" label will be renamed to "Checkout" to better describe what `erk br co --for-plan` does.

## Changes

### 1. `packages/erk-shared/src/erk_shared/output/next_steps.py`

In both `format_next_steps_plain` and `format_draft_pr_next_steps_plain`:
- Rename `Local:` → `Checkout:`
- Remove the `Implement:` line (which shows the `prepare_and_implement` command)

The properties (`prepare`, `prepare_and_implement`, etc.) are kept — they're used by the TUI.

**Before:**
```
OR exit Claude Code first, then run one of:
  Local: {s.prepare}
  Implement: {s.prepare_and_implement}
  Submit to Queue: {s.submit}
```

**After:**
```
OR exit Claude Code first, then run one of:
  Checkout: {s.prepare}
  Submit to Queue: {s.submit}
```

### 2. `.claude/commands/erk/plan-save.md` (lines 193-196, 210-213)

Remove the "Prepare+Implement" lines from both backend output specs and rename "Local" → "Checkout".

### 3. `tests/unit/shared/test_next_steps.py`

- Remove `test_contains_implement_command` tests from both `TestFormatNextStepsPlain` and `TestFormatDraftPRNextStepsPlain`
- (The property tests for `prepare_and_implement` stay — those properties still exist)

### 4. `packages/erk-shared/tests/unit/output/test_next_steps.py`

- Update `test_format_draft_pr_next_steps_plain_uses_for_plan` — remove assertion for `source "$(erk br co --for-plan 42 --script)"`

### 5. `src/erk/cli/commands/plan/create_cmd.py` (line 120)

Rename label `Prepare:` → `Checkout:`.

## Verification

Run scoped tests:
```bash
uv run pytest tests/unit/shared/test_next_steps.py packages/erk-shared/tests/unit/output/test_next_steps.py tests/commands/plan/test_create.py
```
