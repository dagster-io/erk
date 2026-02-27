"""Tests for _build_github_url helper function."""

from erk.tui.app import _build_github_url


class TestBuildGithubUrl:
    """Tests for _build_github_url helper function."""

    def test_build_github_url_for_pull_request(self) -> None:
        """_build_github_url constructs PR URL from issue URL."""
        issue_url = "https://github.com/owner/repo/issues/123"
        result = _build_github_url(issue_url, "pull", 456)
        assert result == "https://github.com/owner/repo/pull/456"

    def test_build_github_url_for_issue(self) -> None:
        """_build_github_url constructs issue URL from issue URL."""
        issue_url = "https://github.com/owner/repo/issues/123"
        result = _build_github_url(issue_url, "issues", 789)
        assert result == "https://github.com/owner/repo/issues/789"

    def test_build_github_url_from_pull_url(self) -> None:
        """_build_github_url constructs PR URL from pull URL (plan-as-PR format)."""
        pull_url = "https://github.com/owner/repo/pull/123"
        result = _build_github_url(pull_url, "pull", 456)
        assert result == "https://github.com/owner/repo/pull/456"

    def test_build_github_url_issue_from_pull_url(self) -> None:
        """_build_github_url constructs issue URL from pull URL."""
        pull_url = "https://github.com/owner/repo/pull/123"
        result = _build_github_url(pull_url, "issues", 789)
        assert result == "https://github.com/owner/repo/issues/789"
