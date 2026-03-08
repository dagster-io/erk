# Handle restack-in-progress state in `erk pr rebase`

## Context

When `gt restack` hits merge conflicts, the repository enters a detached HEAD state with an active rebase-in-progress. In this state, `git rev-parse --abbrev-ref HEAD` returns a commit hash (not a branch name), so `get_current_branch()` returns `None`.

Currently, `erk pr rebase` checks Graphite tracking *before* checking for rebase-in-progress, which means the command fails with:

```
Error: Current branch is not tracked by Graphite. Track it with: gt track
```

This is incorrect. The expected behavior is that `erk pr rebase` should detect the rebase-in-progress state (even on a detached HEAD) and skip straight to the conflict resolution flow — launching Claude with `/erk:pr-rebase`.

## Changes

### 1. Modify `src/erk/cli/commands/pr/rebase_cmd.py`

**What to change:** Restructure the Graphite-enabled path to check for rebase-in-progress *before* checking branch tracking.

The current logic (lines 94-113) is:

```python
if graphite_enabled:
    branch = ctx.git.branch.get_current_branch(cwd)
    Ensure.invariant(
        branch is not None and ctx.graphite.is_branch_tracked(ctx.repo_root, branch),
        "Current branch is not tracked by Graphite. Track it with: gt track",
    )
    click.echo(click.style("Restacking with Graphite...", fg="yellow"))
    result = subprocess.run(...)
    ...
```

Replace with logic that checks for rebase-in-progress first:

```python
if graphite_enabled:
    # If a rebase is already in progress (e.g., gt restack hit conflicts),
    # skip tracking check and go straight to conflict resolution
    if ctx.git.rebase.is_rebase_in_progress(cwd):
        click.echo(click.style("Restack in progress. Launching Claude...", fg="yellow"))
    else:
        branch = ctx.git.branch.get_current_branch(cwd)
        Ensure.invariant(
            branch is not None and ctx.graphite.is_branch_tracked(ctx.repo_root, branch),
            "Current branch is not tracked by Graphite. Track it with: gt track",
        )
        click.echo(click.style("Restacking with Graphite...", fg="yellow"))
        result = subprocess.run(
            ["gt", "restack", "--no-interactive"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            click.echo(click.style("Restack complete!", fg="green", bold=True))
            return
        if not ctx.git.rebase.is_rebase_in_progress(cwd):
            raise click.ClickException(f"gt restack failed:\n{result.stderr}")
        click.echo(click.style("Restack hit conflicts. Launching Claude...", fg="yellow"))
```

The rest of the function (lines 129-150 — conflict display, confirmation prompt, and Claude launch) remains unchanged.

**Key design decision:** The message says "Restack in progress" (not "Rebase in progress") because in the Graphite-enabled path, the rebase was initiated by `gt restack`. The non-Graphite path already has its own "Rebase in progress" message at line 127.

### 2. Add test in `tests/commands/pr/test_rebase.py`

Add a new test function `test_pr_rebase_graphite_restack_in_progress_launches_tui` that covers the scenario where:
- Graphite is enabled
- A rebase is already in progress (simulating `gt restack` conflict)
- Current branch is `None` (detached HEAD state)
- The command should bypass the tracking check and launch Claude

Use this test setup pattern (following existing test patterns in the file):

```python
def test_pr_rebase_graphite_restack_in_progress_launches_tui() -> None:
    """Test that gt restack in-progress state bypasses tracking check and launches Claude."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={},  # No current branch = detached HEAD (get_current_branch returns None)
            rebase_in_progress=True,
            conflicted_files=["docs/learned/cli/tripwires.md", "docs/learned/tripwires-index.md"],
        )

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["rebase", "--dangerous"], obj=ctx, input="y\n")

        assert result.exit_code == 0
        assert "Restack in progress" in result.output
        assert "Launch Claude to resolve conflicts?" in result.output
        assert len(executor.interactive_calls) == 1
        call = executor.interactive_calls[0]
        assert call[2] == "/erk:pr-rebase"  # command
```

**Important detail about `current_branches`:** The FakeGit constructor uses `current_branches` as a dict mapping `cwd -> branch_name`. When the cwd key is absent, `get_current_branch` returns `None`, simulating detached HEAD. Verify this matches FakeGit's actual implementation before coding.

To confirm, check `FakeGit` or `FakeGitBranchOps` for how `get_current_branch` handles missing keys. It should return `None` for unmapped paths.

### 3. Add test for tracked branch with rebase-in-progress (Graphite enabled)

Also add a test for the case where Graphite is enabled, a rebase IS in progress, but `get_current_branch` still returns a valid branch name (some rebases don't detach HEAD). This ensures the early-exit path works regardless of branch state:

```python
def test_pr_rebase_graphite_restack_in_progress_with_branch_launches_tui() -> None:
    """Test restack in-progress with valid branch name still bypasses tracking check."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            rebase_in_progress=True,
            conflicted_files=["file.py"],
        )

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["rebase", "--dangerous"], obj=ctx, input="y\n")

        assert result.exit_code == 0
        assert "Restack in progress" in result.output
        assert len(executor.interactive_calls) == 1
```

## Files NOT Changing

- `.claude/commands/erk/pr-rebase.md` — The slash command itself handles conflict resolution generically; no changes needed.
- `packages/erk-shared/src/erk_shared/gateway/git/` — No changes to git gateway. `is_rebase_in_progress` and `get_current_branch` already behave correctly.
- `src/erk/cli/ensure.py` — No changes needed.
- `src/erk/core/prompt_executor.py` — No changes needed.
- `src/erk/capabilities/workflows/pr_rebase.py` — This is the GitHub Actions capability, unrelated.
- `src/erk/cli/commands/launch_cmd.py` — Remote launch is unrelated.

## Verification

1. Run the existing test suite for rebase: `pytest tests/commands/pr/test_rebase.py -v` — all existing tests must pass.
2. Run the new tests: both `test_pr_rebase_graphite_restack_in_progress_launches_tui` and `test_pr_rebase_graphite_restack_in_progress_with_branch_launches_tui` must pass.
3. Run type checking: `ty check src/erk/cli/commands/pr/rebase_cmd.py`
4. Run lint: `ruff check src/erk/cli/commands/pr/rebase_cmd.py tests/commands/pr/test_rebase.py`

## Implementation Notes

- The `build_workspace_test_context` helper must include Graphite (not disabled) for the tests to exercise the Graphite-enabled path. Check whether it returns a Graphite-enabled or disabled context by default. If it returns `GraphiteDisabled`, the test will need to explicitly provide a `FakeGraphite` via the builder. Look at the Graphite-related test setup in existing tests (there may be tests in `test_rebase_remote.py` or other files that construct a Graphite-enabled context).
- The FakeGit's `current_branches` dict behavior when key is missing: verify that `FakeGitBranchOps.get_current_branch` returns `None` for unmapped cwds. If it raises `KeyError` instead, use an explicit `current_branches={env.cwd: None}` pattern instead.