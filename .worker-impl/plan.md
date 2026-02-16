# Fix rebase-with-conflict-resolution not detecting commits behind target branch

## Context

In [workflow run 22060595791](https://github.com/dagster-io/erk/actions/runs/22060595791), the `pr-fix-conflicts` rebase job reported `Branch is already up-to-date with master (no rebase needed)` even though the PR (#7167) has merge conflicts (GitHub reports `CONFLICTING` / `DIRTY` merge state).

**Root cause**: Line 220 of `rebase_with_conflict_resolution.py` calls `git.branch.get_ahead_behind(cwd, branch_name)`, which compares the branch against its **own remote tracking branch** (`origin/{branch_name}`), NOT against `origin/{target_branch}` (master). Since CI checks out the branch fresh from origin, it's trivially up-to-date with its own remote — so `behind == 0` and the script exits early without attempting the rebase.

**Intended behavior**: Compare against `origin/{target_branch}` to determine if the branch needs rebasing.

## Approach

Add a `count_commits_behind` method to `GitAnalysisOps` (symmetric to the existing `count_commits_ahead`), then use it in the rebase script to correctly compare against the target branch.

## Changes

### 1. Add `count_commits_behind` to analysis ops (5 files)

**`packages/erk-shared/src/erk_shared/gateway/git/analysis_ops/abc.py`**
- Add abstract method `count_commits_behind(self, cwd: Path, target_branch: str) -> int`
- Docstring: "Count commits in target_branch that are not in HEAD. Uses `git rev-list --count HEAD..{target_branch}`."

**`packages/erk-shared/src/erk_shared/gateway/git/analysis_ops/real.py`**
- Implement with `git rev-list --count HEAD..{target_branch}` (same pattern as `count_commits_ahead` but args swapped)

**`packages/erk-shared/src/erk_shared/gateway/git/analysis_ops/fake.py`**
- Add `commits_behind` dict param to `__init__` (same pattern as `commits_ahead`)
- Implement lookup: `return self._commits_behind.get((cwd, target_branch), 0)`
- Add to `link_state` method

**`packages/erk-shared/src/erk_shared/gateway/git/analysis_ops/dry_run.py`**
- Delegate: `return self._wrapped.count_commits_behind(cwd, target_branch)`

**`packages/erk-shared/src/erk_shared/gateway/git/analysis_ops/printing.py`**
- Delegate: `return self._wrapped.count_commits_behind(cwd, target_branch)`

### 2. Wire through FakeGit

**`packages/erk-shared/src/erk_shared/gateway/git/fake.py`**
- Add `commits_behind` constructor parameter (same pattern as `commits_ahead`)
- Pass to `FakeGitAnalysisOps` via `link_state`

### 3. Fix the rebase script

**`src/erk/cli/commands/exec/scripts/rebase_with_conflict_resolution.py`**

Replace lines 218-225:
```python
# Check if behind using ahead_behind
try:
    _ahead, behind = git.branch.get_ahead_behind(cwd, branch_name)
except Exception:
    return RebaseError(...)
```

With:
```python
behind = git.analysis.count_commits_behind(cwd, f"origin/{target_branch}")
```

This correctly counts commits in `origin/{target_branch}` that are not in HEAD.

### 4. Update tests

**`tests/unit/cli/commands/exec/scripts/test_rebase_with_conflict_resolution.py`**

All tests currently configure `ahead_behind={(tmp_path, "feature-branch"): (X, Y)}` on FakeGit. Change these to use `commits_behind={(tmp_path, "origin/main"): Y}` instead (note: the key must use `origin/{target_branch}` since the script now passes that string).

Affected tests:
- `test_rebase_already_up_to_date` — change to `commits_behind={(tmp_path, "origin/main"): 0}`
- `test_rebase_success_no_conflicts` — change to `commits_behind={(tmp_path, "origin/main"): 3}`
- `test_rebase_with_conflicts_resolved_by_claude` — change to `commits_behind={(tmp_path, "origin/main"): 2}`
- `test_rebase_fails_after_max_attempts` — change to `commits_behind={(tmp_path, "origin/main"): 2}`
- `test_rebase_push_failure` — change to `commits_behind={(tmp_path, "origin/main"): 2}`
- `test_cli_already_up_to_date` — change to `commits_behind={(tmp_path, "origin/main"): 0}`
- `test_cli_successful_rebase_generates_summary` — change to `commits_behind={(tmp_path, "origin/main"): 3}`
- `test_conflict_resolution_uses_correct_prompt` — change to `commits_behind={(tmp_path, "origin/main"): 2}`
- `test_model_parameter_passed_correctly` — change to `commits_behind={(tmp_path, "origin/main"): 2}`
- `test_max_attempts_parameter` — change to `commits_behind={(tmp_path, "origin/main"): 2}`

## Verification

1. Run the rebase script tests: `pytest tests/unit/cli/commands/exec/scripts/test_rebase_with_conflict_resolution.py`
2. Run ty type checking
3. Run full fast-ci