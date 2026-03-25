"""Tests for erk pr diverge-fix command."""

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.git.abc import BranchDivergence
from tests.fakes.gateway.git import FakeGit
from tests.fakes.tests.prompt_executor import FakePromptExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_diverge_fix_success() -> None:
    """Test successful reconciliation when branch is diverged."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
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

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["diverge-fix", "--dangerous"], obj=ctx)

        assert result.exit_code == 0
        assert "Branch synced with remote!" in result.output

        # Claude should be invoked for divergence resolution
        assert len(executor.executed_commands) == 1
        command, _, dangerous_flag, _, _ = executor.executed_commands[0]
        assert command == "/erk:diverge-fix"
        assert dangerous_flag is True


def test_pr_diverge_fix_succeeds_without_dangerous_flag() -> None:
    """Test that command succeeds without --dangerous when live_dangerously=True (default)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
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

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["diverge-fix"], obj=ctx)

        assert result.exit_code == 0
        assert "Branch synced with remote!" in result.output


def test_pr_diverge_fix_safe_flag_disables_dangerous() -> None:
    """Test that --safe overrides live_dangerously=True and passes dangerous=False."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
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

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["diverge-fix", "--safe"], obj=ctx)

        assert result.exit_code == 0
        assert "Branch synced with remote!" in result.output
        # Verify dangerous=False was passed to executor
        command, _, dangerous_flag, _, _ = executor.executed_commands[0]
        assert command == "/erk:diverge-fix"
        assert dangerous_flag is False


def test_pr_diverge_fix_dangerous_and_safe_mutually_exclusive() -> None:
    """Test that --dangerous and --safe together produce an error."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
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

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["diverge-fix", "--dangerous", "--safe"], obj=ctx)

        assert result.exit_code != 0
        assert "mutually exclusive" in result.output


def test_pr_diverge_fix_live_dangerously_false_runs_safe() -> None:
    """Test that live_dangerously=False makes command run in safe mode by default."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
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

        executor = FakePromptExecutor(available=True)

        global_config = GlobalConfig.test(
            env.erk_root,
            live_dangerously=False,
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            prompt_executor=executor,
            global_config=global_config,
        )

        result = runner.invoke(pr_group, ["diverge-fix"], obj=ctx)

        assert result.exit_code == 0
        assert "Branch synced with remote!" in result.output
        # Verify dangerous=False was passed to executor
        command, _, dangerous_flag, _, _ = executor.executed_commands[0]
        assert command == "/erk:diverge-fix"
        assert dangerous_flag is False


def test_pr_diverge_fix_already_in_sync() -> None:
    """Test early exit when no divergence."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
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

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["diverge-fix", "--dangerous"], obj=ctx)

        assert result.exit_code == 0
        assert "already in sync" in result.output

        # Claude should NOT be invoked (no divergence to resolve)
        assert len(executor.executed_commands) == 0


def test_pr_diverge_fix_behind_only() -> None:
    """Test fast-forward case (behind but not diverged)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
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

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["diverge-fix", "--dangerous"], obj=ctx)

        assert result.exit_code == 0
        assert "behind remote" in result.output
        assert "Fast-forward possible" in result.output


def test_pr_diverge_fix_no_remote_branch() -> None:
    """Test error when no remote tracking branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            remote_branches={env.cwd: ["origin/main"]},  # No origin/feature-branch
        )

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["diverge-fix", "--dangerous"], obj=ctx)

        assert result.exit_code != 0
        assert "No remote tracking branch" in result.output
        assert "origin/feature-branch" in result.output


def test_pr_diverge_fix_detached_head() -> None:
    """Test error when not on a branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: None},  # Detached HEAD
            remote_branches={env.cwd: ["origin/feature-branch", "origin/main"]},
        )

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["diverge-fix", "--dangerous"], obj=ctx)

        assert result.exit_code != 0
        assert "Not on a branch" in result.output


def test_pr_diverge_fix_claude_not_available() -> None:
    """Test error when Claude is not installed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
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

        executor = FakePromptExecutor(available=False)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["diverge-fix", "--dangerous"], obj=ctx)

        assert result.exit_code != 0
        assert "Claude CLI is required" in result.output
        assert "claude.com/download" in result.output

        # Verify no command was executed
        assert len(executor.executed_commands) == 0


def test_pr_diverge_fix_aborts_on_semantic_conflict() -> None:
    """Test that command aborts when Claude prompts for user input (semantic conflict)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
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
        executor = FakePromptExecutor(
            available=True,
            simulated_tool_events=["Using AskUserQuestion..."],
        )

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["diverge-fix", "--dangerous"], obj=ctx)

        # Should fail with semantic conflict message
        assert result.exit_code != 0
        assert "interactive resolution" in result.output


def test_pr_diverge_fix_fails_on_command_error() -> None:
    """Test that command fails when slash command execution fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
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

        executor = FakePromptExecutor(
            available=True,
            command_should_fail=True,
        )

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["diverge-fix", "--dangerous"], obj=ctx)

        assert result.exit_code != 0
        # Error message from FakePromptExecutor
        assert "failed" in result.output.lower()


def test_pr_diverge_fix_fails_when_no_work_events() -> None:
    """Test that command fails when Claude completes but produces no work events."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
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
        executor = FakePromptExecutor(
            available=True,
            simulated_no_work_events=True,
        )

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["diverge-fix", "--dangerous"], obj=ctx)

        # Should fail due to no work events
        assert result.exit_code != 0
        assert "without producing any output" in result.output
        assert "check hooks" in result.output
