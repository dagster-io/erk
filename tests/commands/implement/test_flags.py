"""Tests for submit and dangerous flags in implement command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.implement import implement
from erk_shared.git.fake import FakeGit
from tests.commands.implement.conftest import create_sample_plan_issue
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans

# Submit Flag Tests


def test_implement_with_submit_flag_from_issue() -> None:
    """Test --submit flag with --script from issue includes command chain in script."""
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

        # Use --script --submit to generate activation script with all commands
        result = runner.invoke(implement, ["#42", "--script", "--submit"], obj=ctx)

        assert result.exit_code == 0
        assert "Assigned" in result.output

        # Script should be created
        assert "erk-implement-" in result.output
        assert ".sh" in result.output


def test_implement_with_submit_flag_from_file() -> None:
    """Test implementing from file with --submit flag and --script generates script."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        # Create plan file
        plan_file = env.cwd / "feature-plan.md"
        plan_file.write_text("# Feature Plan\n\nImplement feature.", encoding="utf-8")

        result = runner.invoke(implement, [str(plan_file), "--script", "--submit"], obj=ctx)

        assert result.exit_code == 0
        assert "Assigned" in result.output

        # Script should be created
        assert "erk-implement-" in result.output
        assert ".sh" in result.output

        # Verify plan file was deleted (moved to worktree)
        assert not plan_file.exists()


def test_implement_without_submit_uses_default_command() -> None:
    """Test that default behavior (without --submit) still works unchanged."""
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

        result = runner.invoke(implement, ["#42", "--script"], obj=ctx)

        assert result.exit_code == 0
        assert "Assigned" in result.output

        # Verify script has only implement-plan command (not CI/submit)
        assert "erk-implement-" in result.output
        assert ".sh" in result.output


def test_implement_submit_in_script_mode() -> None:
    """Test that --script --submit combination generates correct activation script."""
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

        result = runner.invoke(implement, ["#42", "--submit", "--script"], obj=ctx)

        assert result.exit_code == 0

        # Verify script path is output
        assert result.stdout
        script_path = Path(result.stdout.strip())

        # Verify script file exists and read its content
        assert script_path.exists()
        script_content = script_path.read_text(encoding="utf-8")

        # Verify script content contains chained commands
        assert "/erk:plan-implement" in script_content
        assert "/fast-ci" in script_content
        assert "/gt:pr-submit" in script_content

        # Verify commands are chained with &&
        assert "&&" in script_content


def test_implement_submit_with_dry_run() -> None:
    """Test that --submit --dry-run shows all commands that would be executed."""
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
            implement, ["#42", "--no-interactive", "--submit", "--dry-run"], obj=ctx
        )

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output

        # Verify execution mode shown
        assert "Execution mode: non-interactive" in result.output

        # Verify all three commands shown in dry-run output
        assert "/erk:plan-implement" in result.output
        assert "/fast-ci" in result.output
        assert "/gt:pr-submit" in result.output

        # Verify no worktree was actually created
        assert len(git.added_worktrees) == 0


# Dangerous Flag Tests


def test_implement_with_dangerous_flag_in_script_mode() -> None:
    """Test that --dangerous flag adds --dangerously-skip-permissions to generated script."""
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

        result = runner.invoke(implement, ["#42", "--dangerous", "--script"], obj=ctx)

        assert result.exit_code == 0

        # Verify script path is output
        assert result.stdout
        script_path = Path(result.stdout.strip())

        # Verify script file exists and read its content
        assert script_path.exists()
        script_content = script_path.read_text(encoding="utf-8")

        # Verify --dangerously-skip-permissions flag is present
        assert "--dangerously-skip-permissions" in script_content
        expected_cmd = (
            "claude --permission-mode acceptEdits "
            "--dangerously-skip-permissions /erk:plan-implement"
        )
        assert expected_cmd in script_content


def test_implement_without_dangerous_flag_in_script_mode() -> None:
    """Test that script without --dangerous flag does not include --dangerously-skip-permissions."""
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

        result = runner.invoke(implement, ["#42", "--script"], obj=ctx)

        assert result.exit_code == 0

        # Verify script path is output
        assert result.stdout
        script_path = Path(result.stdout.strip())

        # Verify script file exists and read its content
        assert script_path.exists()
        script_content = script_path.read_text(encoding="utf-8")

        # Verify --dangerously-skip-permissions flag is NOT present
        assert "--dangerously-skip-permissions" not in script_content
        # But standard flags should be present
        assert "claude --permission-mode acceptEdits /erk:plan-implement" in script_content


def test_implement_with_dangerous_and_submit_flags() -> None:
    """Test that --dangerous --submit combination adds flag to all three commands."""
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

        result = runner.invoke(implement, ["#42", "--dangerous", "--submit", "--script"], obj=ctx)

        assert result.exit_code == 0

        # Verify script path is output
        assert result.stdout
        script_path = Path(result.stdout.strip())

        # Verify script file exists and read its content
        assert script_path.exists()
        script_content = script_path.read_text(encoding="utf-8")

        # Verify all three commands have the dangerous flag
        assert script_content.count("--dangerously-skip-permissions") == 3
        expected_implement = (
            "claude --permission-mode acceptEdits "
            "--dangerously-skip-permissions /erk:plan-implement"
        )
        expected_ci = "claude --permission-mode acceptEdits --dangerously-skip-permissions /fast-ci"
        expected_submit = (
            "claude --permission-mode acceptEdits --dangerously-skip-permissions /gt:pr-submit"
        )
        assert expected_implement in script_content
        assert expected_ci in script_content
        assert expected_submit in script_content


def test_implement_with_dangerous_flag_in_dry_run() -> None:
    """Test that --dangerous flag shows in dry-run output."""
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

        result = runner.invoke(implement, ["#42", "--dangerous", "--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output

        # Verify dangerous flag is shown in the command
        assert "--dangerously-skip-permissions" in result.output
        expected_cmd = (
            "claude --permission-mode acceptEdits "
            "--dangerously-skip-permissions /erk:plan-implement"
        )
        assert expected_cmd in result.output

        # Verify no worktree was created
        assert len(git.added_worktrees) == 0


def test_implement_with_dangerous_and_submit_in_dry_run() -> None:
    """Test that --dangerous --submit shows flag in all three commands during dry-run."""
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
            implement,
            ["#42", "--dangerous", "--no-interactive", "--submit", "--dry-run"],
            obj=ctx,
        )

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output

        # Verify all three commands show the dangerous flag
        assert result.output.count("--dangerously-skip-permissions") == 3

        # Verify no worktree was created
        assert len(git.added_worktrees) == 0


def test_implement_plan_file_with_dangerous_flag() -> None:
    """Test that --dangerous flag works with plan file mode."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        # Create plan file
        plan_content = "# Implementation Plan\n\nImplement feature X."
        plan_file = env.cwd / "my-feature-plan.md"
        plan_file.write_text(plan_content, encoding="utf-8")

        result = runner.invoke(implement, [str(plan_file), "--dangerous", "--script"], obj=ctx)

        assert result.exit_code == 0

        # Verify script path is output
        assert result.stdout
        script_path = Path(result.stdout.strip())

        # Verify script file exists and read its content
        assert script_path.exists()
        script_content = script_path.read_text(encoding="utf-8")

        # Verify dangerous flag is present
        assert "--dangerously-skip-permissions" in script_content

        # Verify plan file was moved to worktree (deleted from original location)
        assert not plan_file.exists()


def test_implement_with_dangerous_shows_in_manual_instructions() -> None:
    """Test that --dangerous flag appears in manual instructions when shell integration disabled."""
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

        # Use --script flag to generate activation script with dangerous flag
        result = runner.invoke(implement, ["#42", "--dangerous", "--script"], obj=ctx)

        assert result.exit_code == 0
        assert "Assigned" in result.output

        # Verify dangerous flag shown in script file
        assert result.stdout
        script_path = Path(result.stdout.strip())
        assert script_path.exists()
        script_content = script_path.read_text(encoding="utf-8")
        assert "--dangerously-skip-permissions" in script_content
