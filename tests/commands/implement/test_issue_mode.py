"""Tests for GitHub issue mode in implement command."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.implement import implement
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.plan_header import update_plan_header_review_pr
from erk_shared.plan_store.types import Plan, PlanState
from tests.commands.implement.conftest import create_sample_plan_issue
from tests.fakes.prompt_executor import FakePromptExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.test_utils.plan_helpers import (
    create_plan_store_with_plans,
    format_plan_header_body_for_test,
)


def test_implement_from_plain_issue_number() -> None:
    """Test implementing from GitHub issue number without # prefix."""
    plan_issue = create_sample_plan_issue("123")

    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"123": plan_issue})
        executor = FakePromptExecutor(available=True)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, prompt_executor=executor)

        # Test with plain number (no # prefix)
        result = runner.invoke(implement, ["123"], obj=ctx)

        assert result.exit_code == 0
        assert "Created .impl/ folder" in result.output

        # Verify .impl/ folder exists with correct plan ID
        plan_ref_path = env.cwd / ".impl" / "plan-ref.json"
        plan_ref_content = plan_ref_path.read_text(encoding="utf-8")
        assert '"plan_id": "123"' in plan_ref_content


def test_implement_from_issue_number() -> None:
    """Test implementing from GitHub issue number with # prefix."""
    plan_issue = create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        executor = FakePromptExecutor(available=True)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, prompt_executor=executor)

        result = runner.invoke(implement, ["#42"], obj=ctx)

        assert result.exit_code == 0
        assert "Created .impl/ folder" in result.output

        # Verify .impl/ folder exists
        impl_path = env.cwd / ".impl"
        assert impl_path.exists()
        assert (impl_path / "plan.md").exists()
        assert (impl_path / "plan-ref.json").exists()


def test_implement_from_issue_url() -> None:
    """Test implementing from GitHub issue URL."""
    plan_issue = create_sample_plan_issue("123")

    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"123": plan_issue})
        executor = FakePromptExecutor(available=True)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, prompt_executor=executor)

        url = "https://github.com/owner/repo/issues/123"
        result = runner.invoke(implement, [url], obj=ctx)

        assert result.exit_code == 0
        assert "Created .impl/ folder" in result.output

        # Verify plan-ref.json contains correct plan ID
        plan_ref_path = env.cwd / ".impl" / "plan-ref.json"
        plan_ref_content = plan_ref_path.read_text(encoding="utf-8")
        assert '"plan_id": "123"' in plan_ref_content


def test_implement_creates_impl_folder_in_cwd() -> None:
    """Test that implement creates .impl/ folder in current directory."""
    plan_issue = create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        executor = FakePromptExecutor(available=True)
        ctx = build_workspace_test_context(env, git=git, plan_store=store, prompt_executor=executor)

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
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
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
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
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
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
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
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
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
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
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


def test_implement_from_issue_closes_review_pr() -> None:
    """Test that implementing from an issue closes its associated review PR."""
    # Build issue body with plan-header metadata containing review_pr: 99
    issue_body = format_plan_header_body_for_test()
    issue_body_with_review_pr = update_plan_header_review_pr(issue_body, 99)

    # Create IssueInfo objects with plan-header metadata in the issue body.
    # cleanup_review_pr reads review_pr via ctx.plan_backend.get_metadata_field(),
    # so the plan store must be backed by the same FakeGitHubIssues that has
    # the plan-header metadata block.
    issue_42 = IssueInfo(
        number=42,
        title="Add Authentication Feature",
        body=issue_body_with_review_pr,
        state="OPEN",
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan", "enhancement"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        author="test-author",
    )
    # Review PR issue (must exist for add_comment to succeed)
    issue_99 = IssueInfo(
        number=99,
        title="Review PR for plan #42",
        body="Review PR body",
        state="OPEN",
        url="https://github.com/owner/repo/pull/99",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        author="test-author",
    )
    fake_issues = FakeGitHubIssues(issues={42: issue_42, 99: issue_99})
    fake_github = FakeGitHub(issues_gateway=fake_issues)

    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        executor = FakePromptExecutor(available=True)
        ctx = build_workspace_test_context(
            env,
            git=git,
            prompt_executor=executor,
            issues=fake_issues,
            github=fake_github,
        )

        result = runner.invoke(implement, ["#42"], obj=ctx)

        assert result.exit_code == 0
        assert "Created .impl/ folder" in result.output

        # Review PR was closed
        assert 99 in fake_github.closed_prs

        # Comment was added to review PR explaining why it was closed
        comment_bodies = [body for num, body, _ in fake_issues.added_comments if num == 99]
        assert len(comment_bodies) == 1
        assert "automatically closed" in comment_bodies[0]

        # Issue body was updated to clear review_pr metadata
        updated_bodies = [body for num, body in fake_issues.updated_bodies if num == 42]
        assert len(updated_bodies) == 1
        assert "review_pr: null" in updated_bodies[0] or "review_pr:" in updated_bodies[0]

        # .impl/ folder was created (normal implement behavior still works)
        assert (env.cwd / ".impl").exists()
