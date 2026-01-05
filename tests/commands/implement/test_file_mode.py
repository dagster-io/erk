"""Tests for plan file mode in implement command."""

from click.testing import CliRunner

from erk.cli.commands.implement import implement
from erk_shared.git.fake import FakeGit
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_implement_from_plan_file() -> None:
    """Test implementing from plan file."""
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

        result = runner.invoke(implement, [str(plan_file), "--script"], obj=ctx)

        assert result.exit_code == 0
        assert "Assigned" in result.output
        assert "erk-managed-wt-" in result.output

        # Verify worktree created
        assert len(git.added_worktrees) == 1

        # Verify .impl/ folder exists with plan content
        worktree_paths = [wt[0] for wt in git.added_worktrees]
        impl_plan = worktree_paths[0] / ".impl" / "plan.md"
        assert impl_plan.exists()
        assert impl_plan.read_text(encoding="utf-8") == plan_content

        # Verify original plan file deleted (move semantics)
        assert not plan_file.exists()


def test_implement_from_plan_file_assigns_to_slot() -> None:
    """Test implementing from plan file assigns to a pool slot."""
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
        plan_file.write_text("# Plan", encoding="utf-8")

        result = runner.invoke(implement, [str(plan_file), "--script"], obj=ctx)

        assert result.exit_code == 0
        # Should show slot assignment message
        assert "Assigned" in result.output
        assert "erk-managed-wt-" in result.output

        # Verify worktree was created in slot path
        worktree_path, _ = git.added_worktrees[0]
        assert "erk-managed-wt-" in str(worktree_path)


def test_implement_from_plan_file_strips_plan_suffix() -> None:
    """Test that '-plan' suffix is stripped from plan filenames."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        # Create plan file with -plan suffix
        plan_file = env.cwd / "authentication-feature-plan.md"
        plan_file.write_text("# Plan", encoding="utf-8")

        result = runner.invoke(implement, [str(plan_file), "--script"], obj=ctx)

        assert result.exit_code == 0
        # Verify -plan suffix was stripped
        assert "authentication-feature" in result.output
        # Ensure no "-plan" in worktree name
        worktree_path, _ = git.added_worktrees[0]
        worktree_name = str(worktree_path.name)
        assert "-plan" not in worktree_name or worktree_name.endswith("-plan") is False


def test_implement_from_plan_file_fails_when_not_found() -> None:
    """Test that command fails when plan file doesn't exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(implement, ["nonexistent-plan.md", "--dry-run"], obj=ctx)

        assert result.exit_code == 1
        assert "Error" in result.output
        assert "not found" in result.output
        assert len(git.added_worktrees) == 0


def test_implement_from_plan_file_dry_run() -> None:
    """Test dry-run mode for plan file implementation."""
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
        plan_file.write_text("# Plan", encoding="utf-8")

        result = runner.invoke(implement, [str(plan_file), "--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output
        assert "Would create worktree" in result.output
        assert str(plan_file) in result.output
        assert len(git.added_worktrees) == 0
        # Verify plan file NOT deleted in dry-run
        assert plan_file.exists()
