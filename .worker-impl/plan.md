# Plan: Stop auto-executing learn plans in CI

## Context

When `erk land` triggers async learning, the learn workflow (`.github/workflows/learn.yml`) runs `/erk:learn` in GitHub Actions. The learn skill creates a learn plan issue, then in Step 10's "Post-Learn Decision Menu," CI mode auto-selects "Submit for implementation" — which calls `/erk:plan-submit` and queues remote execution. The user wants learn plans to only be created as issues, never auto-implemented.

## Change

**File:** `.claude/commands/erk/learn.md` (~line 797-800)

Change the CI auto-selection from option 1 (submit) to option 4 (done):

```
# Before
- If CI_MODE: Auto-select option 1 (submit) and proceed to Step 11
- If not interactive: Auto-select option 1 (submit) and proceed to Step 11

# After
- If CI_MODE: Auto-select "Done" and proceed to Step 11
- If not interactive: Auto-select "Done" and proceed to Step 11
```

This preserves:
- The plan issue creation (Step 7)
- The parent plan metadata updates (Step 9)
- The learn evaluation tracking (Step 11)

It only removes the automatic `/erk:plan-submit` call in CI mode.

## Verification

1. Read the modified learn.md and confirm the CI auto-selection now picks "Done"
2. Trace the flow: `erk land` → `trigger-async-learn` → `learn.yml` → `/erk:learn` → Step 10 now skips submission