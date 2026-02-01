# Plan: Add copy-pasteable commands to plan-review PR description

## Summary

Add `erk prepare` and `erk implement` copy-pasteable command blocks to the PR body of erk-plan-review PRs, so reviewers can go directly from plan review to implementation with a single copy-paste.

## Changes

### 1. Modify `_format_pr_body()` in `plan_create_review_pr.py`

**File:** `src/erk/cli/commands/exec/scripts/plan_create_review_pr.py` (lines 62-83)

Add a "Quick Start" section to the PR body with two commands:

```markdown
## Quick Start

Prepare worktree only:
```
erk prepare <issue_number>
```

Prepare and implement:
```
source "$(erk prepare <issue_number> --script)" && erk implement --dangerous
```
```

The `issue_number` parameter is already available in the function signature.

### 2. Update test assertions in `test_plan_create_review_pr.py`

**File:** `tests/unit/cli/commands/exec/scripts/test_plan_create_review_pr.py`

- Update `test_plan_create_review_pr_body_format` (line 195) to assert the new command blocks are present
- Update `test_plan_create_review_pr_success` (line 83) body assertion if needed

## Verification

- Run: `devrun` agent with `uv run pytest tests/unit/cli/commands/exec/scripts/test_plan_create_review_pr.py -v`
- Run: `devrun` agent with `uv run ruff check src/erk/cli/commands/exec/scripts/plan_create_review_pr.py`