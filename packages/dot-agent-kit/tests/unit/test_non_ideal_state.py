"""Tests for NonIdealState types and GitHubChecks operations."""

from pathlib import Path

from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.types import PRDetails, PullRequestInfo
from erk_shared.non_ideal_state import (
    BranchDetectionFailed,
    GitHubAPIFailed,
    NonIdealState,
    NoPRForBranch,
    PRNotFoundError,
)

from dot_agent_kit.non_ideal_state import GitHubChecks


def make_pr_info(number: int) -> PullRequestInfo:
    """Create a minimal PullRequestInfo for testing."""
    return PullRequestInfo(
        number=number,
        state="OPEN",
        url=f"https://github.com/owner/repo/pull/{number}",
        is_draft=False,
        title="Test PR",
        checks_passing=True,
        owner="owner",
        repo="repo",
    )


def make_pr_details(number: int, branch: str = "feature") -> PRDetails:
    """Create a minimal PRDetails for testing."""
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title="Test PR",
        body="Test body",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name=branch,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )


class TestNonIdealStateProtocol:
    """Tests for NonIdealState marker interface."""

    def test_branch_detection_failed_is_non_ideal_state(self) -> None:
        """BranchDetectionFailed satisfies NonIdealState protocol."""
        error = BranchDetectionFailed()
        assert isinstance(error, NonIdealState)
        assert error.error_type == "branch_detection_failed"
        assert error.message == "Could not determine current branch"

    def test_no_pr_for_branch_is_non_ideal_state(self) -> None:
        """NoPRForBranch satisfies NonIdealState protocol."""
        error = NoPRForBranch(branch="feature-x")
        assert isinstance(error, NonIdealState)
        assert error.error_type == "no_pr_for_branch"
        assert error.message == "No PR found for branch 'feature-x'"

    def test_pr_not_found_error_is_non_ideal_state(self) -> None:
        """PRNotFoundError satisfies NonIdealState protocol."""
        error = PRNotFoundError(pr_number=456)
        assert isinstance(error, NonIdealState)
        assert error.error_type == "pr_not_found"
        assert error.message == "PR #456 not found"

    def test_github_api_failed_is_non_ideal_state(self) -> None:
        """GitHubAPIFailed satisfies NonIdealState protocol."""
        error = GitHubAPIFailed(_message="Connection timeout")
        assert isinstance(error, NonIdealState)
        assert error.error_type == "github_api_failed"
        assert error.message == "Connection timeout"


class TestGitHubChecksBranch:
    """Tests for GitHubChecks.branch()."""

    def test_branch_returns_branch_when_present(self) -> None:
        """branch() returns branch name when not None."""
        result = GitHubChecks.branch("feature-branch")
        assert result == "feature-branch"

    def test_branch_returns_non_ideal_state_when_none(self) -> None:
        """branch() returns BranchDetectionFailed when None."""
        result = GitHubChecks.branch(None)
        assert isinstance(result, BranchDetectionFailed)


class TestGitHubChecksPRForBranch:
    """Tests for GitHubChecks.pr_for_branch()."""

    def test_pr_for_branch_returns_pr_when_found(self, tmp_path: Path) -> None:
        """pr_for_branch() returns PRDetails when PR exists."""
        pr_info = make_pr_info(123)
        pr_details = make_pr_details(123, "feature")
        fake_github = FakeGitHub(
            prs={"feature": pr_info},
            pr_details={123: pr_details},
        )

        result = GitHubChecks.pr_for_branch(fake_github, tmp_path, "feature")
        assert isinstance(result, PRDetails)
        assert result.number == 123

    def test_pr_for_branch_returns_non_ideal_state_when_not_found(self, tmp_path: Path) -> None:
        """pr_for_branch() returns NoPRForBranch when no PR exists."""
        fake_github = FakeGitHub()

        result = GitHubChecks.pr_for_branch(fake_github, tmp_path, "no-pr-branch")
        assert isinstance(result, NoPRForBranch)
        assert result.branch == "no-pr-branch"


class TestGitHubChecksPRByNumber:
    """Tests for GitHubChecks.pr_by_number()."""

    def test_pr_by_number_returns_pr_when_found(self, tmp_path: Path) -> None:
        """pr_by_number() returns PRDetails when PR exists."""
        pr_details = make_pr_details(456)
        fake_github = FakeGitHub(pr_details={456: pr_details})

        result = GitHubChecks.pr_by_number(fake_github, tmp_path, 456)
        assert isinstance(result, PRDetails)
        assert result.number == 456

    def test_pr_by_number_returns_non_ideal_state_when_not_found(self, tmp_path: Path) -> None:
        """pr_by_number() returns PRNotFoundError when PR doesn't exist."""
        fake_github = FakeGitHub()

        result = GitHubChecks.pr_by_number(fake_github, tmp_path, 999)
        assert isinstance(result, PRNotFoundError)
        assert result.pr_number == 999


class TestGitHubChecksAddReaction:
    """Tests for GitHubChecks.add_reaction()."""

    def test_add_reaction_returns_none_on_success(self, tmp_path: Path) -> None:
        """add_reaction() returns None when successful."""
        fake_github_issues = FakeGitHubIssues()

        result = GitHubChecks.add_reaction(fake_github_issues, tmp_path, 123, "+1")
        assert result is None

    def test_add_reaction_returns_non_ideal_state_on_error(self, tmp_path: Path) -> None:
        """add_reaction() returns GitHubAPIFailed when API fails."""
        fake_github_issues = FakeGitHubIssues(add_reaction_error="API rate limit exceeded")

        result = GitHubChecks.add_reaction(fake_github_issues, tmp_path, 123, "+1")
        assert isinstance(result, GitHubAPIFailed)
        assert "API rate limit exceeded" in result.message


class TestGitHubChecksIssueComments:
    """Tests for GitHubChecks.issue_comments()."""

    def test_issue_comments_returns_list_on_success(self, tmp_path: Path) -> None:
        """issue_comments() returns list when successful."""
        fake_github_issues = FakeGitHubIssues()

        result = GitHubChecks.issue_comments(fake_github_issues, tmp_path, 123)
        assert isinstance(result, list)

    def test_issue_comments_returns_non_ideal_state_on_error(self, tmp_path: Path) -> None:
        """issue_comments() returns GitHubAPIFailed when API fails."""
        fake_github_issues = FakeGitHubIssues(get_comments_error="Repository not found")

        result = GitHubChecks.issue_comments(fake_github_issues, tmp_path, 123)
        assert isinstance(result, GitHubAPIFailed)
        assert "Repository not found" in result.message
