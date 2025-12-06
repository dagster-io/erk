# Plan: Add Literal Types for plan_type and Remove extra_labels

## Summary

Refactor `create_plan_issue` to use `Literal` type for `plan_type` and remove the unused `extra_labels` feature.

## Changes

### 1. Define PlanType Literal

**File**: `packages/erk-shared/src/erk_shared/github/plan_issues.py`

Add type definition at module level:
```python
from typing import Literal

PlanType = Literal["standard", "extraction"]
```

### 2. Update create_plan_issue Signature

**File**: `packages/erk-shared/src/erk_shared/github/plan_issues.py`

Change:
```python
def create_plan_issue(
    github_issues: GitHubIssues,
    repo_root: Path,
    plan_content: str,
    *,
    title: str | None = None,
    plan_type: str | None = None,           # REMOVE
    extra_labels: list[str] | None = None,  # REMOVE
    ...
) -> CreatePlanIssueResult:
```

To:
```python
def create_plan_issue(
    github_issues: GitHubIssues,
    repo_root: Path,
    plan_content: str,
    *,
    title: str | None = None,
    plan_type: PlanType = "standard",       # ADD
    ...
) -> CreatePlanIssueResult:
```

### 3. Update Internal Logic in create_plan_issue

Remove extra_labels handling (lines 115-118):
```python
# DELETE:
if extra_labels:
    for label in extra_labels:
        if label not in labels:
            labels.append(label)
```

Update label logic (currently checks `if plan_type == "extraction"`):
- Logic remains the same, but type checker now validates values

### 4. Remove --label CLI Option

**File**: `src/erk/cli/commands/plan/create_cmd.py`

Remove:
```python
@click.option("--label", "-l", multiple=True, help="Additional labels")
```

Remove from function signature and call to `create_plan_issue`.

### 5. Update Call Sites

**File**: `packages/erk-shared/src/erk_shared/extraction/raw_extraction.py` (line 281)
- Currently: `plan_type="extraction"` ✓ (already correct)

**File**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/create_extraction_plan.py` (line 194)
- Currently: `plan_type="extraction"` ✓ (already correct)

**File**: `src/erk/cli/commands/plan/create_cmd.py`
- Currently: Does not pass `plan_type` (defaults to standard)
- Update to explicitly pass `plan_type="standard"` for clarity

### 6. Update Tests

**File**: `packages/erk-shared/tests/unit/github/test_plan_issues.py`

- Remove tests for `extra_labels` functionality
- Update any tests that pass `plan_type=None` to use `plan_type="standard"`

### 7. Update metadata.py Validation (if needed)

**File**: `packages/erk-shared/src/erk_shared/github/metadata.py`

The `valid_plan_types = {"standard", "extraction"}` validation set should align with the `PlanType` literal. Consider importing the type or keeping the validation set in sync.

## Files to Modify

1. `packages/erk-shared/src/erk_shared/github/plan_issues.py` - Main changes
2. `src/erk/cli/commands/plan/create_cmd.py` - Remove --label option
3. `packages/erk-shared/tests/unit/github/test_plan_issues.py` - Update tests

## Files That May Need Review

- `packages/erk-shared/src/erk_shared/github/metadata.py` - Ensure PlanHeaderSchema validation stays in sync