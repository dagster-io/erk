"""Tests for SubmitService."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo
from erk_shared.github.types import PullRequestInfo
from erk_shared.integrations.time.fake import FakeTime
from erk_shared.plan_store.fake import FakePlanStore
from erk_shared.plan_store.types import Plan, PlanState

from erk.core.git.fake import FakeGit
from erk.core.github.fake import FakeGitHub
from erk.core.services.submit_service import (
    SubmitResult,
    SubmitService,
    SubmitValidationError,
    ValidatedIssue,
)
from tests.fakes.issue_link_branches import FakeIssueLinkBranches


def _make_issue(
    number: int,
    title: str = "Test Issue",
    labels: list[str] | None = None,
    state: str = "OPEN",
) -> IssueInfo:
    """Create a test IssueInfo with sensible defaults."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=title,
        body="Test body",
        state=state,
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=labels or ["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
    )


def _make_plan(identifier: str, body: str = "Plan content") -> Plan:
    """Create a test Plan with sensible defaults."""
    now = datetime.now(UTC)
    return Plan(
        plan_identifier=identifier,
        title="Test Plan",
        body=body,
        state=PlanState.OPEN,
        url=f"https://github.com/owner/repo/issues/{identifier}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        metadata={},
    )


class TestSubmitServiceValidation:
    """Tests for SubmitService.validate_issue()."""

    def test_validates_issue_with_erk_plan_label(self) -> None:
        """Issue with erk-plan label passes validation."""
        repo_root = Path("/test/repo")
        issue = _make_issue(42, labels=["erk-plan"])
        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_git = FakeGit(trunk_branches={repo_root: "main"})
        fake_github = FakeGitHub()
        fake_issue_links = FakeIssueLinkBranches()
        fake_time = FakeTime()
        fake_plan_store = FakePlanStore()

        service = SubmitService(
            git=fake_git,
            github=fake_github,
            github_issues=fake_issues,
            plan_store=fake_plan_store,
            issue_link_branches=fake_issue_links,
            time_provider=fake_time,
        )

        result = service.validate_issue(repo_root, 42)

        assert result.number == 42
        assert result.issue.title == "Test Issue"

    def test_rejects_issue_without_erk_plan_label(self) -> None:
        """Issue without erk-plan label raises SubmitValidationError."""
        repo_root = Path("/test/repo")
        issue = _make_issue(42, labels=["bug"])
        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_git = FakeGit(trunk_branches={repo_root: "main"})
        fake_github = FakeGitHub()
        fake_issue_links = FakeIssueLinkBranches()
        fake_time = FakeTime()
        fake_plan_store = FakePlanStore()

        service = SubmitService(
            git=fake_git,
            github=fake_github,
            github_issues=fake_issues,
            plan_store=fake_plan_store,
            issue_link_branches=fake_issue_links,
            time_provider=fake_time,
        )

        with pytest.raises(SubmitValidationError) as exc_info:
            service.validate_issue(repo_root, 42)

        assert "does not have erk-plan label" in str(exc_info.value)

    def test_rejects_closed_issue(self) -> None:
        """Closed issue raises SubmitValidationError."""
        repo_root = Path("/test/repo")
        issue = _make_issue(42, labels=["erk-plan"], state="CLOSED")
        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_git = FakeGit(trunk_branches={repo_root: "main"})
        fake_github = FakeGitHub()
        fake_issue_links = FakeIssueLinkBranches()
        fake_time = FakeTime()
        fake_plan_store = FakePlanStore()

        service = SubmitService(
            git=fake_git,
            github=fake_github,
            github_issues=fake_issues,
            plan_store=fake_plan_store,
            issue_link_branches=fake_issue_links,
            time_provider=fake_time,
        )

        with pytest.raises(SubmitValidationError) as exc_info:
            service.validate_issue(repo_root, 42)

        assert "is CLOSED" in str(exc_info.value)

    def test_raises_error_for_nonexistent_issue(self) -> None:
        """Non-existent issue raises SubmitValidationError."""
        repo_root = Path("/test/repo")
        fake_issues = FakeGitHubIssues()  # No issues
        fake_git = FakeGit(trunk_branches={repo_root: "main"})
        fake_github = FakeGitHub()
        fake_issue_links = FakeIssueLinkBranches()
        fake_time = FakeTime()
        fake_plan_store = FakePlanStore()

        service = SubmitService(
            git=fake_git,
            github=fake_github,
            github_issues=fake_issues,
            plan_store=fake_plan_store,
            issue_link_branches=fake_issue_links,
            time_provider=fake_time,
        )

        with pytest.raises(SubmitValidationError) as exc_info:
            service.validate_issue(repo_root, 999)

        assert "not found" in str(exc_info.value)

    def test_detects_existing_branch_with_pr(self) -> None:
        """Validation detects existing branch with PR."""
        repo_root = Path("/test/repo")
        issue = _make_issue(42)
        fake_issues = FakeGitHubIssues(issues={42: issue})
        # Simulate existing branch on remote
        fake_git = FakeGit(
            trunk_branches={repo_root: "main"},
            remote_branches={repo_root: ["origin/42-test-issue-11-30-1234"]},
        )
        # Simulate existing PR
        fake_github = FakeGitHub(pr_statuses={"42-test-issue-11-30-1234": ("OPEN", 123, "Test PR")})
        fake_issue_links = FakeIssueLinkBranches(existing_branches={42: "42-test-issue-11-30-1234"})
        fake_time = FakeTime()
        fake_plan_store = FakePlanStore()

        service = SubmitService(
            git=fake_git,
            github=fake_github,
            github_issues=fake_issues,
            plan_store=fake_plan_store,
            issue_link_branches=fake_issue_links,
            time_provider=fake_time,
        )

        result = service.validate_issue(repo_root, 42)

        assert result.branch_exists is True
        assert result.pr_number == 123


class TestSubmitServiceSubmit:
    """Tests for SubmitService.submit()."""

    def test_creates_branch_and_pr_for_new_submission(self, tmp_path: Path) -> None:
        """New submission creates branch, commits, and creates draft PR."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        issue = _make_issue(42, title="Test Feature")
        plan = _make_plan("42", body="Implementation plan content")

        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_git = FakeGit(
            trunk_branches={repo_root: "main"},
            worktrees={repo_root: []},
            existing_paths={repo_root},
        )
        fake_github = FakeGitHub()
        fake_issue_links = FakeIssueLinkBranches()
        fake_time = FakeTime()
        fake_plan_store = FakePlanStore(plans={"42": plan})

        service = SubmitService(
            git=fake_git,
            github=fake_github,
            github_issues=fake_issues,
            plan_store=fake_plan_store,
            issue_link_branches=fake_issue_links,
            time_provider=fake_time,
        )

        validated = ValidatedIssue(
            number=42,
            issue=issue,
            branch_name="42-test-feature-11-30-1234",
            branch_exists=False,
            pr_number=None,
        )

        result = service.submit(repo_root, validated, "test-user")

        assert result.issue_number == 42
        assert result.pr_number == 999  # FakeGitHub returns 999
        assert "1234567890" in result.run_id  # FakeGitHub returns this run_id

        # Verify branch was pushed
        assert len(fake_git.pushed_branches) == 1
        assert fake_git.pushed_branches[0][1] == "42-test-feature-11-30-1234"

        # Verify PR was created
        assert len(fake_github.created_prs) == 1
        branch, title, body, base, draft = fake_github.created_prs[0]
        assert branch == "42-test-feature-11-30-1234"
        assert draft is True
        assert "Test Feature" in title

        # Verify workflow was triggered
        assert len(fake_github.triggered_workflows) == 1
        workflow, inputs = fake_github.triggered_workflows[0]
        assert inputs["issue_number"] == "42"
        assert inputs["submitted_by"] == "test-user"

    def test_reuses_existing_branch_with_pr(self, tmp_path: Path) -> None:
        """Existing branch with PR just triggers workflow."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        issue = _make_issue(42)

        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_git = FakeGit(trunk_branches={repo_root: "main"})
        fake_github = FakeGitHub()
        fake_issue_links = FakeIssueLinkBranches()
        fake_time = FakeTime()
        fake_plan_store = FakePlanStore()

        service = SubmitService(
            git=fake_git,
            github=fake_github,
            github_issues=fake_issues,
            plan_store=fake_plan_store,
            issue_link_branches=fake_issue_links,
            time_provider=fake_time,
        )

        validated = ValidatedIssue(
            number=42,
            issue=issue,
            branch_name="42-test-issue-11-30-1234",
            branch_exists=True,
            pr_number=123,  # PR already exists
        )

        result = service.submit(repo_root, validated, "test-user")

        assert result.pr_number == 123

        # Should NOT create a new PR
        assert len(fake_github.created_prs) == 0

        # Should still trigger workflow
        assert len(fake_github.triggered_workflows) == 1

    def test_closes_orphaned_draft_prs(self, tmp_path: Path) -> None:
        """Submission closes old draft PRs for the same issue."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        issue = _make_issue(42)
        plan = _make_plan("42")

        # Simulate existing orphaned draft PRs
        old_pr = PullRequestInfo(
            number=100,
            state="OPEN",
            url="https://github.com/owner/repo/pull/100",
            is_draft=True,
            title="Old PR",
            checks_passing=None,
            owner="owner",
            repo="repo",
            labels=["erk-plan"],  # Has erk-plan label so it gets closed
        )

        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_git = FakeGit(
            trunk_branches={repo_root: "main"},
            existing_paths={repo_root},
        )
        fake_github = FakeGitHub(pr_issue_linkages={42: [old_pr]})
        fake_issue_links = FakeIssueLinkBranches()
        fake_time = FakeTime()
        fake_plan_store = FakePlanStore(plans={"42": plan})

        service = SubmitService(
            git=fake_git,
            github=fake_github,
            github_issues=fake_issues,
            plan_store=fake_plan_store,
            issue_link_branches=fake_issue_links,
            time_provider=fake_time,
        )

        validated = ValidatedIssue(
            number=42,
            issue=issue,
            branch_name="42-new-branch",
            branch_exists=False,
            pr_number=None,
        )

        result = service.submit(repo_root, validated, "test-user")

        # Old PR should be closed
        assert 100 in fake_github.closed_prs
        # Result should track closed PRs
        assert result.closed_orphan_prs == [100]

    def test_strips_plan_markers_from_pr_title(self, tmp_path: Path) -> None:
        """PR title has Plan: prefix and [erk-plan] suffix stripped."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        issue = _make_issue(42, title="Plan: Add Feature [erk-plan]")
        plan = _make_plan("42")

        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_git = FakeGit(
            trunk_branches={repo_root: "main"},
            existing_paths={repo_root},
        )
        fake_github = FakeGitHub()
        fake_issue_links = FakeIssueLinkBranches()
        fake_time = FakeTime()
        fake_plan_store = FakePlanStore(plans={"42": plan})

        service = SubmitService(
            git=fake_git,
            github=fake_github,
            github_issues=fake_issues,
            plan_store=fake_plan_store,
            issue_link_branches=fake_issue_links,
            time_provider=fake_time,
        )

        validated = ValidatedIssue(
            number=42,
            issue=issue,
            branch_name="42-test-branch",
            branch_exists=False,
            pr_number=None,
        )

        service.submit(repo_root, validated, "test-user")

        # Check PR title was cleaned
        _, title, _, _, _ = fake_github.created_prs[0]
        assert title == "Add Feature"  # Markers stripped


class TestSubmitServiceBranchUniqueness:
    """Tests for branch name uniqueness handling."""

    def test_appends_suffix_for_duplicate_branch_names(self) -> None:
        """Unique branch name is generated when base name exists."""
        repo_root = Path("/test/repo")
        issue = _make_issue(42)

        # Simulate first branch already exists on remote
        fake_git = FakeGit(
            trunk_branches={repo_root: "main"},
            remote_branches={repo_root: ["origin/42-test-issue-11-30-1234"]},
        )
        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_github = FakeGitHub()
        fake_issue_links = FakeIssueLinkBranches()
        fake_time = FakeTime()
        fake_plan_store = FakePlanStore()

        service = SubmitService(
            git=fake_git,
            github=fake_github,
            github_issues=fake_issues,
            plan_store=fake_plan_store,
            issue_link_branches=fake_issue_links,
            time_provider=fake_time,
        )

        unique_name = service._ensure_unique_branch_name(repo_root, "42-test-issue-11-30-1234")

        # Should get a -1 suffix
        assert unique_name == "42-test-issue-11-30-1234-1"


class TestSubmitResult:
    """Tests for SubmitResult dataclass."""

    def test_dataclass_is_frozen(self) -> None:
        """SubmitResult instances are immutable."""
        result = SubmitResult(
            issue_number=42,
            branch_name="test-branch",
            pr_number=123,
            pr_url="https://github.com/owner/repo/pull/123",
            run_id="1234567890",
            workflow_url="https://github.com/owner/repo/actions/runs/1234567890",
            closed_orphan_prs=[],
        )

        with pytest.raises(AttributeError):
            result.issue_number = 99  # type: ignore[misc]

    def test_dataclass_contains_all_fields(self) -> None:
        """SubmitResult has all expected fields."""
        result = SubmitResult(
            issue_number=42,
            branch_name="test-branch",
            pr_number=123,
            pr_url="https://github.com/owner/repo/pull/123",
            run_id="1234567890",
            workflow_url="https://github.com/owner/repo/actions/runs/1234567890",
            closed_orphan_prs=[100, 101],
        )

        assert result.issue_number == 42
        assert result.branch_name == "test-branch"
        assert result.pr_number == 123
        assert result.pr_url == "https://github.com/owner/repo/pull/123"
        assert result.run_id == "1234567890"
        assert "actions/runs" in result.workflow_url
        assert result.closed_orphan_prs == [100, 101]


class TestValidatedIssue:
    """Tests for ValidatedIssue dataclass."""

    def test_dataclass_is_frozen(self) -> None:
        """ValidatedIssue instances are immutable."""
        issue = _make_issue(42)
        validated = ValidatedIssue(
            number=42,
            issue=issue,
            branch_name="test-branch",
            branch_exists=False,
            pr_number=None,
        )

        with pytest.raises(AttributeError):
            validated.number = 99  # type: ignore[misc]
