"""Tests for erk pr address-remote command."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk.cli.constants import PR_ADDRESS_WORKFLOW_NAME
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.types import PRDetails, PullRequestInfo
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.test_utils.plan_helpers import format_plan_header_body_for_test


def _make_pr_info(
    number: int,
    branch: str,
    state: str,
    title: str | None,
) -> PullRequestInfo:
    """Create a PullRequestInfo for testing."""
    return PullRequestInfo(
        number=number,
        state=state,
        url=f"https://github.com/owner/repo/pull/{number}",
        is_draft=False,
        title=title or f"PR #{number}",
        checks_passing=True,
        owner="owner",
        repo="repo",
    )


def _make_pr_details(
    number: int,
    *,
    head_ref_name: str,
    state: str,
    base_ref_name: str,
    title: str | None,
) -> PRDetails:
    """Create a PRDetails for testing."""
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title=f"PR #{number}" if title is None else title,
        body="",
        state=state,
        is_draft=False,
        base_ref_name=base_ref_name,
        head_ref_name=head_ref_name,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )


def test_address_remote_triggers_workflow(tmp_path: Path) -> None:
    """Test successful workflow trigger with default options."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Setup PR info
        pr_info = _make_pr_info(123, "feature-branch", "OPEN", "Add feature")
        pr_details = _make_pr_details(
            number=123,
            head_ref_name="feature-branch",
            state="OPEN",
            base_ref_name="main",
            title="Add feature",
        )
        github = FakeGitHub(
            prs={"feature-branch": pr_info},
            pr_details={123: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["address-remote", "123"], obj=ctx)

        assert result.exit_code == 0
        assert "PR #123" in result.output
        assert "Add feature" in result.output
        assert "Workflow triggered" in result.output
        assert "Run URL:" in result.output

        # Verify workflow was triggered with correct inputs
        assert len(github.triggered_workflows) == 1
        workflow, inputs = github.triggered_workflows[0]
        assert workflow == PR_ADDRESS_WORKFLOW_NAME
        assert inputs["pr_number"] == "123"
        assert "model_name" not in inputs  # Not specified


def test_address_remote_requires_pr_number(tmp_path: Path) -> None:
    """Test error when PR number is not provided."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git)

        # No PR number argument
        result = runner.invoke(pr_group, ["address-remote"], obj=ctx)

        # Click returns exit code 2 for missing required arguments
        assert result.exit_code == 2
        assert "Missing argument 'PR_NUMBER'" in result.output


def test_address_remote_pr_not_found(tmp_path: Path) -> None:
    """Test error when PR number doesn't exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # No PRs configured
        github = FakeGitHub(prs={}, pr_details={})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["address-remote", "999"], obj=ctx)

        assert result.exit_code == 1
        assert "No pull request found with number #999" in result.output


def test_address_remote_pr_not_open(tmp_path: Path) -> None:
    """Test error when PR is closed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # PR is closed
        pr_info = _make_pr_info(111, "closed-branch", "CLOSED", "Closed PR")
        pr_details = _make_pr_details(
            number=111,
            head_ref_name="closed-branch",
            state="CLOSED",
            base_ref_name="main",
            title="Closed PR",
        )
        github = FakeGitHub(
            prs={"closed-branch": pr_info},
            pr_details={111: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["address-remote", "111"], obj=ctx)

        assert result.exit_code == 1
        assert "Cannot address comments on CLOSED PR" in result.output


def test_address_remote_pr_merged(tmp_path: Path) -> None:
    """Test error when PR is merged."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # PR is merged
        pr_info = _make_pr_info(222, "merged-branch", "MERGED", "Merged PR")
        pr_details = _make_pr_details(
            number=222,
            head_ref_name="merged-branch",
            state="MERGED",
            base_ref_name="main",
            title="Merged PR",
        )
        github = FakeGitHub(
            prs={"merged-branch": pr_info},
            pr_details={222: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["address-remote", "222"], obj=ctx)

        assert result.exit_code == 1
        assert "Cannot address comments on MERGED PR" in result.output


def test_address_remote_model_option(tmp_path: Path) -> None:
    """Test workflow trigger with custom model."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        pr_info = _make_pr_info(789, "feature-branch", "OPEN", "Feature")
        pr_details = _make_pr_details(
            number=789,
            head_ref_name="feature-branch",
            state="OPEN",
            base_ref_name="main",
            title="Feature",
        )
        github = FakeGitHub(
            prs={"feature-branch": pr_info},
            pr_details={789: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            pr_group, ["address-remote", "789", "--model", "claude-opus-4"], obj=ctx
        )

        assert result.exit_code == 0

        # Verify model is passed
        assert len(github.triggered_workflows) == 1
        _, inputs = github.triggered_workflows[0]
        assert inputs["model_name"] == "claude-opus-4"


def _make_issue_info(
    number: int,
    body: str,
    *,
    title: str | None,
    state: str,
) -> IssueInfo:
    """Create an IssueInfo for testing."""
    # Use fixed timestamp for deterministic test data
    fixed_timestamp = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
    return IssueInfo(
        number=number,
        title=title or f"Issue #{number}",
        body=body,
        state=state,
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=fixed_timestamp,
        updated_at=fixed_timestamp,
        author="testuser",
    )


def test_address_remote_updates_dispatch_metadata_for_plan_branch(tmp_path: Path) -> None:
    """Test that dispatch metadata is updated when branch follows P-pattern."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Branch follows P{issue_number}-{slug} pattern
        branch_name = "P123-fix-auth-bug-01-15-1430"

        # Create plan issue with plan-header block
        plan_body = format_plan_header_body_for_test(
            created_at="2024-01-15T14:30:00Z",
            created_by="testuser",
        )
        plan_issue = _make_issue_info(123, plan_body, title="Fix auth bug", state="OPEN")
        issues_gateway = FakeGitHubIssues(issues={123: plan_issue})

        pr_info = _make_pr_info(456, branch_name, "OPEN", "Fix auth bug")
        pr_details = _make_pr_details(
            number=456,
            head_ref_name=branch_name,
            state="OPEN",
            base_ref_name="main",
            title="Fix auth bug",
        )
        github = FakeGitHub(
            prs={branch_name: pr_info},
            pr_details={456: pr_details},
            issues_gateway=issues_gateway,
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["address-remote", "456"], obj=ctx)

        assert result.exit_code == 0
        assert "Workflow triggered" in result.output
        assert "Updated dispatch metadata on plan #123" in result.output

        # Verify issue body was updated with dispatch metadata
        assert len(issues_gateway.updated_bodies) == 1
        updated_issue_number, updated_body = issues_gateway.updated_bodies[0]
        assert updated_issue_number == 123
        assert "last_dispatched_run_id" in updated_body
        assert "last_dispatched_node_id" in updated_body


def test_address_remote_skips_metadata_for_non_plan_branch(tmp_path: Path) -> None:
    """Test that no metadata update occurs for branches without P-pattern."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Branch does NOT follow P{issue_number}-{slug} pattern
        branch_name = "feature-branch"

        pr_info = _make_pr_info(123, branch_name, "OPEN", "Add feature")
        pr_details = _make_pr_details(
            number=123,
            head_ref_name=branch_name,
            state="OPEN",
            base_ref_name="main",
            title="Add feature",
        )

        issues_gateway = FakeGitHubIssues()
        github = FakeGitHub(
            prs={branch_name: pr_info},
            pr_details={123: pr_details},
            issues_gateway=issues_gateway,
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["address-remote", "123"], obj=ctx)

        assert result.exit_code == 0
        assert "Workflow triggered" in result.output
        # Should NOT see dispatch metadata update message
        assert "Updated dispatch metadata" not in result.output

        # Verify no issue updates occurred
        assert len(issues_gateway.updated_bodies) == 0
