"""Tests for --here flag in implement command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.implement import implement
from erk_shared.git.fake import FakeGit
from tests.commands.implement.conftest import create_sample_plan_issue
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans


def test_implement_here_from_issue_creates_impl_in_cwd() -> None:
    """Test that --here creates .impl/ in current directory, no pool slot."""
    plan_issue = create_sample_plan_issue("123")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"123": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["123", "--here", "--script"], obj=ctx)

        assert result.exit_code == 0
        # Should NOT show slot assignment
        assert "erk-slot-" not in result.output
        # Should show .impl/ creation
        assert "Created .impl/ folder" in result.output

        # No worktree created
        assert len(git.added_worktrees) == 0

        # .impl/ folder exists in cwd
        impl_dir = env.cwd / ".impl"
        assert impl_dir.exists()
        assert (impl_dir / "plan.md").exists()
        assert (impl_dir / "issue.json").exists()

        # Verify issue.json content
        issue_json = (impl_dir / "issue.json").read_text(encoding="utf-8")
        assert '"issue_number": 123' in issue_json


def test_implement_here_from_file_creates_impl_in_cwd() -> None:
    """Test that --here from file creates .impl/ in current directory."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        # Create plan file
        plan_content = "# Implementation Plan\n\nImplement feature X."
        plan_file = env.cwd / "my-feature-plan.md"
        plan_file.write_text(plan_content, encoding="utf-8")

        result = runner.invoke(implement, [str(plan_file), "--here", "--script"], obj=ctx)

        assert result.exit_code == 0
        # Should NOT show slot assignment
        assert "erk-slot-" not in result.output
        # Should show .impl/ creation
        assert "Created .impl/ folder" in result.output

        # No worktree created
        assert len(git.added_worktrees) == 0

        # .impl/ folder exists in cwd with plan content
        impl_dir = env.cwd / ".impl"
        assert impl_dir.exists()
        impl_plan = impl_dir / "plan.md"
        assert impl_plan.exists()
        assert impl_plan.read_text(encoding="utf-8") == plan_content


def test_implement_here_from_file_deletes_original() -> None:
    """Test that --here from file deletes original plan file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        # Create plan file
        plan_file = env.cwd / "feature-plan.md"
        plan_file.write_text("# Plan content", encoding="utf-8")
        assert plan_file.exists()

        result = runner.invoke(implement, [str(plan_file), "--here", "--script"], obj=ctx)

        assert result.exit_code == 0

        # Original plan file should be deleted
        assert not plan_file.exists()

        # But content should be in .impl/plan.md
        impl_plan = env.cwd / ".impl" / "plan.md"
        assert impl_plan.exists()
        assert impl_plan.read_text(encoding="utf-8") == "# Plan content"


def test_implement_here_with_dry_run() -> None:
    """Test --here with --dry-run shows what would happen without mutation."""
    plan_issue = create_sample_plan_issue("42")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--here", "--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output
        assert "Would create .impl/ in current directory" in result.output

        # No worktree created
        assert len(git.added_worktrees) == 0

        # No .impl/ created
        assert not (env.cwd / ".impl").exists()


def test_implement_here_with_force_errors() -> None:
    """Test that --here and --force are incompatible."""
    plan_issue = create_sample_plan_issue("42")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--here", "--force"], obj=ctx)

        assert result.exit_code != 0
        assert "--force is for pool slot management" in result.output


def test_implement_here_with_script_generates_script() -> None:
    """Test that --here --script generates activation script without cd."""
    plan_issue = create_sample_plan_issue("42")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--here", "--script"], obj=ctx)

        assert result.exit_code == 0

        # Verify script path is output
        assert result.stdout
        script_path = Path(result.stdout.strip())

        # Verify script file exists and read its content
        assert script_path.exists()
        script_content = script_path.read_text(encoding="utf-8")

        # Should have claude command
        assert "/erk:system:impl-execute" in script_content


def test_implement_here_issue_without_erk_plan_label_fails() -> None:
    """Test that --here fails for issue without erk-plan label."""
    from datetime import UTC, datetime

    from erk_shared.plan_store.types import Plan, PlanState

    plan_issue = Plan(
        plan_identifier="42",
        title="Regular Issue",
        body="Not a plan issue",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["bug"],  # Missing "erk-plan" label
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--here", "--script"], obj=ctx)

        assert result.exit_code == 1
        assert "erk-plan" in result.output

        # No .impl/ created
        assert not (env.cwd / ".impl").exists()


def test_implement_here_file_not_found_fails() -> None:
    """Test that --here with nonexistent file fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(implement, ["nonexistent.md", "--here", "--script"], obj=ctx)

        assert result.exit_code == 1
        assert "not found" in result.output


def test_implement_here_with_submit_flag() -> None:
    """Test that --here --submit --script generates script with all commands."""
    plan_issue = create_sample_plan_issue("42")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--here", "--submit", "--script"], obj=ctx)

        assert result.exit_code == 0

        # Verify script contains all commands
        script_path = Path(result.stdout.strip())
        script_content = script_path.read_text(encoding="utf-8")

        assert "/erk:system:impl-execute" in script_content
        assert "/fast-ci" in script_content
        assert "/gt:pr-submit" in script_content
