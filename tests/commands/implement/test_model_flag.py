"""Tests for model flag integration in implement command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.implement import implement
from erk_shared.git.fake import FakeGit
from tests.commands.implement.conftest import create_sample_plan_issue
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans


def test_model_flag_in_interactive_mode() -> None:
    """Verify --model flag is passed to executor in interactive mode."""
    plan_issue = create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, claude_executor=executor)

        result = runner.invoke(implement, ["#42", "--model", "opus"], obj=ctx)

        assert result.exit_code == 0

        # Verify model was passed to execute_interactive
        assert len(executor.interactive_calls) == 1
        _, _, _, _, model = executor.interactive_calls[0]
        assert model == "opus"


def test_model_flag_short_form_in_interactive_mode() -> None:
    """Verify -m short form flag is passed to executor in interactive mode."""
    plan_issue = create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, claude_executor=executor)

        result = runner.invoke(implement, ["#42", "-m", "sonnet"], obj=ctx)

        assert result.exit_code == 0

        # Verify model was passed to execute_interactive
        assert len(executor.interactive_calls) == 1
        _, _, _, _, model = executor.interactive_calls[0]
        assert model == "sonnet"


def test_model_alias_in_interactive_mode() -> None:
    """Verify model alias (h, s, o) is expanded in interactive mode."""
    plan_issue = create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, claude_executor=executor)

        result = runner.invoke(implement, ["#42", "-m", "h"], obj=ctx)

        assert result.exit_code == 0

        # Verify model alias was expanded to full name
        assert len(executor.interactive_calls) == 1
        _, _, _, _, model = executor.interactive_calls[0]
        assert model == "haiku"


def test_model_flag_in_non_interactive_mode() -> None:
    """Verify --model flag is passed to executor in non-interactive mode."""
    plan_issue = create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, claude_executor=executor)

        result = runner.invoke(implement, ["#42", "--no-interactive", "--model", "opus"], obj=ctx)

        assert result.exit_code == 0

        # Verify model was passed to execute_command
        assert len(executor.executed_commands) == 1
        _, _, _, _, model = executor.executed_commands[0]
        assert model == "opus"


def test_model_flag_in_script_mode() -> None:
    """Verify --model flag is included in generated script."""
    plan_issue = create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--script", "--model", "sonnet"], obj=ctx)

        assert result.exit_code == 0

        # Verify script path is output
        assert result.stdout
        script_path = Path(result.stdout.strip())

        # Verify script file exists and read its content
        assert script_path.exists()
        script_content = script_path.read_text(encoding="utf-8")

        # Verify --model flag is present in the generated command
        assert "--model sonnet" in script_content


def test_model_flag_in_dry_run() -> None:
    """Verify --model flag is shown in dry-run output."""
    plan_issue = create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(
            implement, ["#42", "--dry-run", "--no-interactive", "--model", "opus"], obj=ctx
        )

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output

        # Verify --model flag is shown in the command sequence
        assert "--model opus" in result.output

        # Verify no worktree was created
        assert len(git.added_worktrees) == 0


def test_invalid_model_flag() -> None:
    """Verify invalid model names are rejected."""
    plan_issue = create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--model", "invalid-model"], obj=ctx)

        assert result.exit_code != 0
        assert "Invalid model" in result.output
