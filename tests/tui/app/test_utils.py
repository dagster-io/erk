"""Tests for build_github_url helper function."""

from erk.tui.operations.logic import build_github_url


class TestBuildGithubUrl:
    """Tests for build_github_url helper function."""

    def testbuild_github_url_for_pull_request(self) -> None:
        """build_github_url constructs PR URL from issue URL."""
        issue_url = "https://github.com/owner/repo/issues/123"
        result = build_github_url(issue_url, "pull", 456)
        assert result == "https://github.com/owner/repo/pull/456"

    def testbuild_github_url_for_issue(self) -> None:
        """build_github_url constructs issue URL from issue URL."""
        issue_url = "https://github.com/owner/repo/issues/123"
        result = build_github_url(issue_url, "issues", 789)
        assert result == "https://github.com/owner/repo/issues/789"

    def testbuild_github_url_from_pull_url(self) -> None:
        """build_github_url constructs PR URL from pull URL (plan-as-PR format)."""
        pull_url = "https://github.com/owner/repo/pull/123"
        result = build_github_url(pull_url, "pull", 456)
        assert result == "https://github.com/owner/repo/pull/456"

    def testbuild_github_url_issue_from_pull_url(self) -> None:
        """build_github_url constructs issue URL from pull URL."""
        pull_url = "https://github.com/owner/repo/pull/123"
        result = build_github_url(pull_url, "issues", 789)
        assert result == "https://github.com/owner/repo/issues/789"
