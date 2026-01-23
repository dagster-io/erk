# Plan: Move [erk-learn] to Beginning of Plan Titles

## Summary

Change the title format for erk-learn plans from `"{title} [erk-learn]"` to `"[erk-learn] {title}"`.

## Changes

### 1. Title Generation Logic

**File**: `packages/erk-shared/src/erk_shared/github/plan_issues.py:155`

Modify the title construction to handle erk-learn differently:

```python
# Current:
issue_title = f"{title} {title_suffix}"

# New:
if is_learn_plan:
    issue_title = f"{title_suffix} {title}"
else:
    issue_title = f"{title} {title_suffix}"
```

### 2. Update Test Fixture

**File**: `tests/commands/plan/learn/test_complete.py:30`

Update the test fixture title format:

```python
# Current:
title=f"Learn Plan #{number} [erk-learn]",

# New:
title=f"[erk-learn] Learn Plan #{number}",
```

## Verification

1. Run tests: `pytest tests/commands/plan/learn/`
2. Run tests that cover plan issue creation