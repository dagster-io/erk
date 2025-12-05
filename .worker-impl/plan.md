# Plan: Add `--base` option to `erk submit`

## Goal

Allow `erk submit` to target any branch (not just master/main) for creating PRs and branches. Primary use case: submitting work against existing feature branches for stacked work.

## Implementation

### 1. Add `--base` CLI option to `submit_cmd`

**File:** `src/erk/cli/commands/submit.py`

Add a `--base` option to the click command:

```python
@click.option(
    "--base",
    type=str,
    default=None,
    help="Base branch for PR (defaults to trunk branch). Use for targeting feature branches.",
)
```

### 2. Validate the base branch exists (LBYL)

If `--base` is provided, validate it exists on remote before proceeding:

```python
if base is not None:
    if not ctx.git.branch_exists_on_remote(repo.root, "origin", base):
        user_output(
            click.style("Error: ", fg="red")
            + f"Base branch '{base}' does not exist on remote"
        )
        raise SystemExit(1)
    target_branch = base
else:
    target_branch = ctx.git.detect_trunk_branch(repo.root)
```

### 3. Pass base branch to validation and submission functions

Update `_validate_issue_for_submit` to accept `base_branch` parameter:
- Line 202: Remove `detect_trunk_branch` call, use passed parameter
- Line 230: Already passes `trunk_branch` to `create_development_branch`

Update `_submit_single_issue` to accept `base_branch` parameter:
- Line 283: Remove `detect_trunk_branch` call, use passed parameter
- Lines 327, 398: Use parameter for PR base
- Line 363: Use parameter for branch creation

### 4. Update function signatures

```python
def _validate_issue_for_submit(
    ctx: ErkContext,
    repo: RepoContext,
    issue_number: int,
    base_branch: str,  # NEW
) -> ValidatedIssue:

def _submit_single_issue(
    ctx: ErkContext,
    repo: RepoContext,
    validated: ValidatedIssue,
    submitted_by: str,
    original_branch: str,
    base_branch: str,  # NEW
) -> SubmitResult:
```

### 5. Add tests

**File:** `tests/commands/test_submit.py`

Add tests:
- `test_submit_with_custom_base_branch` - verify PR created with custom base
- `test_submit_with_invalid_base_branch` - verify error when base doesn't exist

## Files to Modify

1. `src/erk/cli/commands/submit.py` - Add option and thread through base_branch
2. `tests/commands/test_submit.py` - Add tests for new functionality

## Notes

- The workflow (`dispatch-erk-queue-git.yml`) doesn't need changes - it just uses the PR's base branch
- `create_development_branch` already supports `base_branch` parameter
- No changes needed to `IssueLinkBranches` interface