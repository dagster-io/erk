# Enable Learn Prompts for Remote Plan Branches During `erk land`

## Context

When landing remotely-implemented PRs (e.g., `plan/fix-plan-header-block-not-02-21-1210`), the learn prompt is never shown. This means learn plans are never created for remote implementations.

The learn prompt used to fire during CI implementation, but that was removed (commit `a0d3ee560`, Feb 4) because it ran too early — before review. The intent was to move learn to land time, but the guard `(is_current_branch or worktree_path is not None)` (added in commit `915635382`) blocks remote branches since they have no local worktree.

The `trigger-async-learn` infrastructure already handles remote sessions via branch-based storage (`session/{plan_id}` branches). The guard is the only thing blocking learn prompts for remote PRs.

## Changes

### 1. Remove the worktree/current-branch guard in `land_cmd.py`

**File:** `src/erk/cli/commands/land_cmd.py` (lines 1058-1059)

Change:
```python
plan_id = ctx.plan_backend.resolve_plan_id_for_branch(main_repo_root, target.branch)
if plan_id is not None and (target.is_current_branch or target.worktree_path is not None):
```

To:
```python
plan_id = ctx.plan_backend.resolve_plan_id_for_branch(main_repo_root, target.branch)
if plan_id is not None:
```

### 2. Remove the same guard in `land_pipeline.py`

**File:** `src/erk/cli/commands/land_pipeline.py` (line 341)

Change:
```python
if plan_id is not None and (state.is_current_branch or state.worktree_path is not None):
```

To:
```python
if plan_id is not None:
```

## Why This Is Safe

- `_check_learn_status_and_prompt()` respects `prompt_learn_on_land` config overrides
- Skips learn plans (issues with `erk-learn` label)
- Returns early if learn already completed or pending
- `trigger-async-learn` discovers remote sessions from plan metadata (`last_session_branch`, `last_session_id`)
- Downloads remote sessions via `git show origin/{session_branch}:.erk/session/{session_id}.jsonl`
- Handles zero sessions gracefully (outputs error and returns, no workflow triggered)
- Non-interactive mode auto-selects "trigger async learn" (line 361-362)

## Verification

1. Land a remote plan PR by number: `erk land <pr-number>` — confirm learn prompt appears
2. Land a local plan branch: `erk land` — confirm learn prompt still appears (no regression)
3. Select "trigger async learn" for a remote PR — confirm it discovers the remote session from the branch and triggers the workflow
4. Run existing tests: `pytest tests/ -k learn` and `pytest tests/ -k land`
