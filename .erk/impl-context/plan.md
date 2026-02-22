# Eliminate checkout race condition in one_shot_dispatch.py

## Context

`one_shot_dispatch.py` has the same race condition we just fixed in `plan_save.py` — it temporarily checks out a branch to commit `.worker-impl/prompt.md`, but the checkout window spans **multiple network calls** (push, create PR, trigger workflow, post comments — lines 222-424), making it far more likely to race than plan_save ever was.

With `commit_files_to_branch` now available (from PR #7783), we can eliminate this checkout entirely. The only reason the branch is checked out is to write/stage/commit a single file. Everything else (push, GitHub API calls) doesn't need HEAD on the branch.

## Implementation

### 1. Refactor `dispatch_one_shot` in `one_shot_dispatch.py`

**File:** `src/erk/cli/commands/one_shot_dispatch.py`

Replace the checkout/write/stage/commit/restore pattern (lines 221-234 + 441-446) with a single `commit_files_to_branch` call:

**Before** (lines 221-234):

```python
try:
    ctx.branch_manager.checkout_branch(repo.root, branch_name)
    worker_impl_dir = repo.root / ".worker-impl"
    worker_impl_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = worker_impl_dir / "prompt.md"
    prompt_file.write_text(params.prompt + "\n", encoding="utf-8")
    ctx.git.commit.stage_files(repo.root, [".worker-impl/prompt.md"])
    ctx.git.commit.commit(repo.root, f"One-shot: {params.prompt[:60]}")
```

**After:**

```python
ctx.git.commit.commit_files_to_branch(
    repo.root,
    branch=branch_name,
    files={".worker-impl/prompt.md": params.prompt + "\n"},
    message=f"One-shot: {params.prompt[:60]}",
)
```

Also:

- Remove the happy-path restore on line 424 (`ctx.branch_manager.checkout_branch(repo.root, original_branch)`)
- Remove the `finally` block (lines 441-446) that restores the branch on error
- Remove the `try:` on line 221 (no longer needed)
- The `original_branch` variable (line 208-209) is no longer needed for restoration but is still used for detached HEAD check (line 210-215), so keep it

### 2. Update tests

**File:** `tests/commands/one_shot/test_one_shot_dispatch.py`

**`test_dispatch_happy_path`** (line 21):

- Lines 60-62: Change `git.commits[0].staged_files` → `git.branch_commits[0].files` with key check
- Lines 64-67: Remove filesystem assertions (`prompt_file.exists()`, `read_text`). Files are no longer written to the working tree — verify content via `branch_commits[0].files[".worker-impl/prompt.md"]` instead
- Line 102: Keep as-is — we're still on "main" (trivially true since no checkout occurs)

**`test_dispatch_restores_branch_on_error`** (line 180):

- Rename to `test_dispatch_stays_on_original_branch_on_error`
- Remove assertions about branch restoration (no checkout = nothing to restore)
- Keep the assertion that we're still on "main" — validates the race-free behavior
- Keep the push error injection to verify error handling still works

**`test_dispatch_long_prompt_truncates_workflow_input`** (line 412):

- Lines 447-450: Replace filesystem assertions with `branch_commits` check for full prompt content
- Line 453: Change `git.commits[0].staged_files` → `git.branch_commits[0].files`

Other tests (`test_dispatch_with_extra_inputs`, `test_dispatch_dry_run`, `test_dispatch_creates_skeleton_plan_issue`, `test_dispatch_posts_queued_event_comment`, `test_dispatch_writes_metadata_to_plan_issue`, `test_dispatch_draft_pr_lifecycle`) have no commit/filesystem assertions and need no changes.

## Files to modify

1. `src/erk/cli/commands/one_shot_dispatch.py` — Replace checkout pattern with `commit_files_to_branch`
2. `tests/commands/one_shot/test_one_shot_dispatch.py` — Update 3 tests

## Verification

1. Run unit tests: `uv run pytest tests/commands/one_shot/test_one_shot_dispatch.py -v`
2. Run full fast-ci: `make fast-ci`
