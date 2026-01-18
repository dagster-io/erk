"""Tests for erk pr fix-conflicts-remote command."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk.cli.constants import REBASE_WORKFLOW_NAME
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.metadata.plan_header import format_plan_header_body
from erk_shared.github.types import PRDetails, PullRequestInfo
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


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


def test_fix_conflicts_remote_triggers_workflow(tmp_path: Path) -> None:
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
            current_branches={env.cwd: "feature-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["fix-conflicts-remote"], obj=ctx)

        assert result.exit_code == 0
        assert "PR #123" in result.output
        assert "Add feature" in result.output
        assert "Base branch: main" in result.output
        assert "Workflow triggered" in result.output
        assert "Run URL:" in result.output

        # Verify workflow was triggered with correct inputs
        assert len(github.triggered_workflows) == 1
        workflow, inputs = github.triggered_workflows[0]
        assert workflow == REBASE_WORKFLOW_NAME
        assert inputs["branch_name"] == "feature-branch"
        assert inputs["base_branch"] == "main"
        assert inputs["pr_number"] == "123"
        assert inputs["squash"] == "true"
        assert "model_name" not in inputs  # Not specified


def test_fix_conflicts_remote_with_no_squash(tmp_path: Path) -> None:
    """Test workflow trigger with --no-squash flag."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        pr_info = _make_pr_info(456, "bugfix-branch", "OPEN", "Fix bug")
        pr_details = _make_pr_details(
            number=456,
            head_ref_name="bugfix-branch",
            state="OPEN",
            base_ref_name="main",
            title="Fix bug",
        )
        github = FakeGitHub(
            prs={"bugfix-branch": pr_info},
            pr_details={456: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "bugfix-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["fix-conflicts-remote", "--no-squash"], obj=ctx)

        assert result.exit_code == 0

        # Verify squash is false
        assert len(github.triggered_workflows) == 1
        _, inputs = github.triggered_workflows[0]
        assert inputs["squash"] == "false"


def test_fix_conflicts_remote_with_model(tmp_path: Path) -> None:
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
            current_branches={env.cwd: "feature-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            pr_group, ["fix-conflicts-remote", "--model", "claude-opus-4"], obj=ctx
        )

        assert result.exit_code == 0

        # Verify model is passed
        assert len(github.triggered_workflows) == 1
        _, inputs = github.triggered_workflows[0]
        assert inputs["model_name"] == "claude-opus-4"


def test_fix_conflicts_remote_fails_when_not_on_branch(tmp_path: Path) -> None:
    """Test error when on detached HEAD."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Detached HEAD (no current branch)
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: None},
        )

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(pr_group, ["fix-conflicts-remote"], obj=ctx)

        assert result.exit_code == 1
        assert "Not on a branch" in result.output


def test_fix_conflicts_remote_fails_when_no_pr_exists(tmp_path: Path) -> None:
    """Test error when branch has no PR."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # No PR for this branch
        github = FakeGitHub(prs={}, pr_details={})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "no-pr-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["fix-conflicts-remote"], obj=ctx)

        assert result.exit_code == 1
        assert "No pull request found for branch 'no-pr-branch'" in result.output


def test_fix_conflicts_remote_fails_when_pr_is_closed(tmp_path: Path) -> None:
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
            current_branches={env.cwd: "closed-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["fix-conflicts-remote"], obj=ctx)

        assert result.exit_code == 1
        assert "Cannot rebase CLOSED PR" in result.output


def test_fix_conflicts_remote_fails_when_pr_is_merged(tmp_path: Path) -> None:
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
            current_branches={env.cwd: "merged-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["fix-conflicts-remote"], obj=ctx)

        assert result.exit_code == 1
        assert "Cannot rebase MERGED PR" in result.output


def test_fix_conflicts_remote_uses_correct_base_branch(tmp_path: Path) -> None:
    """Test that the correct base branch is passed to workflow."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # PR targets release branch, not main
        pr_info = _make_pr_info(333, "hotfix-branch", "OPEN", "Hotfix")
        pr_details = _make_pr_details(
            number=333,
            head_ref_name="hotfix-branch",
            state="OPEN",
            base_ref_name="release/v1.0",  # Non-standard base
            title="Hotfix",
        )
        github = FakeGitHub(
            prs={"hotfix-branch": pr_info},
            pr_details={333: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "hotfix-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["fix-conflicts-remote"], obj=ctx)

        assert result.exit_code == 0
        assert "Base branch: release/v1.0" in result.output

        # Verify correct base branch in workflow inputs
        assert len(github.triggered_workflows) == 1
        _, inputs = github.triggered_workflows[0]
        assert inputs["base_branch"] == "release/v1.0"


def test_fix_conflicts_remote_with_pr_number_argument(tmp_path: Path) -> None:
    """Test triggering workflow via explicit PR number (without being on the branch)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Setup PR - note the branch is different from current branch
        pr_info = _make_pr_info(456, "other-feature", "OPEN", "Other Feature")
        pr_details = _make_pr_details(
            number=456,
            head_ref_name="other-feature",
            state="OPEN",
            base_ref_name="main",
            title="Other Feature",
        )
        github = FakeGitHub(
            prs={"other-feature": pr_info},
            pr_details={456: pr_details},
        )

        # We're on a different branch (or even master)
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        # Pass PR number as argument
        result = runner.invoke(pr_group, ["fix-conflicts-remote", "456"], obj=ctx)

        assert result.exit_code == 0
        assert "PR #456" in result.output
        assert "Other Feature" in result.output
        assert "Workflow triggered" in result.output

        # Verify workflow was triggered with the PR's branch, not current branch
        assert len(github.triggered_workflows) == 1
        _, inputs = github.triggered_workflows[0]
        assert inputs["branch_name"] == "other-feature"
        assert inputs["pr_number"] == "456"


def test_fix_conflicts_remote_with_pr_number_not_found(tmp_path: Path) -> None:
    """Test error when explicit PR number doesn't exist."""
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

        result = runner.invoke(pr_group, ["fix-conflicts-remote", "999"], obj=ctx)

        assert result.exit_code == 1
        assert "No pull request found with number #999" in result.output


def test_fix_conflicts_remote_with_pr_number_closed(tmp_path: Path) -> None:
    """Test error when explicit PR number refers to a closed PR."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # PR is closed
        pr_info = _make_pr_info(111, "closed-feature", "CLOSED", "Closed Feature")
        pr_details = _make_pr_details(
            number=111,
            head_ref_name="closed-feature",
            state="CLOSED",
            base_ref_name="main",
            title="Closed Feature",
        )
        github = FakeGitHub(
            prs={"closed-feature": pr_info},
            pr_details={111: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["fix-conflicts-remote", "111"], obj=ctx)

        assert result.exit_code == 1
        assert "Cannot rebase CLOSED PR" in result.output


def test_fix_conflicts_remote_with_pr_number_on_detached_head(tmp_path: Path) -> None:
    """Test that PR number argument works even when on detached HEAD."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Setup PR
        pr_info = _make_pr_info(789, "feature-x", "OPEN", "Feature X")
        pr_details = _make_pr_details(
            number=789,
            head_ref_name="feature-x",
            state="OPEN",
            base_ref_name="main",
            title="Feature X",
        )
        github = FakeGitHub(
            prs={"feature-x": pr_info},
            pr_details={789: pr_details},
        )

        # Detached HEAD (no current branch)
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: None},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        # Should work with PR number even though we're on detached HEAD
        result = runner.invoke(pr_group, ["fix-conflicts-remote", "789"], obj=ctx)

        assert result.exit_code == 0
        assert "PR #789" in result.output
        assert "Feature X" in result.output
        assert "Workflow triggered" in result.output

        # Verify correct branch name from PR
        assert len(github.triggered_workflows) == 1
        _, inputs = github.triggered_workflows[0]
        assert inputs["branch_name"] == "feature-x"


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


def test_fix_conflicts_remote_updates_dispatch_metadata_for_plan_branch(tmp_path: Path) -> None:
    """Test that dispatch metadata is updated when branch follows P-pattern."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Branch follows P{issue_number}-{slug} pattern
        branch_name = "P123-fix-auth-bug-01-15-1430"

        # Create plan issue with plan-header block
        plan_body = format_plan_header_body(
            created_at="2024-01-15T14:30:00Z",
            created_by="testuser",
            worktree_name=None,
            branch_name=None,
            plan_comment_id=None,
            last_dispatched_run_id=None,
            last_dispatched_node_id=None,
            last_dispatched_at=None,
            last_local_impl_at=None,
            last_local_impl_event=None,
            last_local_impl_session=None,
            last_local_impl_user=None,
            last_remote_impl_at=None,
            source_repo=None,
            objective_issue=None,
            created_from_session=None,
            last_learn_session=None,
            last_learn_at=None,
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
            current_branches={env.cwd: branch_name},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["fix-conflicts-remote"], obj=ctx)

        assert result.exit_code == 0
        assert "Workflow triggered" in result.output
        assert "Updated dispatch metadata on plan #123" in result.output

        # Verify issue body was updated with dispatch metadata
        assert len(issues_gateway.updated_bodies) == 1
        updated_issue_number, updated_body = issues_gateway.updated_bodies[0]
        assert updated_issue_number == 123
        assert "last_dispatched_run_id" in updated_body
        assert "last_dispatched_node_id" in updated_body


def test_fix_conflicts_remote_skips_metadata_for_non_plan_branch(tmp_path: Path) -> None:
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
            current_branches={env.cwd: branch_name},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["fix-conflicts-remote"], obj=ctx)

        assert result.exit_code == 0
        assert "Workflow triggered" in result.output
        # Should NOT see dispatch metadata update message
        assert "Updated dispatch metadata" not in result.output

        # Verify no issue updates occurred
        assert len(issues_gateway.updated_bodies) == 0


def test_fix_conflicts_remote_handles_missing_plan_header_gracefully(tmp_path: Path) -> None:
    """Test that command succeeds when plan issue has no plan-header block."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Branch follows P{issue_number}-{slug} pattern
        branch_name = "P456-fix-bug-01-15-1430"

        # Issue exists but has no plan-header block (just plain text)
        plain_issue = _make_issue_info(
            456, "This is a regular issue body without metadata", title=None, state="OPEN"
        )
        issues_gateway = FakeGitHubIssues(issues={456: plain_issue})

        pr_info = _make_pr_info(789, branch_name, "OPEN", "Fix bug")
        pr_details = _make_pr_details(
            number=789,
            head_ref_name=branch_name,
            state="OPEN",
            base_ref_name="main",
            title="Fix bug",
        )
        github = FakeGitHub(
            prs={branch_name: pr_info},
            pr_details={789: pr_details},
            issues_gateway=issues_gateway,
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: branch_name},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["fix-conflicts-remote"], obj=ctx)

        # Command should succeed even though plan-header update failed
        assert result.exit_code == 0
        assert "Workflow triggered" in result.output
        # Should NOT see error or warning about plan header (ValueError is silently caught)
        assert "Updated dispatch metadata" not in result.output

        # Verify no issue updates occurred (update failed due to missing plan-header)
        assert len(issues_gateway.updated_bodies) == 0
