"""Tests for erk pr sync-divergence command."""

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.context.types import GlobalConfig
from erk_shared.git.abc import BranchDivergence
from erk_shared.git.fake import FakeGit
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_sync_divergence_success() -> None:
    """Test successful sync when branch is diverged."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            remote_branches={env.cwd: ["origin/feature-branch", "origin/main"]},
            branch_divergence={
                (env.cwd, "feature-branch", "origin"): BranchDivergence(
                    is_diverged=True, ahead=2, behind=3
                )
            },
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["sync-divergence", "--dangerous"], obj=ctx)

        assert result.exit_code == 0
        assert "Branch synced with remote!" in result.output

        # Claude should be invoked for divergence resolution
        assert len(claude_executor.executed_commands) == 1
        command, _, dangerous_flag, _, _ = claude_executor.executed_commands[0]
        assert command == "/erk:sync-divergence"
        assert dangerous_flag is True


def test_pr_sync_divergence_requires_dangerous_flag() -> None:
    """Test that command fails when --dangerous flag is not provided (default config)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            remote_branches={env.cwd: ["origin/feature-branch", "origin/main"]},
            branch_divergence={
                (env.cwd, "feature-branch", "origin"): BranchDivergence(
                    is_diverged=True, ahead=2, behind=3
                )
            },
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["sync-divergence"], obj=ctx)

        assert result.exit_code != 0
        assert "Missing option '--dangerous'" in result.output
        # Verify error message includes config hint
        assert "fix_conflicts_require_dangerous_flag false" in result.output


def test_pr_sync_divergence_skip_dangerous_with_config() -> None:
    """Test that --dangerous flag is not required when config disables requirement."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            remote_branches={env.cwd: ["origin/feature-branch", "origin/main"]},
            branch_divergence={
                (env.cwd, "feature-branch", "origin"): BranchDivergence(
                    is_diverged=True, ahead=2, behind=3
                )
            },
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        # Create GlobalConfig with fix_conflicts_require_dangerous_flag=False
        global_config = GlobalConfig.test(
            env.erk_root,
            fix_conflicts_require_dangerous_flag=False,  # Disable --dangerous requirement
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            claude_executor=claude_executor,
            global_config=global_config,
        )

        # Invoke WITHOUT --dangerous flag
        result = runner.invoke(pr_group, ["sync-divergence"], obj=ctx)

        # Should succeed without --dangerous when config disables requirement
        assert result.exit_code == 0
        assert "Branch synced with remote!" in result.output


def test_pr_sync_divergence_already_in_sync() -> None:
    """Test early exit when no divergence."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            remote_branches={env.cwd: ["origin/feature-branch", "origin/main"]},
            branch_divergence={
                (env.cwd, "feature-branch", "origin"): BranchDivergence(
                    is_diverged=False, ahead=0, behind=0
                )
            },
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["sync-divergence", "--dangerous"], obj=ctx)

        assert result.exit_code == 0
        assert "already in sync" in result.output

        # Claude should NOT be invoked (no divergence to resolve)
        assert len(claude_executor.executed_commands) == 0


def test_pr_sync_divergence_behind_only() -> None:
    """Test fast-forward case (behind but not diverged)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            remote_branches={env.cwd: ["origin/feature-branch", "origin/main"]},
            branch_divergence={
                (env.cwd, "feature-branch", "origin"): BranchDivergence(
                    is_diverged=False, ahead=0, behind=3
                )
            },
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["sync-divergence", "--dangerous"], obj=ctx)

        assert result.exit_code == 0
        assert "behind remote" in result.output
        assert "Fast-forward possible" in result.output


def test_pr_sync_divergence_no_remote_branch() -> None:
    """Test error when no remote tracking branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            remote_branches={env.cwd: ["origin/main"]},  # No origin/feature-branch
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["sync-divergence", "--dangerous"], obj=ctx)

        assert result.exit_code != 0
        assert "No remote tracking branch" in result.output
        assert "origin/feature-branch" in result.output


def test_pr_sync_divergence_detached_head() -> None:
    """Test error when not on a branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: None},  # Detached HEAD
            remote_branches={env.cwd: ["origin/feature-branch", "origin/main"]},
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["sync-divergence", "--dangerous"], obj=ctx)

        assert result.exit_code != 0
        assert "Not on a branch" in result.output


def test_pr_sync_divergence_claude_not_available() -> None:
    """Test error when Claude is not installed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            remote_branches={env.cwd: ["origin/feature-branch", "origin/main"]},
            branch_divergence={
                (env.cwd, "feature-branch", "origin"): BranchDivergence(
                    is_diverged=True, ahead=2, behind=3
                )
            },
        )

        claude_executor = FakeClaudeExecutor(claude_available=False)

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["sync-divergence", "--dangerous"], obj=ctx)

        assert result.exit_code != 0
        assert "Claude CLI is required" in result.output
        assert "claude.com/download" in result.output

        # Verify no command was executed
        assert len(claude_executor.executed_commands) == 0


def test_pr_sync_divergence_aborts_on_semantic_conflict() -> None:
    """Test that command aborts when Claude prompts for user input (semantic conflict)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            remote_branches={env.cwd: ["origin/feature-branch", "origin/main"]},
            branch_divergence={
                (env.cwd, "feature-branch", "origin"): BranchDivergence(
                    is_diverged=True, ahead=2, behind=3
                )
            },
        )

        # Simulate Claude using AskUserQuestion tool (semantic conflict)
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_tool_events=["Using AskUserQuestion..."],
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["sync-divergence", "--dangerous"], obj=ctx)

        # Should fail with semantic conflict message
        assert result.exit_code != 0
        assert "interactive resolution" in result.output


def test_pr_sync_divergence_fails_on_command_error() -> None:
    """Test that command fails when slash command execution fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            remote_branches={env.cwd: ["origin/feature-branch", "origin/main"]},
            branch_divergence={
                (env.cwd, "feature-branch", "origin"): BranchDivergence(
                    is_diverged=True, ahead=2, behind=3
                )
            },
        )

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            command_should_fail=True,
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["sync-divergence", "--dangerous"], obj=ctx)

        assert result.exit_code != 0
        # Error message from FakeClaudeExecutor
        assert "failed" in result.output.lower()


def test_pr_sync_divergence_fails_when_no_work_events() -> None:
    """Test that command fails when Claude completes but produces no work events."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            remote_branches={env.cwd: ["origin/feature-branch", "origin/main"]},
            branch_divergence={
                (env.cwd, "feature-branch", "origin"): BranchDivergence(
                    is_diverged=True, ahead=2, behind=3
                )
            },
        )

        # Simulate Claude completing but emitting no work events
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_no_work_events=True,
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["sync-divergence", "--dangerous"], obj=ctx)

        # Should fail due to no work events
        assert result.exit_code != 0
        assert "without producing any output" in result.output
        assert "check hooks" in result.output
