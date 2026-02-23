# Plan: Convert submit.py checkout cycles to commit_files_to_branch

Part of Objective #7813, Node 2.2

## Context

The submit pipeline in `src/erk/cli/commands/submit.py` uses checkout-based git workflows: checkout a branch, write files to disk, stage, commit, push, checkout back. This is fragile (requires cleanup on failure) and creates race conditions when multiple sessions share a worktree. Phase 1 of Objective #7813 already converted 3 other call sites to use `commit_files_to_branch` (a git plumbing operation that commits directly to a branch ref without touching the working tree). Node 2.2 applies the same pattern to the submit pipeline.

**Target functions:**
1. `_create_branch_and_pr` (line 685) - creates impl-context files, commits, pushes, creates draft PR
2. "Branch-exists-but-no-PR" path in `_submit_single_issue` (line 864) - adds empty placeholder commit, pushes, creates PR

**Checkouts eliminated:** 4 explicit `checkout_branch` calls at lines 715, 823, 877, 951, plus 1 redundant caller checkout at line 968.

## Phase 1: Add `build_impl_context_files` helper

**File:** `packages/erk-shared/src/erk_shared/impl_context.py`

Add a new function that returns impl-context content as a `dict[str, str]` (for use with `commit_files_to_branch`) without writing to the filesystem:

```python
def build_impl_context_files(
    plan_content: str,
    plan_id: str,
    url: str,
    *,
    provider: str,
    objective_id: int | None,
    now_iso: str,
) -> dict[str, str]:
```

Returns:
```python
{
    f"{IMPL_CONTEXT_DIR}/plan.md": plan_content,
    f"{IMPL_CONTEXT_DIR}/ref.json": json.dumps({...}, indent=2),
}
```

Same ref.json structure as `create_impl_context` (provider, plan_id, url, created_at, synced_at, labels, objective_id). Note: no `repo_root` parameter needed since there are no filesystem operations.

## Phase 2: Refactor `_create_branch_and_pr`

**File:** `src/erk/cli/commands/submit.py`

### Changes to `_create_branch_and_pr` (lines 685-825):

1. **Remove initial checkout** (line 715): `ctx.branch_manager.checkout_branch(repo.root, branch_name)`

2. **Remove filesystem impl-context operations** (lines 725-739): Remove calls to `impl_context_exists`, `remove_impl_context`, `create_impl_context`. Replace with `build_impl_context_files`.

3. **Replace stage+commit with plumbing** (lines 742-743): Replace `stage_files` + `commit` with:
   ```python
   files = build_impl_context_files(
       plan_content=plan.body,
       plan_id=str(issue_number),
       url=issue.url,
       provider="github",
       objective_id=plan.objective_id,
       now_iso=ctx.time.now().isoformat(),
   )
   ctx.git.commit.commit_files_to_branch(
       repo.root,
       branch=branch_name,
       files=files,
       message=f"Add plan for issue #{issue_number}",
   )
   ```

4. **Graphite linking** (lines 801-811): Wrap in a targeted checkout scope since `gt submit` operates on the current stack:
   ```python
   if ctx.branch_manager.is_graphite_managed():
       user_output("Linking PR with Graphite...")
       ctx.branch_manager.checkout_branch(repo.root, branch_name)
       submit_result = ctx.branch_manager.submit_branch(repo.root, branch_name)
       ctx.branch_manager.checkout_branch(repo.root, original_branch)
       # ... error handling ...
   ```

5. **Remove final checkout** (line 823): `ctx.branch_manager.checkout_branch(repo.root, original_branch)` - replaced by Graphite-specific restore above or removed entirely for non-Graphite paths.

### Changes to callers in `_submit_single_issue`:

1. **"Branch exists locally" path** (lines 957-980):
   - Remove checkout at line 968: `ctx.branch_manager.checkout_branch(repo.root, branch_name)`
   - Remove `branch_rollback` context manager wrapper (lines 971, 980)

2. **"Create new branch" path** (lines 1001-1019):
   - `create_branch` already creates ref without checkout (confirmed in docstring) - keep as-is
   - Remove `branch_rollback` context manager wrapper (lines 1010, 1019)

## Phase 3: Refactor "branch-exists-but-no-PR" path

**File:** `src/erk/cli/commands/submit.py` (lines 864-951)

1. **Remove checkout** (line 877): `ctx.branch_manager.checkout_branch(repo.root, branch_name)`

2. **Replace empty commit with plumbing** (lines 880-883):
   ```python
   ctx.git.commit.commit_files_to_branch(
       repo.root,
       branch=branch_name,
       files={},
       message=f"[erk-plan] Initialize implementation for issue #{issue_number}",
   )
   ```
   Note: `commit_files_to_branch` with empty `files={}` creates an empty commit (same tree as parent, different commit hash) - equivalent to `git commit --allow-empty`.

3. **Graphite linking** (lines 929-939): Same pattern as Phase 2 - wrap in targeted checkout scope.

4. **Remove final checkout** (line 951): `ctx.branch_manager.checkout_branch(repo.root, original_branch)` - replaced by Graphite-specific restore.

## Phase 4: Clean up dead code

**File:** `src/erk/cli/commands/submit.py`

1. **Remove `branch_rollback` context manager** (lines 73-87): Only used at lines 971 and 1010, both removed. Delete function and import of `contextmanager`/`Iterator` if no longer needed.

2. **Clean up imports** (lines 45-49): Remove `create_impl_context`, `impl_context_exists`, `remove_impl_context` from imports. Add `build_impl_context_files`.

3. **Remove `IMPL_CONTEXT_DIR` import** (line 52) if no longer used directly (now encapsulated in `build_impl_context_files`). Check usage first.

## Phase 5: Update tests

**File:** `tests/commands/plan/test_submit.py`

### Rewrite `test_submit_issue_plan_cleans_up_stale_impl_context_folder` (line 537):

- Current test creates a stale `.erk/impl-context/` folder on disk and verifies it's cleaned up
- After change: filesystem is not touched, so this test scenario no longer applies
- Rewrite as `test_submit_issue_plan_uses_plumbing_commit`:
  - Verify `fake_git.commit.branch_commits` has 1 entry
  - Verify `branch_commits[0].files` contains `".erk/impl-context/plan.md"` and `".erk/impl-context/ref.json"`
  - Verify `branch_commits[0].branch` matches expected branch name
  - Verify no checkouts occurred (no checkout_branch calls for the plan branch)

### Verify existing tests still pass:

- `test_submit_succeeds_when_parent_branch_tracked` - should work since FakeGit handles `commit_files_to_branch`
- `test_submit_updates_pr_body_with_workflow_run_link` - should work (PR body logic unchanged)
- `test_submit_exits_cleanly_when_parent_branch_untracked` - should work (error path is before commit)
- `test_submit_draft_pr_plan_cleans_up_stale_impl_context_folder` - different code path (draft PR backend), unaffected
- `test_submit_draft_pr_plan_triggers_workflow_with_draft_pr_backend` - unaffected

## Files to modify

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/impl_context.py` | Add `build_impl_context_files` function |
| `src/erk/cli/commands/submit.py` | Core refactoring: plumbing commits, remove checkouts |
| `tests/commands/plan/test_submit.py` | Update/rewrite tests for plumbing behavior |

## Verification

1. Run unit tests: `pytest tests/commands/plan/test_submit.py`
2. Run integration tests: `pytest tests/integration/test_real_git_commit_ops.py` (verify plumbing operations)
3. Run type checker: `ty check src/erk/cli/commands/submit.py packages/erk-shared/src/erk_shared/impl_context.py`
4. Run full fast-ci: `make fast-ci`
