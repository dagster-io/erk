"""Tests for plan file mode in implement command."""

from click.testing import CliRunner

from erk.cli.commands.implement import implement
from erk_shared.gateway.git.fake import FakeGit
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_implement_from_plan_file() -> None:
    """Test implementing from plan file creates .impl/ in current directory."""
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

        result = runner.invoke(implement, [str(plan_file)], obj=ctx)

        assert result.exit_code == 0
        assert "Created .impl/ folder" in result.output

        # Verify .impl/ folder exists with plan content
        impl_plan = env.cwd / ".impl" / "plan.md"
        assert impl_plan.exists()
        assert impl_plan.read_text(encoding="utf-8") == plan_content

        # Verify original plan file preserved (not deleted)
        assert plan_file.exists()


def test_implement_from_plan_file_creates_impl_folder() -> None:
    """Test implementing from plan file creates .impl/ folder in cwd."""
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
        plan_file = env.cwd / "feature-plan.md"
        plan_file.write_text("# Plan", encoding="utf-8")

        result = runner.invoke(implement, [str(plan_file)], obj=ctx)

        assert result.exit_code == 0
        assert "Created .impl/ folder" in result.output

        # Verify .impl/ was created in current directory
        impl_dir = env.cwd / ".impl"
        assert impl_dir.exists()
        assert (impl_dir / "plan.md").exists()


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
        assert "Would run in current directory" in result.output
        assert str(plan_file) in result.output

        # Verify plan file preserved in dry-run
        assert plan_file.exists()

        # Verify no .impl/ created in dry-run
        assert not (env.cwd / ".impl").exists()
