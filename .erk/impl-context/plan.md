# Detect missing child branch early in `erk land --up`

## Context

When running `erk land --up`, the validation phase determines a `target_child_branch` from Graphite's tracked metadata and bakes a `cd <path>` into the generated shell script. If the child branch was deleted before the script runs, the `cd` fails with a confusing error after the PR has already merged — too late to do anything about it.

The user hit this: child branch `add-dgibson-print-03-04-1405` was deleted via slot cleanup, then `erk land -u` ran successfully but the final `cd` failed.

## Change

Add a local branch existence check during validation, right after resolving `target_child_branch` from Graphite metadata.

### File: `src/erk/cli/commands/land_cmd.py`

**In `_resolve_land_target_current_branch()`, after line 721** (`target_child_branch = children[0]`):

Add check that the child branch exists as a local git branch:

```python
local_branches = ctx.git.branch.list_local_branches(repo.root)
Ensure.invariant(
    target_child_branch in local_branches,
    f"Cannot use --up: child branch '{target_child_branch}' no longer exists locally.\n"
    "It may have been deleted. Use 'erk land' without --up to return to trunk.",
)
```

This fails fast with a clear message before any mutations happen.

### File: `tests/commands/land/test_up_flag.py`

Add test: `test_land_with_up_child_branch_deleted_fails_before_merge`

Set up FakeGraphite with a child branch in metadata, but configure FakeGit with `local_branches` that excludes the child. Assert exit code != 0 and error message contains "no longer exists locally".

## Verification

- Run: `uv run pytest tests/commands/land/test_up_flag.py`
- Existing `--up` tests should still pass (they include child branch in worktrees which implies local branch existence)
