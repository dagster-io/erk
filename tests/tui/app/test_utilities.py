"""Tests for utility functions."""

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
