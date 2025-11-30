# Plan: Enable `erk submit` to Support Multiple Arguments

## Summary

Modify `erk submit` to accept multiple issue numbers as arguments, enabling batch submission of plans with atomic validation (validate all before submitting any).

**Current behavior:** `erk submit 123` (single issue)
**New behavior:** `erk submit 123 456 789` (multiple issues)

## Implementation

### 1. Modify CLI Argument Definition

**File:** `src/erk/cli/commands/submit.py`

Change from:
```python
@click.command("submit")
@click.argument("issue_number", type=int)
@click.pass_obj
def submit_cmd(ctx: ErkContext, issue_number: int) -> None:
```

To:
```python
@click.command("submit")
@click.argument("issue_numbers", type=int, nargs=-1, required=True)
@click.pass_obj
def submit_cmd(ctx: ErkContext, issue_numbers: tuple[int, ...]) -> None:
```

Note: `required=True` with `nargs=-1` ensures at least one argument is provided.

### 2. Refactor Into Two Phases

**Phase 1: Validate ALL issues upfront**

Extract validation logic into a helper function that returns validated issue data:

```python
@dataclass
class ValidatedIssue:
    """Issue that passed all validation checks."""
    number: int
    issue: IssueInfo
    branch_name: str
    branch_exists: bool
    pr_number: int | None
```

Create validation function:
```python
def _validate_issue_for_submit(
    ctx: ErkContext,
    repo: RepoContext,
    issue_number: int,
) -> ValidatedIssue:
    """Validate a single issue for submission. Raises on any failure."""
```

In main function, validate all issues first:
```python
# Validate ALL issues upfront (atomic - fail fast before any side effects)
validated: list[ValidatedIssue] = []
for issue_number in issue_numbers:
    validated.append(_validate_issue_for_submit(ctx, repo, issue_number))
```

**Phase 2: Submit all validated issues**

Process each validated issue:
```python
results: list[SubmitResult] = []
for v in validated:
    result = _submit_single_issue(ctx, repo, v, submitted_by, original_branch)
    results.append(result)
```

### 3. Define Result Data Structure

```python
@dataclass
class SubmitResult:
    """Result of submitting a single issue."""
    issue_number: int
    issue_title: str
    issue_url: str
    pr_number: int | None
    pr_url: str | None
    workflow_run_id: str
    workflow_url: str
```

### 4. Update Output for Multiple Issues

Display summary after all submissions:

```python
# Success output
user_output("")
user_output(click.style("✓", fg="green") + f" {len(results)} issue(s) submitted successfully!")
user_output("")
user_output("Submitted issues:")
for r in results:
    user_output(f"  • #{r.issue_number}: {r.issue_title}")
    user_output(f"    Issue: {r.issue_url}")
    if r.pr_url:
        user_output(f"    PR: {r.pr_url}")
    user_output(f"    Workflow: {r.workflow_url}")
```

### 5. Update Docstring

```python
"""Submit issues for remote AI implementation via GitHub Actions.

Creates branch and draft PR locally (for correct commit attribution),
then triggers the dispatch-erk-queue.yml GitHub Actions workflow.

Arguments:
    ISSUE_NUMBERS: One or more GitHub issue numbers to submit

Example:
    erk submit 123
    erk submit 123 456 789

Requires:
    - All issues must have erk-plan label
    - All issues must be OPEN
    - Working directory must be clean (no uncommitted changes)
"""
```

### 6. Update Tests

**File:** `tests/commands/test_submit.py`

Add tests for:
1. `test_submit_multiple_issues_success` - Happy path with 2-3 issues
2. `test_submit_multiple_issues_atomic_validation_failure` - Second issue invalid, nothing submitted
3. `test_submit_single_issue_still_works` - Backwards compatibility

Update existing tests to use `["123"]` tuple format (no change needed - already works).

## Critical Files

| File | Change |
|------|--------|
| `src/erk/cli/commands/submit.py` | Main implementation |
| `tests/commands/test_submit.py` | Test updates |

## Testing Strategy

1. Run existing tests to ensure backwards compatibility
2. Add new multi-argument tests
3. Manual verification with actual GitHub issues