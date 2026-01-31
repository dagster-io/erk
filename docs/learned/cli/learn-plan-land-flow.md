---
title: Learn Plan Land Flow
read_when:
  - "landing PRs associated with learn plans"
  - "understanding learn plan status transitions"
  - "working with tripwire documentation promotion"
tripwires:
  - action: "landing a PR without updating associated learn plan status"
    warning: "Learn plan PRs trigger special execution pipeline steps: check_learn_status, update_learn_plan, promote_tripwires, close_review_pr. Ensure these steps execute after PR merge."
---

# Learn Plan Land Flow

Learn plan branches require special handling in the land command execution pipeline. After the PR merges, the land command updates plan status, promotes tripwires to category files, and closes review PRs.

## Learn Plan Detection

Learn plans are detected during validation pipeline:

```python
def validate_checks(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Validate PR checks and detect learn plan."""
    pr_details = ctx.github.get_pr(state.pr_number)

    # Detect learn plan from labels or branch name
    is_learn_plan = (
        "erk-learn" in pr_details.labels
        or pr_details.branch.startswith("erk-learn-")
    )

    return dataclasses.replace(state, is_learn_plan=is_learn_plan)
```

**Detection criteria**:

- PR has `erk-learn` label, OR
- Branch name starts with `erk-learn-`

Once detected, `state.is_learn_plan = True` triggers learn-specific execution steps.

## Execution Pipeline Steps for Learn Plans

The execution pipeline includes 4 learn-plan-specific steps:

### 1. merge_pr_step (Standard)

Merges the PR like any other PR - no learn-specific logic.

### 2. check_learn_status

**Purpose**: Verify learn plan issue exists and extract metadata

```python
def check_learn_status(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Check if learn plan issue exists and extract issue number."""
    if not state.is_learn_plan:
        return state  # Skip if not learn plan

    # Extract issue number from PR body or branch
    issue_number = extract_learn_issue_number(state.pr_details.body)
    if issue_number is None:
        return LandError(
            phase="execution",
            error_type="learn-issue-not-found",
            message="Learn plan PR missing issue link",
        )

    # Verify issue exists
    issue = ctx.github.issues.get_issue(issue_number)
    if isinstance(issue, IssueNotFound):
        return LandError(
            phase="execution",
            error_type="learn-issue-not-found",
            message=f"Learn plan issue #{issue_number} not found",
        )

    return dataclasses.replace(state, learn_issue_number=issue_number)
```

**State updates**: Populates `learn_issue_number` field

### 3. update_learn_plan

**Purpose**: Update learn plan issue status to "Landed"

```python
def update_learn_plan(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Update learn plan issue status after PR lands."""
    if not state.is_learn_plan:
        return state  # Skip if not learn plan

    assert state.learn_issue_number is not None

    # Update issue with "Landed" status
    result = ctx.github.issues.update_issue(
        issue_number=state.learn_issue_number,
        body=update_status_in_body(original_body, status="Landed"),
    )

    if isinstance(result, IssueUpdateError):
        return LandError(
            phase="execution",
            error_type="learn-plan-update-failed",
            message=f"Failed to update learn plan issue: {result.message}",
        )

    return state
```

**Side effects**: Updates GitHub issue status

### 4. promote_tripwires

**Purpose**: Promote tripwires from plan to category tripwires.md files

```python
def promote_tripwires(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Promote tripwires from learn plan to category files."""
    if not state.is_learn_plan:
        return state  # Skip if not learn plan

    # Find tripwire files created in this PR
    tripwire_files = find_tripwire_files_in_pr(state.pr_number)

    # Promote each to category tripwires.md
    for file_path in tripwire_files:
        category = extract_category_from_path(file_path)
        promote_to_category(file_path, category)

    return dataclasses.replace(state, learn_tripwire_files=tripwire_files)
```

**State updates**: Populates `learn_tripwire_files` field

**Side effects**: Updates `docs/learned/{category}/tripwires.md` files

### 5. close_review_pr

**Purpose**: Close associated review PR if one exists

```python
def close_review_pr(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Close review PR if learn plan had one."""
    if not state.is_learn_plan or not state.has_review_pr:
        return state  # Skip if not learn plan or no review PR

    # Find review PR (branch: erk-learn-{issue}-review)
    review_pr = ctx.github.get_pr_for_branch(f"{state.pr_details.branch}-review")
    if isinstance(review_pr, PRNotFound):
        return state  # No review PR found (expected if async)

    # Close the review PR
    result = ctx.github.close_pr(review_pr.number)
    if isinstance(result, PRCloseError):
        return LandError(
            phase="execution",
            error_type="review-pr-close-failed",
            message=f"Failed to close review PR: {result.message}",
        )

    return state
```

**State updates**: None (terminal step)

**Side effects**: Closes GitHub PR

### 6. cleanup_branches (Standard)

Deletes feature branches like any other PR - no learn-specific logic.

## State Field Usage

Learn-specific state fields:

| Field                 | Populated By         | Used By                        |
| --------------------- | -------------------- | ------------------------------ |
| `is_learn_plan`       | `validate_checks`    | All learn steps (skip check)   |
| `learn_issue_number`  | `check_learn_status` | `update_learn_plan`            |
| `learn_tripwire_files | `promote_tripwires`  | (Terminal - for logging)       |
| `has_review_pr`       | `validate_checks`    | `close_review_pr` (skip check) |

## Skip Conditions

Learn pipeline steps skip execution if:

- `state.is_learn_plan == False` (not a learn plan)
- `state.has_review_pr == False` (no review PR to close)

**Pattern**:

```python
def learn_step(ctx: ErkContext, state: LandState) -> LandState | LandError:
    if not state.is_learn_plan:
        return state  # Skip - not a learn plan
    # ... learn-specific logic ...
```

## Error Handling

Learn-specific errors:

| Error Type                | Meaning                            | Recovery                     |
| ------------------------- | ---------------------------------- | ---------------------------- |
| `learn-issue-not-found`   | Issue link missing or invalid      | Fix PR body, re-run land     |
| `learn-plan-update-failed | GitHub API error updating issue    | Manually update issue status |
| `review-pr-close-failed`  | GitHub API error closing review PR | Manually close review PR     |

All errors short-circuit the execution pipeline (no further steps run).

## Async Learn Plans

Some learn plans are implemented asynchronously (not by the planner):

- **No review PR** - `has_review_pr == False`
- **close_review_pr** skips (no PR to close)
- Other steps execute normally

## Relationship to Plan Issues

Learn plan issues track documentation work:

- **Status field**: "Planning" → "Review" → "Landed"
- **Linked PRs**: Implementation PR + optional review PR
- **Tripwires**: Extracted from plan, promoted on land

The land command transitions status from "Review" → "Landed" and promotes tripwires.

## Reference Implementation

**File**: `src/erk/cli/commands/workflows/land_pipeline.py`

**Execution pipeline** (lines 159-224):

```python
def run_execution_pipeline(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Run all execution steps, short-circuit on first error."""
    for step in [
        merge_pr_step,           # Standard merge
        check_learn_status,      # Learn: verify issue exists
        update_learn_plan,       # Learn: update issue status
        promote_tripwires,       # Learn: promote to category files
        close_review_pr,         # Learn: close review PR
        cleanup_branches,        # Standard cleanup
    ]:
        result = step(ctx, state)
        if isinstance(result, LandError):
            return result
        state = result
    return state
```

## Related Documentation

- [Linear Pipelines](../architecture/linear-pipelines.md) - Two-pipeline pattern overview
- [Land State Threading](../architecture/land-state-threading.md) - State field lifecycle
- [Erk Learn Workflow](../planning/erk-learn-workflow.md) - Learn plan lifecycle
