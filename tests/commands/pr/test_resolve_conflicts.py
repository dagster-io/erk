"""Tests for erk pr resolve-conflicts command."""

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.context.types import GlobalConfig
from tests.fakes.gateway.git import FakeGit
from tests.fakes.tests.prompt_executor import FakePromptExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_rebase_in_progress_launches_tui() -> None:
    """Test that existing rebase-in-progress shows files and launches Claude TUI."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            rebase_in_progress=True,
            conflicted_files=["src/context.py", "src/fast_llm.py"],
        )

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["resolve-conflicts", "--dangerous"], obj=ctx, input="y\n")

        assert result.exit_code == 0
        assert "Rebase in progress" in result.output
        assert "src/context.py" in result.output
        assert "src/fast_llm.py" in result.output
        assert "Launch Claude to resolve conflicts?" in result.output
        assert len(executor.interactive_calls) == 1
        call = executor.interactive_calls[0]
        assert call[2] == "/erk:pr-resolve-conflicts"  # command
        assert call[5] == "edits"  # permission_mode


def test_no_rebase_in_progress_error() -> None:
    """Test error when no rebase is in progress."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            rebase_in_progress=False,
        )

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["resolve-conflicts", "--dangerous"], obj=ctx)

        assert result.exit_code != 0
        assert "No rebase in progress" in result.output
        assert "git rebase <branch>" in result.output
        assert len(executor.interactive_calls) == 0


def test_user_declines() -> None:
    """Test that declining the confirm prompt does not launch Claude."""
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

        result = runner.invoke(pr_group, ["resolve-conflicts", "--dangerous"], obj=ctx, input="n\n")

        assert result.exit_code == 0
        assert "Launch Claude to resolve conflicts?" in result.output
        assert "Conflicts remain" in result.output
        assert "erk pr resolve-conflicts" in result.output
        assert len(executor.interactive_calls) == 0


def test_claude_not_available() -> None:
    """Test error when Claude is not installed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            rebase_in_progress=True,
        )

        executor = FakePromptExecutor(available=False)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["resolve-conflicts", "--dangerous"], obj=ctx)

        assert result.exit_code != 0
        assert "Claude CLI is required" in result.output
        assert "claude.com/download" in result.output
        assert len(executor.interactive_calls) == 0


def test_safe_flag() -> None:
    """Test that --safe overrides live_dangerously=True default."""
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

        result = runner.invoke(pr_group, ["resolve-conflicts", "--safe"], obj=ctx, input="y\n")

        assert result.exit_code == 0
        assert len(executor.interactive_calls) == 1
        call = executor.interactive_calls[0]
        assert call[1] is False  # dangerous should be False


def test_dangerous_and_safe_mutually_exclusive() -> None:
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

        result = runner.invoke(pr_group, ["resolve-conflicts", "--dangerous", "--safe"], obj=ctx)

        assert result.exit_code != 0
        assert "mutually exclusive" in result.output


def test_live_dangerously_false_runs_safe() -> None:
    """Test that live_dangerously=False makes command run in safe mode by default."""
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

        result = runner.invoke(pr_group, ["resolve-conflicts"], obj=ctx, input="y\n")

        assert result.exit_code == 0
        assert len(executor.interactive_calls) == 1
        call = executor.interactive_calls[0]
        assert call[1] is False  # dangerous should be False


def test_no_conflicted_files_still_confirms() -> None:
    """Test that confirm prompt appears even when get_conflicted_files returns empty."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            rebase_in_progress=True,
        )

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["resolve-conflicts", "--dangerous"], obj=ctx, input="y\n")

        assert result.exit_code == 0
        assert "Conflicted files:" not in result.output
        assert "Launch Claude to resolve conflicts?" in result.output
        assert len(executor.interactive_calls) == 1
