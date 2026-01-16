# Plan: Remove erk-plan Label from Objectives

## Problem

The `erk dash` command displays objectives alongside regular plans. Objectives currently have both `erk-plan` AND `erk-objective` labels, so when the dashboard queries for `erk-plan` issues, it includes objectives.

## Solution

Remove the `erk-plan` label from objective creation. Objectives will only have `erk-objective` label.

- **Plans**: `erk-plan` label
- **Objectives**: `erk-objective` label only

This is a cleaner separation - objectives are NOT plans, they're higher-level coordination documents.

## Implementation

### 1. Core Change: `packages/erk-shared/src/erk_shared/github/plan_issues.py`

**Line 264** - Change from:
```python
labels = [_LABEL_ERK_PLAN, _LABEL_ERK_OBJECTIVE]
```
To:
```python
labels = [_LABEL_ERK_OBJECTIVE]
```

**Lines 227-231, 241, 263** - Update docstrings/comments that mention "erk-plan + erk-objective" pattern.

### 2. Test Update: `packages/erk-shared/tests/unit/github/test_plan_issues.py`

**Lines 534, 550-552** - Update test to expect only `erk-objective` label:
```python
assert labels == ["erk-objective"]
```

### 3. Exec Script Docstring: `src/erk/cli/commands/exec/scripts/objective_save_to_issue.py`

**Lines 6-7** - Update docstring to remove mention of `erk-plan` label.

### 4. Documentation Updates

- `.claude/skills/objective/SKILL.md:32` - Update label comparison table
- `.claude/commands/erk/objective-create.md:336` - Update label row in table

## Files Modified

1. `packages/erk-shared/src/erk_shared/github/plan_issues.py` - Remove erk-plan from objective labels
2. `packages/erk-shared/tests/unit/github/test_plan_issues.py` - Update label assertions
3. `src/erk/cli/commands/exec/scripts/objective_save_to_issue.py` - Update docstring
4. `.claude/skills/objective/SKILL.md` - Update documentation
5. `.claude/commands/erk/objective-create.md` - Update documentation

## Verification

1. Run unit tests: `make test` (specifically test_plan_issues.py)
2. Create a test objective and verify it only has `erk-objective` label
3. Run `erk dash` and verify objectives no longer appear

## Note: Existing Objectives

Existing objectives in the repo will still have both labels. They can be manually updated via GitHub UI or left as-is (they'll appear in both `erk dash` and `erk objective list` until the `erk-plan` label is removed).