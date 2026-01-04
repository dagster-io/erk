"""Tests for erk plan start command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.plan.start_cmd import plan_start
from erk.core.worktree_pool import PoolState, SlotAssignment, save_pool_state
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env

# Slot Assignment Tests


def test_plan_start_assigns_slot() -> None:
    """Test that plan start assigns a slot and creates worktree."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        result = runner.invoke(plan_start, ["--script"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Assigned" in result.output
        assert "erk-managed-wt-" in result.output

        # Verify worktree was created
        assert len(git.added_worktrees) == 1


def test_plan_start_with_custom_name() -> None:
    """Test plan start with custom branch name."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        result = runner.invoke(plan_start, ["--name", "my-feature", "--script"], obj=ctx)

        assert result.exit_code == 0
        assert "my-feature" in result.output


def test_plan_start_generates_timestamp_name() -> None:
    """Test that plan start generates timestamp-based name when none provided."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        result = runner.invoke(plan_start, ["--script"], obj=ctx)

        assert result.exit_code == 0
        # Should contain "planning-" prefix in output
        assert "planning-" in result.output


# Interactive Mode Tests


def test_plan_start_interactive_calls_executor() -> None:
    """Verify interactive mode calls executor.execute_interactive with empty command."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        # Interactive mode is the default (no --script flag)
        result = runner.invoke(plan_start, obj=ctx)

        assert result.exit_code == 0

        # Verify execute_interactive was called with empty command
        assert len(executor.interactive_calls) == 1
        worktree_path, dangerous, command, target_subpath, model = executor.interactive_calls[0]
        assert "erk-managed-wt-" in str(worktree_path)
        assert dangerous is False
        assert command == ""  # No slash command for planning
        assert model is None


def test_plan_start_interactive_with_dangerous() -> None:
    """Verify interactive mode passes dangerous flag to executor."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        result = runner.invoke(plan_start, ["--dangerous"], obj=ctx)

        assert result.exit_code == 0

        # Verify dangerous flag was passed
        assert len(executor.interactive_calls) == 1
        _, dangerous, _, _, _ = executor.interactive_calls[0]
        assert dangerous is True


def test_plan_start_interactive_with_model() -> None:
    """Verify model is passed to executor in interactive mode."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        result = runner.invoke(plan_start, ["--model", "opus"], obj=ctx)

        assert result.exit_code == 0

        # Verify model was passed
        assert len(executor.interactive_calls) == 1
        _, _, _, _, model = executor.interactive_calls[0]
        assert model == "opus"


def test_plan_start_interactive_fails_without_claude() -> None:
    """Verify interactive mode fails gracefully when Claude CLI not available."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        executor = FakeClaudeExecutor(claude_available=False)
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        result = runner.invoke(plan_start, obj=ctx)

        assert result.exit_code != 0
        assert "Claude CLI not found" in result.output


# Script Mode Tests


def test_plan_start_script_mode_generates_script() -> None:
    """Test that --script generates activation script."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(plan_start, ["--script"], obj=ctx)

        assert result.exit_code == 0

        # Verify script path is output
        assert result.stdout
        script_path = Path(result.stdout.strip())
        assert script_path.exists()

        # Verify script contains Claude command without slash command
        script_content = script_path.read_text(encoding="utf-8")
        assert "claude --permission-mode acceptEdits" in script_content


def test_plan_start_script_with_dangerous() -> None:
    """Test that --dangerous adds flag to generated script."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(plan_start, ["--dangerous", "--script"], obj=ctx)

        assert result.exit_code == 0

        script_path = Path(result.stdout.strip())
        script_content = script_path.read_text(encoding="utf-8")
        assert "--dangerously-skip-permissions" in script_content


def test_plan_start_script_with_model() -> None:
    """Test that --model is included in generated script."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(plan_start, ["--script", "--model", "sonnet"], obj=ctx)

        assert result.exit_code == 0

        script_path = Path(result.stdout.strip())
        script_content = script_path.read_text(encoding="utf-8")
        assert "--model sonnet" in script_content


# Dry Run Tests


def test_plan_start_dry_run() -> None:
    """Test dry-run mode shows what would be done."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(plan_start, ["--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output
        assert "Would assign to slot" in result.output
        assert "Would launch Claude" in result.output

        # Verify no worktree was created
        assert len(git.added_worktrees) == 0


# Pool Full Tests


def test_plan_start_force_flag_unassigns_oldest() -> None:
    """Test that --force auto-unassigns oldest slot when pool is full."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo = env.repo
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        # Create pool with all 4 slots assigned
        pool_size = 4
        assignments = tuple(
            SlotAssignment(
                slot_name=f"erk-managed-wt-{i:02d}",
                branch_name=f"existing-branch-{i}",
                assigned_at=f"2024-01-0{i}T00:00:00+00:00",
                worktree_path=repo.worktrees_dir / f"erk-managed-wt-{i:02d}",
            )
            for i in range(1, pool_size + 1)
        )
        full_state = PoolState(
            version="1.0",
            pool_size=pool_size,
            slots=(),
            assignments=assignments,
        )
        save_pool_state(repo.pool_json_path, full_state)

        result = runner.invoke(plan_start, ["--force", "--script"], obj=ctx)

        assert result.exit_code == 0
        assert "Unassigned" in result.output
        assert "existing-branch-1" in result.output  # Oldest assignment


def test_plan_start_existing_branch_reuses_slot() -> None:
    """Test that if branch is already assigned, we reuse that slot."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo = env.repo
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "my-feature"]},
            default_branches={env.cwd: "main"},
        )
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        # Create pool with my-feature already assigned
        wt_path = repo.worktrees_dir / "erk-managed-wt-01"
        wt_path.mkdir(parents=True, exist_ok=True)
        existing_state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(),
            assignments=(
                SlotAssignment(
                    slot_name="erk-managed-wt-01",
                    branch_name="my-feature",
                    assigned_at="2024-01-01T00:00:00+00:00",
                    worktree_path=wt_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, existing_state)

        result = runner.invoke(plan_start, ["--name", "my-feature", "--script"], obj=ctx)

        assert result.exit_code == 0
        assert "already assigned" in result.output
        # Should not create new worktree
        assert len(git.added_worktrees) == 0


# Graphite Integration Tests


def test_plan_start_tracks_branch_with_graphite() -> None:
    """Test that new branches are tracked via Graphite when enabled."""
    from erk_shared.gateway.graphite.fake import FakeGraphite

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        fake_graphite = FakeGraphite()
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=fake_graphite,
            claude_executor=executor,
            use_graphite=True,
        )

        result = runner.invoke(plan_start, ["--script"], obj=ctx)

        assert result.exit_code == 0

        # Verify track_branch was called
        assert len(fake_graphite.track_branch_calls) == 1
        _, branch_name, parent_branch = fake_graphite.track_branch_calls[0]
        assert "planning-" in branch_name
        assert parent_branch == "main"


def test_plan_start_stacks_on_feature_branch() -> None:
    """When on feature branch with Graphite, stack on current branch."""
    from erk_shared.gateway.graphite.fake import FakeGraphite

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},  # On feature branch
        )
        fake_graphite = FakeGraphite()
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=fake_graphite,
            claude_executor=executor,
            use_graphite=True,
        )

        result = runner.invoke(plan_start, ["--script"], obj=ctx)

        assert result.exit_code == 0

        # Verify parent_branch is feature-branch (stacking)
        assert len(fake_graphite.track_branch_calls) == 1
        _, branch_name, parent_branch = fake_graphite.track_branch_calls[0]
        assert parent_branch == "feature-branch"


# Relative Path Preservation Tests


def test_plan_start_preserves_relative_path() -> None:
    """Verify interactive mode passes relative path when run from subdirectory."""
    import os

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create a subdirectory structure
        subdir = env.cwd / "src" / "lib"
        subdir.mkdir(parents=True)

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main", is_root=True)]},
        )
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor, cwd=subdir)

        # Change to subdirectory before invoking
        os.chdir(subdir)

        result = runner.invoke(plan_start, obj=ctx)

        assert result.exit_code == 0

        # Verify target_subpath is passed
        assert len(executor.interactive_calls) == 1
        _, _, _, target_subpath, _ = executor.interactive_calls[0]
        assert target_subpath == Path("src/lib")
