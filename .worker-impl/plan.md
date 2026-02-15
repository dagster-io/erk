# Fix one-shot command to restore original branch

## Context

The `erk one-shot` command currently leaves the user on the newly created one-shot branch after triggering the autonomous workflow. This differs from `erk plan submit`, which correctly restores the original branch after creating a PR. This inconsistent behavior is confusing - users expect to be returned to their original branch after the command completes.

**Current behavior:**
1. User is on `master`
2. Run `erk one-shot "some task"`
3. Command creates `oneshot-some-task-02-15-0447` branch
4. Command pushes, creates PR, triggers workflow
5. User is left on `oneshot-some-task-02-15-0447` ❌

**Expected behavior:**
1. User is on `master`
2. Run `erk one-shot "some task"`
3. Command creates branch, pushes, creates PR, triggers workflow
4. User is returned to `master` ✅

## Implementation Plan

### 1. Capture original branch before operations

**File:** `src/erk/cli/commands/one_shot.py`

After line 99 (after dry-run check, before branch operations), add original branch capture with detached HEAD validation:

```python
# Save current branch for restoration after workflow trigger
original_branch = ctx.git.branch.get_current_branch(repo.root)
if original_branch is None:
    user_output(
        click.style("Error: ", fg="red")
        + "Not on a branch (detached HEAD state). Cannot submit from here."
    )
    raise SystemExit(1)
```

**Rationale:** Match the pattern from `plan submit` (lines 908-914 in `submit.py`). Prevents confusing behavior if user is in detached HEAD state.

### 2. Standardize checkout to use branch_manager

**File:** `src/erk/cli/commands/one_shot.py`

At line 133, change:
```python
ctx.git.branch.checkout_branch(repo.root, branch_name)
```

To:
```python
ctx.branch_manager.checkout_branch(repo.root, branch_name)
```

**Rationale:** `one_shot.py` is the ONLY command file that uses `ctx.git.branch.checkout_branch()` directly. All 29 other command files use `ctx.branch_manager.checkout_branch()`. This standardizes the approach and ensures compatibility with both Graphite and plain Git modes.

### 3. Add try/finally for branch restoration

**File:** `src/erk/cli/commands/one_shot.py`

Wrap lines 130-174 (branch creation through workflow trigger) in a try/finally block:

```python
# Create branch from trunk
user_output("Creating branch...")
ctx.git.branch.create_branch(repo.root, branch_name, trunk, force=False)

try:
    ctx.branch_manager.checkout_branch(repo.root, branch_name)

    # Make empty commit
    ctx.git.commit.commit(repo.root, f"One-shot: {instruction}")

    # Push to remote
    user_output("Pushing to remote...")
    push_result = ctx.git.remote.push_to_remote(
        repo.root, "origin", branch_name, set_upstream=True, force=False
    )
    if isinstance(push_result, PushError):
        Ensure.invariant(False, f"Failed to push branch: {push_result.message}")

    # Create draft PR
    user_output("Creating draft PR...")
    pr_number = ctx.github.create_pr(
        repo.root,
        branch_name,
        pr_title,
        f"Autonomous one-shot execution.\n\n**Instruction:** {instruction}",
        trunk,
        draft=True,
    )
    user_output(f"Created draft PR #{pr_number}")

    # Build workflow inputs
    inputs: dict[str, str] = {
        "instruction": instruction,
        "branch_name": branch_name,
        "pr_number": str(pr_number),
        "submitted_by": submitted_by,
    }
    if model is not None:
        inputs["model_name"] = model

    # Trigger workflow
    user_output("Triggering one-shot workflow...")
    run_id = ctx.github.trigger_workflow(
        repo_root=repo.root,
        workflow=ONE_SHOT_WORKFLOW,
        inputs=inputs,
    )

    # Restore original branch after successful workflow trigger
    ctx.branch_manager.checkout_branch(repo.root, original_branch)

finally:
    # Always ensure we're back on original branch, even on error
    current = ctx.git.branch.get_current_branch(repo.root)
    if current != original_branch:
        user_output(click.style("Restoring original branch...", fg="yellow"))
        ctx.branch_manager.checkout_branch(repo.root, original_branch)
```

**Key points:**
- Branch restoration happens immediately after successful workflow trigger (success path)
- `finally` block provides safety net for any exceptions during operations
- Simpler than `plan submit`'s `branch_rollback` context manager (one-shot doesn't have complex branch reuse logic)

### 4. Update tests to verify branch restoration

**File:** `tests/commands/one_shot/test_one_shot.py`

#### 4a. Update existing test

Add assertion to `test_one_shot_happy_path()` after line 66:

```python
# Verify we're back on original branch
assert git.current_branch == "main"
```

#### 4b. Add error handling test

```python
def test_one_shot_restores_branch_on_error() -> None:
    """Test that original branch is restored even if workflow trigger fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Configure GitHub to fail workflow trigger
        github = FakeGitHub(authenticated=True, fail_workflow_trigger=True)
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            cli,
            ["one-shot", "fix the import in config.py"],
            obj=ctx,
        )

        # Verify command failed
        assert result.exit_code != 0

        # Verify we're back on original branch despite error
        assert git.current_branch == "main"
```

#### 4c. Add detached HEAD test

```python
def test_one_shot_rejects_detached_head() -> None:
    """Test that one-shot rejects execution from detached HEAD."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branch=None,  # Detached HEAD
            trunk_branches={env.cwd: "main"},
        )
        github = FakeGitHub(authenticated=True)

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            cli,
            ["one-shot", "fix something"],
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "detached HEAD" in result.output
        assert len(git.created_branches) == 0  # No branch created
```

## Edge Cases Handled

1. **Detached HEAD**: Rejected early with clear error message (matches `plan submit`)
2. **Push failure**: Branch restored via finally block before `Ensure.invariant` raises
3. **PR creation failure**: Branch restored via finally block before exception propagates
4. **Workflow trigger failure**: Branch restored via finally block before exception propagates
5. **Already on a one-shot branch**: Works correctly - restores to the original one-shot branch
6. **Dry-run mode**: No branch changes, no restoration needed (early return at line 128)

## Critical Files

- **src/erk/cli/commands/one_shot.py** - Primary changes (capture branch, standardize checkout, add try/finally)
- **tests/commands/one_shot/test_one_shot.py** - Test updates (add assertions and new tests)
- **src/erk/cli/commands/submit.py** - Reference for branch capture pattern (lines 908-914)

## Verification

### Manual testing

1. **Happy path:**
   ```bash
   cd /path/to/erk
   git checkout master
   erk one-shot "test task"
   git branch  # Should show * master
   ```

2. **Error handling:**
   - Disconnect network while running command
   - Verify restoration happens even on error

3. **Detached HEAD:**
   ```bash
   git checkout HEAD~1  # Enter detached HEAD
   erk one-shot "test task"  # Should fail with clear error
   ```

### Automated tests

Run the test suite:
```bash
pytest tests/commands/one_shot/test_one_shot.py -v
```

All three tests should pass:
- `test_one_shot_happy_path` - with new assertion
- `test_one_shot_restores_branch_on_error` - new test
- `test_one_shot_rejects_detached_head` - new test