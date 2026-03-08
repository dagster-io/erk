# Add `--branch` option to `erk codespace connect`

## Context

Running `erk codespace connect --shell` while on a local branch that doesn't exist on the remote (e.g., `restructured-land-loop`) fails because it tries `git fetch origin restructured-land-loop` which errors with "couldn't find remote ref". The user needs a way to specify a different branch (e.g., `master`) instead of inheriting the current local one.

## Changes

### `src/erk/cli/commands/codespace/connect_cmd.py`

1. Add `--branch` Click option to specify the remote branch to checkout
2. When `--branch` is provided, use that value instead of auto-detecting from `ctx.git.branch.get_current_branch()`
3. When `--branch` is provided, skip the local branch detection entirely (works even outside a repo)

```python
@click.option("--branch", "-b", help="Branch to checkout on the codespace (default: current local branch).")
```

Logic change (lines 60-70):
```python
# If --branch provided, use it directly; otherwise detect from local repo
if branch is not None:
    local_branch = branch
elif isinstance(ctx.repo, NoRepoSentinel):
    local_branch = None
else:
    local_branch = ctx.git.branch.get_current_branch(ctx.repo_root)
```

### `tests/unit/cli/commands/codespace/test_connect_cmd.py`

Add tests:
1. `test_connect_with_branch_option_overrides_local_branch` - verifies `--branch master` uses `master` instead of the local branch
2. `test_connect_with_branch_option_and_shell` - verifies `--branch` works with `--shell` flag
3. `test_connect_with_branch_option_no_repo` - verifies `--branch` works even when not in a git repo

## Verification

Run: `uv run pytest tests/unit/cli/commands/codespace/test_connect_cmd.py`
