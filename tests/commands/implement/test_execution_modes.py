"""Tests for execution modes in implement command.

Covers interactive mode, non-interactive mode, script mode, YOLO flag,
and mutual exclusivity validation.
"""

from click.testing import CliRunner

from erk.cli.commands.implement import implement
from erk_shared.git.fake import FakeGit
from tests.commands.implement.conftest import create_sample_plan_issue
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans

# Interactive Mode Tests


def test_interactive_mode_calls_executor() -> None:
    """Verify interactive mode calls executor.execute_interactive."""
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

        # Interactive mode is the default (no --no-interactive flag)
        # Set ERK_SHELL to simulate shell integration being active
        result = runner.invoke(implement, ["#42"], obj=ctx, env={"ERK_SHELL": "zsh"})

        assert result.exit_code == 0

        # Verify execute_interactive was called, not execute_command
        assert len(executor.interactive_calls) == 1
        assert len(executor.executed_commands) == 0

        worktree_path, dangerous, command, target_subpath, model = executor.interactive_calls[0]
        # Slot-based path
        assert "erk-managed-wt-" in str(worktree_path)
        assert dangerous is False
        assert command == "/erk:system:impl-execute"
        # No relative path preservation when running from worktree root
        assert target_subpath is None
        assert model is None


def test_interactive_mode_with_dangerous_flag() -> None:
    """Verify interactive mode passes dangerous flag to executor."""
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

        # Set ERK_SHELL to simulate shell integration being active
        result = runner.invoke(implement, ["#42", "--dangerous"], obj=ctx, env={"ERK_SHELL": "zsh"})

        assert result.exit_code == 0

        # Verify dangerous flag was passed to execute_interactive
        assert len(executor.interactive_calls) == 1
        worktree_path, dangerous, command, target_subpath, model = executor.interactive_calls[0]
        assert dangerous is True
        assert command == "/erk:system:impl-execute"
        assert model is None


def test_interactive_mode_from_plan_file() -> None:
    """Verify interactive mode works with plan file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        # Create plan file
        plan_content = "# Implementation Plan\n\nImplement feature X."
        plan_file = env.cwd / "my-feature-plan.md"
        plan_file.write_text(plan_content, encoding="utf-8")

        # Set ERK_SHELL to simulate shell integration being active
        result = runner.invoke(implement, [str(plan_file)], obj=ctx, env={"ERK_SHELL": "zsh"})

        assert result.exit_code == 0

        # Verify execute_interactive was called
        assert len(executor.interactive_calls) == 1
        worktree_path, dangerous, command, target_subpath, model = executor.interactive_calls[0]
        assert "erk-managed-wt-" in str(worktree_path)
        assert dangerous is False
        assert command == "/erk:system:impl-execute"
        assert model is None

        # Verify plan file was deleted (moved to worktree)
        assert not plan_file.exists()


def test_interactive_mode_fails_when_claude_not_available() -> None:
    """Verify interactive mode fails gracefully when Claude CLI not available."""
    plan_issue = create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        executor = FakeClaudeExecutor(claude_available=False)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, claude_executor=executor)

        # Set ERK_SHELL to simulate shell integration being active
        result = runner.invoke(implement, ["#42"], obj=ctx, env={"ERK_SHELL": "zsh"})

        # Should fail with error about Claude CLI not found
        assert result.exit_code != 0
        assert "Claude CLI not found" in result.output


def test_interactive_mode_uses_subshell_fallback_without_shell_integration() -> None:
    """Verify interactive mode uses subshell fallback when ERK_SHELL is not set.

    Without shell integration, execute_interactive_mode should call
    spawn_worktree_subshell() via the Shell gateway instead of executor.execute_interactive().
    """
    from unittest.mock import patch

    from erk_shared.gateway.shell import FakeShell

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
        shell = FakeShell(subshell_exit_code=0)
        ctx = build_workspace_test_context(
            env, git=git, plan_store=store, claude_executor=executor, shell=shell
        )

        # Patch sys.exit to prevent test from exiting
        with patch("erk.cli.commands.implement_shared.sys.exit"):
            # Do NOT set ERK_SHELL - this triggers subshell fallback path
            runner.invoke(implement, ["#42"], obj=ctx)

        # Verify spawn_subshell was called via the Shell gateway
        assert len(shell.subshell_calls) == 1
        assert len(executor.interactive_calls) == 0

        # Verify the spawn call arguments
        call = shell.subshell_calls[0]
        assert "/erk:system:impl-execute" in call.command


# Non-Interactive Mode Tests


def test_non_interactive_executes_single_command() -> None:
    """Verify --no-interactive runs executor for implementation."""
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

        result = runner.invoke(implement, ["#42", "--no-interactive"], obj=ctx)

        assert result.exit_code == 0

        # Verify one command execution
        assert len(executor.executed_commands) == 1
        command, worktree_path, dangerous, verbose, model = executor.executed_commands[0]
        assert command == "/erk:plan-implement"
        assert dangerous is False
        assert verbose is False
        assert model is None


def test_non_interactive_with_submit_runs_all_commands() -> None:
    """Verify --no-interactive --submit runs all three commands."""
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

        result = runner.invoke(
            implement,
            ["#42", "--no-interactive", "--submit"],
            obj=ctx,
        )

        assert result.exit_code == 0

        # Verify three command executions
        assert len(executor.executed_commands) == 3
        commands = [cmd for cmd, _, _, _, _ in executor.executed_commands]
        assert commands[0] == "/erk:plan-implement"
        assert commands[1] == "/fast-ci"
        assert commands[2] == "/gt:pr-submit"


# Script Mode Tests


def test_script_with_submit_includes_all_commands() -> None:
    """Verify --script --submit succeeds and creates script file."""
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

        result = runner.invoke(implement, ["#42", "--script", "--submit"], obj=ctx)

        assert result.exit_code == 0

        # Script should be created (output contains script path)
        assert "erk-implement-" in result.output
        assert ".sh" in result.output


# Dry-Run Tests


def test_dry_run_shows_execution_mode() -> None:
    """Verify --dry-run shows execution mode."""
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

        # Test with interactive mode (default)
        result = runner.invoke(implement, ["#42", "--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "Execution mode: interactive" in result.output

        # Test with non-interactive mode
        result = runner.invoke(implement, ["#42", "--dry-run", "--no-interactive"], obj=ctx)

        assert result.exit_code == 0
        assert "Execution mode: non-interactive" in result.output


def test_dry_run_shows_command_sequence() -> None:
    """Verify --dry-run shows correct command sequence."""
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

        # Without --submit (single command)
        result = runner.invoke(implement, ["#42", "--dry-run", "--no-interactive"], obj=ctx)

        assert result.exit_code == 0
        assert "Command sequence:" in result.output
        assert "/erk:plan-implement" in result.output
        assert "/fast-ci" not in result.output

        # With --submit (three commands)
        result = runner.invoke(
            implement, ["#42", "--dry-run", "--no-interactive", "--submit"], obj=ctx
        )

        assert result.exit_code == 0
        assert "Command sequence:" in result.output
        assert "/erk:plan-implement" in result.output
        assert "/fast-ci" in result.output
        assert "/gt:pr-submit" in result.output


# YOLO Flag Tests


def test_yolo_flag_sets_all_flags() -> None:
    """Verify --yolo flag is equivalent to --dangerous --submit --no-interactive."""
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

        result = runner.invoke(implement, ["#42", "--yolo"], obj=ctx)

        assert result.exit_code == 0

        # Verify three command executions (submit mode)
        assert len(executor.executed_commands) == 3
        commands = [cmd for cmd, _, dangerous, _, _ in executor.executed_commands]
        assert commands[0] == "/erk:plan-implement"
        assert commands[1] == "/fast-ci"
        assert commands[2] == "/gt:pr-submit"

        # Verify dangerous flag was set for all commands
        for _, _, dangerous, _, _ in executor.executed_commands:
            assert dangerous is True


def test_yolo_flag_in_dry_run() -> None:
    """Verify --yolo flag works with --dry-run."""
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

        result = runner.invoke(implement, ["#42", "--yolo", "--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output

        # Verify execution mode shown as non-interactive
        assert "Execution mode: non-interactive" in result.output

        # Verify all three commands shown with dangerous flag
        assert result.output.count("--dangerously-skip-permissions") == 3
        assert "/erk:plan-implement" in result.output
        assert "/fast-ci" in result.output
        assert "/gt:pr-submit" in result.output

        # Verify no worktree was created
        assert len(git.added_worktrees) == 0


def test_yolo_flag_conflicts_with_script() -> None:
    """Verify --yolo and --script are mutually exclusive."""
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

        # --yolo sets --no-interactive, which conflicts with --script
        result = runner.invoke(implement, ["#42", "--yolo", "--script"], obj=ctx)

        assert result.exit_code != 0
        assert "mutually exclusive" in result.output


# Mutual Exclusivity Validation Tests


def test_submit_without_non_interactive_errors() -> None:
    """Verify --submit requires --no-interactive."""
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

        result = runner.invoke(implement, ["#42", "--submit"], obj=ctx)

        assert result.exit_code != 0
        assert "--submit requires --no-interactive" in result.output


def test_script_and_non_interactive_errors() -> None:
    """Verify --script and --no-interactive are mutually exclusive."""
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

        result = runner.invoke(implement, ["#42", "--no-interactive", "--script"], obj=ctx)

        assert result.exit_code != 0
        assert "mutually exclusive" in result.output
