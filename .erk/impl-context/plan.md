# Pre-check for duplicate branch/PR in dispatch_one_shot

## Context

When `erk workflow smoke-test` (or any one-shot dispatch) runs and a PR already exists for the generated branch name, `create_pr` fails with a raw HTTP 422 error from GitHub's API. The error message is unhelpful:

```
Failed during: Creating draft PR
Error during dispatch: Failed to create pull request for branch 'plnd/smoke-test-03-01-2110'
```

Two LBYL violations exist:
1. **Line 224**: `create_branch()` returns `BranchCreated | BranchAlreadyExists` but the return value is ignored
2. **No pre-check for existing PR**: The code attempts PR creation without first checking if one already exists

## Changes

### 1. Handle `BranchAlreadyExists` return (one_shot_dispatch.py:224)

Check the return value of `create_branch()` and fail with a clear message:

```python
branch_result = ctx.git.branch.create_branch(repo.root, branch_name, trunk, force=False)
if isinstance(branch_result, BranchAlreadyExists):
    user_output(
        click.style("Error: ", fg="red")
        + f"Branch '{branch_name}' already exists locally. "
        + "Run 'erk delete <branch>' to clean up, then retry."
    )
    raise SystemExit(1)
```

Add `BranchAlreadyExists` to the imports from `erk_shared.gateway.git.branch_ops.types`.

### 2. Pre-check for existing PR before creating one (one_shot_dispatch.py, before line 289)

After the push succeeds but before calling `create_pr`, check if a PR already exists:

```python
existing_pr = ctx.github.get_pr_for_branch(repo.root, branch_name)
if isinstance(existing_pr, PRDetails):
    pr_num = existing_pr.number
    user_output(
        click.style("Error: ", fg="red")
        + f"A pull request already exists for branch '{branch_name}' (#{pr_num}). "
        + "Run 'erk delete <branch>' to clean up, then retry."
    )
    raise SystemExit(1)
```

Add `PRDetails` and `PRNotFound` to the imports from `erk_shared.gateway.github.types`.

### 3. Add test for branch-already-exists case

In `tests/commands/one_shot/test_one_shot_dispatch.py`, add a test that configures `FakeGit` to return `BranchAlreadyExists` and verifies the dispatch raises `SystemExit` with a clear error.

### 4. Add test for PR-already-exists case

Add a test that pre-configures `FakeGitHub` with an existing PR for the branch name and verifies dispatch catches it before attempting `create_pr`.

## Files to modify

- `src/erk/cli/commands/one_shot_dispatch.py` — add LBYL checks and imports
- `tests/commands/one_shot/test_one_shot_dispatch.py` — add two tests

## Verification

- Run `uv run pytest tests/commands/one_shot/test_one_shot_dispatch.py` to verify new and existing tests pass
- Run `uv run ty check src/erk/cli/commands/one_shot_dispatch.py` for type checking
