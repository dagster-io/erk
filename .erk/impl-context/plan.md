# Fix: erk-dev audit-collect crashes with `repo_info required for list_prs`

## Context

`erk-dev audit-collect` crashes because `create_context()` in `erk_dev/context.py` creates `RealLocalGitHub` with `repo_info=None`. The `list_prs` method asserts `repo_info is not None` since it needs `owner/name` to construct the GitHub API endpoint.

Other callers (statusline, main erk context, gt gateway) all detect `repo_info` from the git remote URL before creating `RealLocalGitHub`.

## Fix

**File:** `packages/erk-dev/src/erk_dev/context.py`

1. Import `get_repo_info` from `erk_shared.context.factories`
2. Reorder `create_context()` so `repo_root` is detected first
3. Call `get_repo_info(git, repo_root)` to get `RepoInfo`
4. Pass the result to `RealLocalGitHub` instead of `None`

The reordering is needed because `get_repo_info` requires a `Git` gateway and `repo_root`, but currently `repo_root` is detected after `RealLocalGitHub` is created.

## Verification

Run `erk-dev audit-collect` and confirm it produces JSON output instead of crashing.
