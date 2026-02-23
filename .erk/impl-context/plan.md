# Plan: Add "Implement in new worktree" option to plan-save next steps

## Context

After saving a plan, the next steps output is missing the option to implement in a new worktree from outside Claude Code. The `prepare_new_slot_and_implement` property already exists on both `IssueNextSteps` and `DraftPRNextSteps` dataclasses but neither `format_next_steps_plain()` nor `format_draft_pr_next_steps_plain()` includes it in the output.

## Changes

### 1. `packages/erk-shared/src/erk_shared/output/next_steps.py`

Add the implement line to both format functions.

**`format_draft_pr_next_steps_plain()`** (line 105) — add `Implement: {s.prepare_new_slot_and_implement}` to the "exit Claude Code" section:

```python
def format_draft_pr_next_steps_plain(pr_number: int, *, branch_name: str) -> str:
    s = DraftPRNextSteps(pr_number=pr_number, branch_name=branch_name)
    return f"""Next steps:

View PR: {s.view}

In Claude Code:
  Submit to queue: {SUBMIT_SLASH_COMMAND}

OR exit Claude Code first, then run one of:
  Checkout: {s.prepare}
  Implement: {s.prepare_new_slot_and_implement}
  Submit to Queue: {s.submit}"""
```

**`format_next_steps_plain()`** (line 90) — same change:

```python
def format_next_steps_plain(issue_number: int) -> str:
    s = IssueNextSteps(issue_number)
    return f"""Next steps:

View Issue: {s.view}

In Claude Code:
  Submit to queue: {SUBMIT_SLASH_COMMAND}

OR exit Claude Code first, then run one of:
  Checkout: {s.prepare}
  Implement: {s.prepare_and_implement}
  Submit to Queue: {s.submit}"""
```

Note: Issue version uses `prepare_and_implement` (not `new_slot`) since issue plans don't have slots.

### 2. Test updates

**`packages/erk-shared/tests/unit/output/test_next_steps.py`** — add assertion that the implement command appears in format output.

**`tests/unit/shared/test_next_steps.py`** — add tests to both `TestFormatNextStepsPlain` and `TestFormatDraftPRNextStepsPlain` verifying the implement command is present.

## Verification

Run scoped tests:
```bash
uv run pytest packages/erk-shared/tests/unit/output/test_next_steps.py tests/unit/shared/test_next_steps.py
```
