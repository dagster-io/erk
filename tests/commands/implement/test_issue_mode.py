"""Tests for GitHub issue mode in implement command."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.implement import implement
from erk_shared.git.fake import FakeGit
from erk_shared.plan_store.types import Plan, PlanState
from tests.commands.implement.conftest import create_sample_plan_issue
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans


def test_implement_from_plain_issue_number() -> None:
    """Test implementing from GitHub issue number without # prefix."""
    plan_issue = create_sample_plan_issue("123")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"123": plan_issue})
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, claude_executor=executor)

        # Test with plain number (no # prefix)
        result = runner.invoke(implement, ["123"], obj=ctx)

        assert result.exit_code == 0
        assert "Created .impl/ folder" in result.output

        # Verify .impl/ folder exists with correct issue number
        issue_json_path = env.cwd / ".impl" / "issue.json"
        issue_json_content = issue_json_path.read_text(encoding="utf-8")
        assert '"issue_number": 123' in issue_json_content


def test_implement_from_issue_number() -> None:
    """Test implementing from GitHub issue number with # prefix."""
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

        result = runner.invoke(implement, ["#42"], obj=ctx)

        assert result.exit_code == 0
        assert "Created .impl/ folder" in result.output

        # Verify .impl/ folder exists
        impl_path = env.cwd / ".impl"
        assert impl_path.exists()
        assert (impl_path / "plan.md").exists()
        assert (impl_path / "issue.json").exists()


def test_implement_from_issue_url() -> None:
    """Test implementing from GitHub issue URL."""
    plan_issue = create_sample_plan_issue("123")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"123": plan_issue})
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, claude_executor=executor)

        url = "https://github.com/owner/repo/issues/123"
        result = runner.invoke(implement, [url], obj=ctx)

        assert result.exit_code == 0
        assert "Created .impl/ folder" in result.output

        # Verify issue.json contains correct issue number
        issue_json_path = env.cwd / ".impl" / "issue.json"
        issue_json_content = issue_json_path.read_text(encoding="utf-8")
        assert '"issue_number": 123' in issue_json_content


def test_implement_creates_impl_folder_in_cwd() -> None:
    """Test that implement creates .impl/ folder in current directory."""
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

        result = runner.invoke(implement, ["#42"], obj=ctx)

        assert result.exit_code == 0
        assert "Created .impl/ folder" in result.output

        # Verify .impl/ was created in current directory
        impl_dir = env.cwd / ".impl"
        assert impl_dir.exists()


def test_implement_from_issue_fails_without_erk_plan_label() -> None:
    """Test that command fails when issue doesn't have erk-plan label."""
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
        objective_id=None,
    )

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#42", "--dry-run"], obj=ctx)

        assert result.exit_code == 1
        assert "Error" in result.output
        assert "erk-plan" in result.output


def test_implement_from_issue_fails_when_not_found() -> None:
    """Test that command fails when issue doesn't exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        result = runner.invoke(implement, ["#999", "--dry-run"], obj=ctx)

        assert result.exit_code == 1
        assert "Error" in result.output


def test_implement_from_issue_dry_run() -> None:
    """Test dry-run mode for issue implementation."""
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

        result = runner.invoke(implement, ["#42", "--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output
        assert "Would run in current directory" in result.output
        assert "Add Authentication Feature" in result.output

        # Verify no .impl/ created in dry-run
        assert not (env.cwd / ".impl").exists()


def test_auto_detect_plan_from_branch_name() -> None:
    """Test auto-detection of plan number from PXXXX-* branch."""
    plan_issue = create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "P42-my-feature-01-16-1200"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "P42-my-feature-01-16-1200"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_store=store)

        # TARGET omitted, should auto-detect from branch name
        result = runner.invoke(implement, ["--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "Auto-detected plan #42" in result.output
        assert "Dry-run mode" in result.output


def test_auto_detect_fails_on_non_plan_branch() -> None:
    """Test error when TARGET omitted and not on PXXXX-* branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(implement, ["--dry-run"], obj=ctx)

        assert result.exit_code != 0
        assert "Could not auto-detect plan number" in result.output
        assert "feature-branch" in result.output
        assert "PXXXX-* pattern" in result.output
