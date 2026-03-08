"""Tests for erk pr rebase command."""

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.git.abc import RebaseResult
from erk_shared.gateway.git.fake import FakeGit
from tests.fakes.prompt_executor import FakePromptExecutor
from tests.test_utils.context_builders import (
    build_graphite_test_context,
    build_workspace_test_context,
)
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_rebase_non_graphite_success() -> None:
    """Test successful rebase via git rebase (Graphite disabled)."""
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

        result = runner.invoke(pr_group, ["rebase", "--dangerous", "--target", "main"], obj=ctx)

        assert result.exit_code == 0
        assert "Rebase complete!" in result.output
        assert len(executor.interactive_calls) == 0
        assert len(git.rebase_onto_calls) == 1


def test_pr_rebase_non_graphite_conflict_launches_tui() -> None:
    """Test that git rebase conflicts show files and launch Claude TUI after confirm."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            rebase_onto_result=RebaseResult(success=False, conflict_files=("file.py",)),
            conflicted_files=["file.py"],
        )

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(
            pr_group, ["rebase", "--dangerous", "--target", "main"], obj=ctx, input="y\n"
        )

        assert result.exit_code == 0
        assert "Rebase hit conflicts" in result.output
        assert "file.py" in result.output
        assert "Launch Claude to resolve conflicts?" in result.output
        assert len(executor.interactive_calls) == 1
        call = executor.interactive_calls[0]
        assert call[2] == "/erk:pr-rebase"  # command
        assert call[5] == "edits"  # permission_mode


def test_pr_rebase_non_graphite_no_target_error() -> None:
    """Test error when --target not provided with Graphite disabled."""
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

        result = runner.invoke(pr_group, ["rebase", "--dangerous"], obj=ctx)

        assert result.exit_code != 0
        assert "Specify --target" in result.output


def test_pr_rebase_in_progress_launches_tui() -> None:
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

        result = runner.invoke(pr_group, ["rebase", "--dangerous"], obj=ctx, input="y\n")

        assert result.exit_code == 0
        assert "Rebase in progress" in result.output
        assert "src/context.py" in result.output
        assert "src/fast_llm.py" in result.output
        assert "Launch Claude to resolve conflicts?" in result.output
        assert len(executor.interactive_calls) == 1


def test_pr_rebase_succeeds_without_dangerous_flag() -> None:
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

        result = runner.invoke(pr_group, ["rebase", "--target", "main"], obj=ctx)

        assert result.exit_code == 0
        assert "Rebase complete!" in result.output


def test_pr_rebase_safe_flag_disables_dangerous() -> None:
    """Test that --safe overrides live_dangerously=True default."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            rebase_onto_result=RebaseResult(success=False, conflict_files=("file.py",)),
            conflicted_files=["file.py"],
        )

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(
            pr_group, ["rebase", "--safe", "--target", "main"], obj=ctx, input="y\n"
        )

        assert result.exit_code == 0
        assert len(executor.interactive_calls) == 1
        call = executor.interactive_calls[0]
        assert call[1] is False  # dangerous should be False


def test_pr_rebase_dangerous_and_safe_mutually_exclusive() -> None:
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

        result = runner.invoke(
            pr_group, ["rebase", "--dangerous", "--safe", "--target", "main"], obj=ctx
        )

        assert result.exit_code != 0
        assert "mutually exclusive" in result.output


def test_pr_rebase_live_dangerously_false_runs_safe() -> None:
    """Test that live_dangerously=False makes command run in safe mode by default."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            rebase_onto_result=RebaseResult(success=False, conflict_files=("file.py",)),
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

        result = runner.invoke(pr_group, ["rebase", "--target", "main"], obj=ctx, input="y\n")

        assert result.exit_code == 0
        assert len(executor.interactive_calls) == 1
        call = executor.interactive_calls[0]
        assert call[1] is False  # dangerous should be False


def test_pr_rebase_claude_not_available() -> None:
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

        result = runner.invoke(pr_group, ["rebase", "--dangerous", "--target", "main"], obj=ctx)

        assert result.exit_code != 0
        assert "Claude CLI is required" in result.output
        assert "claude.com/download" in result.output

        assert len(executor.interactive_calls) == 0


def test_pr_rebase_conflict_user_declines() -> None:
    """Test that declining the confirm prompt does not launch Claude."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            rebase_onto_result=RebaseResult(success=False, conflict_files=("file.py",)),
            conflicted_files=["file.py"],
        )

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(
            pr_group, ["rebase", "--dangerous", "--target", "main"], obj=ctx, input="n\n"
        )

        assert result.exit_code == 0
        assert "file.py" in result.output
        assert "Launch Claude to resolve conflicts?" in result.output
        assert "Rebase paused" in result.output
        assert len(executor.interactive_calls) == 0


def test_pr_rebase_conflict_no_conflicted_files_still_confirms() -> None:
    """Test that confirm prompt appears even when get_conflicted_files returns empty."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            rebase_onto_result=RebaseResult(success=False, conflict_files=("file.py",)),
        )

        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(
            pr_group, ["rebase", "--dangerous", "--target", "main"], obj=ctx, input="y\n"
        )

        assert result.exit_code == 0
        assert "Conflicted files:" not in result.output
        assert "Launch Claude to resolve conflicts?" in result.output
        assert len(executor.interactive_calls) == 1


def test_pr_rebase_graphite_restack_in_progress_launches_tui() -> None:
    """Test that gt restack in-progress state bypasses tracking check and launches Claude."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={},  # No current branch = detached HEAD
            rebase_in_progress=True,
            conflicted_files=["docs/learned/cli/tripwires.md", "docs/learned/tripwires-index.md"],
        )

        executor = FakePromptExecutor(available=True)

        ctx = build_graphite_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["rebase", "--dangerous"], obj=ctx, input="y\n")

        assert result.exit_code == 0
        assert "Restack in progress" in result.output
        assert "Launch Claude to resolve conflicts?" in result.output
        assert len(executor.interactive_calls) == 1
        call = executor.interactive_calls[0]
        assert call[2] == "/erk:pr-rebase"  # command


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

        ctx = build_graphite_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["rebase", "--dangerous"], obj=ctx, input="y\n")

        assert result.exit_code == 0
        assert "Restack in progress" in result.output
        assert len(executor.interactive_calls) == 1
