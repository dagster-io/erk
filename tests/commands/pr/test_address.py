"""Tests for erk pr address command (local variant)."""

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.context.types import GlobalConfig
from erk_shared.fakes.git import FakeGit
from tests.fakes.prompt_executor import FakePromptExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_address_success() -> None:
    """Test successful local address when Claude is available."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["address", "--dangerous"], obj=ctx)

        assert result.exit_code == 0
        assert "PR comments addressed!" in result.output

        # Claude should be invoked for PR comment addressing
        assert len(executor.executed_commands) == 1
        command, _, dangerous_flag, _, _ = executor.executed_commands[0]
        assert command == "/erk:pr-address"
        assert dangerous_flag is True


def test_pr_address_succeeds_without_dangerous_flag() -> None:
    """Test that command succeeds without --dangerous when live_dangerously=True (default)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["address"], obj=ctx)

        assert result.exit_code == 0
        assert "PR comments addressed!" in result.output


def test_pr_address_safe_flag_disables_dangerous() -> None:
    """Test that --safe overrides live_dangerously=True and passes dangerous=False."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["address", "--safe"], obj=ctx)

        assert result.exit_code == 0
        assert "PR comments addressed!" in result.output
        # Verify dangerous=False was passed to executor
        command, _, dangerous_flag, _, _ = executor.executed_commands[0]
        assert command == "/erk:pr-address"
        assert dangerous_flag is False


def test_pr_address_dangerous_and_safe_mutually_exclusive() -> None:
    """Test that --dangerous and --safe together produce an error."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["address", "--dangerous", "--safe"], obj=ctx)

        assert result.exit_code != 0
        assert "mutually exclusive" in result.output


def test_pr_address_live_dangerously_false_runs_safe() -> None:
    """Test that live_dangerously=False makes command run in safe mode by default."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
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

        result = runner.invoke(pr_group, ["address"], obj=ctx)

        assert result.exit_code == 0
        assert "PR comments addressed!" in result.output
        # Verify dangerous=False was passed to executor
        command, _, dangerous_flag, _, _ = executor.executed_commands[0]
        assert command == "/erk:pr-address"
        assert dangerous_flag is False


def test_pr_address_claude_not_available() -> None:
    """Test error when Claude is not installed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )

        executor = FakePromptExecutor(available=False)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["address", "--dangerous"], obj=ctx)

        assert result.exit_code != 0
        assert "Claude CLI is required" in result.output
        assert "claude.com/download" in result.output

        # Verify no command was executed
        assert len(executor.executed_commands) == 0


def test_pr_address_fails_on_command_error() -> None:
    """Test that command fails when slash command execution fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )

        executor = FakePromptExecutor(
            available=True,
            command_should_fail=True,
        )

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["address", "--dangerous"], obj=ctx)

        assert result.exit_code != 0
        # Error message from FakePromptExecutor
        assert "failed" in result.output.lower()
