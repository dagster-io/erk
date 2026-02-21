# Fix plan-save race condition with git plumbing

## Context

When `plan_save.py` creates a draft PR plan, it temporarily checks out the plan branch in the root worktree to commit files (lines 165-189). This creates a race condition when multiple Claude Code sessions share the same root worktree:

1. Session A: plan-save checks out `planned/branch-a`, captures `start_point = master`
2. Session B: plan-save starts, captures `start_point = planned/branch-a` (A hasn't restored yet)
3. Session A: finally block restores to `master`
4. Session B: finally block restores to `planned/branch-a` (its captured start_point)
5. Root worktree is now stuck on `planned/branch-a`

The fix: use git plumbing commands (`hash-object`, `read-tree`, `update-index`, `write-tree`, `commit-tree`, `update-ref`) to create the plan commit directly on the branch without ever checking it out. This eliminates the checkout/restore dance entirely.

Note: `GraphiteBranchManager.create_branch()` also temporarily checks out for `gt track`, but that window is very short (local operation only). The plan_save window includes a network push, making it orders of magnitude more likely to race. This plan addresses the plan_save checkout only.

## Implementation

### 1. Add `commit_files_to_branch` to `GitCommitOps` ABC

**File:** `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/abc.py`

Add new abstract method to the Mutation Operations section:

```python
@abstractmethod
def commit_files_to_branch(
    self,
    cwd: Path,
    *,
    branch: str,
    files: dict[str, str],
    message: str,
) -> None:
    """Create a commit on a branch without checking it out.

    Uses git plumbing commands to create a commit directly on the target
    branch without modifying the working tree or HEAD. This avoids race
    conditions when multiple sessions share the same worktree.

    Args:
        cwd: Repository root directory
        branch: Target branch name (must exist)
        files: Mapping of relative file paths to string content
        message: Commit message
    """
    ...
```

### 2. Implement in `RealGitCommitOps`

**File:** `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/real.py`

Add `import os`, `import tempfile` at top.

Implementation using a temporary index file:

```python
def commit_files_to_branch(
    self,
    cwd: Path,
    *,
    branch: str,
    files: dict[str, str],
    message: str,
) -> None:
    """Create a commit on a branch using git plumbing (no checkout)."""
    # Get parent commit SHA
    parent_sha = run_subprocess_with_context(
        cmd=["git", "rev-parse", branch],
        operation_context=f"resolve branch {branch}",
        cwd=cwd,
    ).stdout.strip()

    # Create temporary index file
    tmp_fd, tmp_index = tempfile.mkstemp(suffix=".idx", prefix="erk-plan-")
    os.close(tmp_fd)
    try:
        env = os.environ.copy()
        env["GIT_INDEX_FILE"] = tmp_index

        # Read parent tree into temp index
        run_subprocess_with_context(
            cmd=["git", "read-tree", parent_sha],
            operation_context="read parent tree into temp index",
            cwd=cwd,
            env=env,
        )

        # Hash each file and add to temp index
        for path, content in files.items():
            blob_sha = run_subprocess_with_context(
                cmd=["git", "hash-object", "-w", "--stdin"],
                operation_context=f"hash content for {path}",
                cwd=cwd,
                input=content,
            ).stdout.strip()

            run_subprocess_with_context(
                cmd=["git", "update-index", "--add", "--cacheinfo", f"100644,{blob_sha},{path}"],
                operation_context=f"add {path} to temp index",
                cwd=cwd,
                env=env,
            )

        # Write tree from temp index
        tree_sha = run_subprocess_with_context(
            cmd=["git", "write-tree"],
            operation_context="write tree from temp index",
            cwd=cwd,
            env=env,
        ).stdout.strip()

        # Create commit object
        commit_sha = run_subprocess_with_context(
            cmd=["git", "commit-tree", tree_sha, "-p", parent_sha, "-m", message],
            operation_context="create commit on branch",
            cwd=cwd,
        ).stdout.strip()

        # Update branch ref
        run_subprocess_with_context(
            cmd=["git", "update-ref", f"refs/heads/{branch}", commit_sha],
            operation_context=f"update ref for {branch}",
            cwd=cwd,
        )
    finally:
        Path(tmp_index).unlink(missing_ok=True)
```

### 3. Implement in `FakeGitCommitOps`

**File:** `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/fake.py`

Add a new frozen dataclass for tracking and implement the method:

```python
@dataclass(frozen=True)
class BranchCommitRecord:
    """Record of a direct-to-branch commit (no checkout)."""
    cwd: Path
    branch: str
    files: dict[str, str]
    message: str
```

Add `_branch_commits: list[BranchCommitRecord]` mutation tracking list. Add a `branch_commits` property. Add to `link_mutation_tracking` signature. Implement the method to record the operation.

### 4. Implement in `DryRunGitCommitOps`

**File:** `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/dry_run.py`

Add no-op:

```python
def commit_files_to_branch(self, cwd: Path, *, branch: str, files: dict[str, str], message: str) -> None:
    pass
```

### 5. Implement in `PrintingGitCommitOps`

**File:** `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/printing.py`

Add print-and-delegate:

```python
def commit_files_to_branch(self, cwd: Path, *, branch: str, files: dict[str, str], message: str) -> None:
    file_list = ", ".join(files.keys())
    self._emit(self._format_command(f"git plumbing: commit [{file_list}] to {branch}"))
    self._wrapped.commit_files_to_branch(cwd, branch=branch, files=files, message=message)
```

### 6. Update `FakeGit` parent class

**File:** `packages/erk-shared/src/erk_shared/gateway/git/fake.py`

Add `branch_commits` tracking list and link it to `FakeGitCommitOps` via `link_mutation_tracking`.

### 7. Refactor `_save_as_draft_pr` in `plan_save.py`

**File:** `src/erk/cli/commands/exec/scripts/plan_save.py`

Replace lines 162-189 (the checkout/try/finally block) with:

```python
# Commit plan files directly to branch (no checkout needed)
git.commit.commit_files_to_branch(
    repo_root,
    branch=branch_name,
    files={
        f"{IMPL_CONTEXT_DIR}/plan.md": plan_content,
        f"{IMPL_CONTEXT_DIR}/ref.json": json.dumps(ref_data, indent=2),
    },
    message=f"Add plan: {title}",
)
git.remote.push_to_remote(cwd, "origin", branch_name, set_upstream=True, force=False)
```

This eliminates the `checkout_branch` calls on lines 165 and 189, the `mkdir`/`write_text` file operations, and the `stage_files`/`commit` calls. The `ref_data` dict construction (lines 173-180) moves above this block.

### 8. Update tests

**File:** `tests/unit/cli/commands/exec/scripts/test_plan_save.py`

- **`test_draft_pr_restores_original_branch`** (line 220): Rename to `test_draft_pr_does_not_checkout_branch`. Verify that `fake_git.checked_out_branches` has only 2 entries (from `branch_manager.create_branch`), not 4. The plan commit no longer causes any checkouts.

- **`test_draft_pr_commits_plan_file`** (line 238): Update to verify via `fake_git.branch_commits` instead of checking filesystem for plan.md/ref.json. The files are no longer written to the working tree.

- **`test_draft_pr_objective_issue_metadata`** (line 197): Update to verify `objective_id` via `fake_git.branch_commits[0].files` instead of reading ref.json from filesystem.

### 9. Update documentation

**File:** `docs/learned/architecture/plan-save-branch-restoration.md`

Update to reflect that plan-save no longer checks out branches. The try/finally pattern is replaced by git plumbing. Document the new approach and why it's race-condition-free.

## Files to modify

1. `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/abc.py` - Add abstract method
2. `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/real.py` - Real implementation
3. `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/fake.py` - Fake + tracking
4. `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/dry_run.py` - No-op
5. `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/printing.py` - Print wrapper
6. `packages/erk-shared/src/erk_shared/gateway/git/fake.py` - FakeGit linkage
7. `src/erk/cli/commands/exec/scripts/plan_save.py` - Use new method
8. `tests/unit/cli/commands/exec/scripts/test_plan_save.py` - Update tests
9. `docs/learned/architecture/plan-save-branch-restoration.md` - Update docs

## Verification

1. Run unit tests: `uv run pytest tests/unit/cli/commands/exec/scripts/test_plan_save.py -v`
2. Run fake tests: `uv run pytest tests/unit/fakes/ -v`
3. Type check: `uv run ty check`
4. Integration test: run `erk exec plan-save --format display` with a real plan to verify the plumbing commands work end-to-end
5. Verify no checkout occurs by checking `git log --oneline` on the plan branch shows the commit, while `git branch` shows we never left master
