"""Tests for GitHub URL parsing utilities."""

from erk_shared.github.parsing import (
    construct_issue_url,
    construct_pr_url,
    construct_workflow_run_url,
    extract_owner_repo_from_github_url,
    parse_issue_number_from_url,
    parse_pr_number_from_url,
)

# Tests for parse_issue_number_from_url


def test_parse_issue_number_from_simple_url() -> None:
    """Test parsing issue number from a standard issue URL."""
    url = "https://github.com/owner/repo/issues/123"
    assert parse_issue_number_from_url(url) == 123


def test_parse_issue_number_from_url_with_fragment() -> None:
    """Test parsing issue number from URL with fragment (anchor)."""
    url = "https://github.com/owner/repo/issues/456#issuecomment-789"
    assert parse_issue_number_from_url(url) == 456


def test_parse_issue_number_from_url_with_query_string() -> None:
    """Test parsing issue number from URL with query parameters."""
    url = "https://github.com/owner/repo/issues/789?something=value"
    assert parse_issue_number_from_url(url) == 789


def test_parse_issue_number_returns_none_for_invalid_url() -> None:
    """Test that non-matching URLs return None."""
    assert parse_issue_number_from_url("https://github.com/owner/repo") is None
    assert parse_issue_number_from_url("https://github.com/owner/repo/pull/123") is None
    assert parse_issue_number_from_url("not-a-url") is None
    assert parse_issue_number_from_url("") is None


def test_parse_issue_number_returns_none_for_enterprise_url() -> None:
    """Test that GitHub Enterprise URLs return None (strict github.com matching)."""
    url = "https://github.company.com/owner/repo/issues/123"
    assert parse_issue_number_from_url(url) is None


# Tests for parse_pr_number_from_url


def test_parse_pr_number_from_simple_url() -> None:
    """Test parsing PR number from a standard PR URL."""
    url = "https://github.com/owner/repo/pull/123"
    assert parse_pr_number_from_url(url) == 123


def test_parse_pr_number_from_url_with_fragment() -> None:
    """Test parsing PR number from URL with fragment (anchor)."""
    url = "https://github.com/owner/repo/pull/456#discussion_r789"
    assert parse_pr_number_from_url(url) == 456


def test_parse_pr_number_from_url_with_query_string() -> None:
    """Test parsing PR number from URL with query parameters."""
    url = "https://github.com/owner/repo/pull/789?diff=unified"
    assert parse_pr_number_from_url(url) == 789


def test_parse_pr_number_returns_none_for_invalid_url() -> None:
    """Test that non-matching URLs return None."""
    assert parse_pr_number_from_url("https://github.com/owner/repo") is None
    assert parse_pr_number_from_url("https://github.com/owner/repo/issues/123") is None
    assert parse_pr_number_from_url("not-a-url") is None
    assert parse_pr_number_from_url("") is None


def test_parse_pr_number_returns_none_for_enterprise_url() -> None:
    """Test that GitHub Enterprise URLs return None (strict github.com matching)."""
    url = "https://github.company.com/owner/repo/pull/123"
    assert parse_pr_number_from_url(url) is None


# Tests for extract_owner_repo_from_github_url


def test_extract_owner_repo_from_issue_url() -> None:
    """Test extracting owner/repo from issue URL."""
    url = "https://github.com/dagster-io/erk/issues/123"
    assert extract_owner_repo_from_github_url(url) == ("dagster-io", "erk")


def test_extract_owner_repo_from_pr_url() -> None:
    """Test extracting owner/repo from PR URL."""
    url = "https://github.com/dagster-io/erk/pull/456"
    assert extract_owner_repo_from_github_url(url) == ("dagster-io", "erk")


def test_extract_owner_repo_from_base_url() -> None:
    """Test extracting owner/repo from base repo URL."""
    url = "https://github.com/dagster-io/erk"
    assert extract_owner_repo_from_github_url(url) == ("dagster-io", "erk")


def test_extract_owner_repo_from_base_url_with_trailing_slash() -> None:
    """Test extracting owner/repo from base repo URL with trailing slash."""
    url = "https://github.com/dagster-io/erk/"
    assert extract_owner_repo_from_github_url(url) == ("dagster-io", "erk")


def test_extract_owner_repo_returns_none_for_invalid_url() -> None:
    """Test that non-GitHub URLs return None."""
    assert extract_owner_repo_from_github_url("not-a-url") is None
    assert extract_owner_repo_from_github_url("https://gitlab.com/owner/repo") is None
    assert extract_owner_repo_from_github_url("") is None


# Tests for URL construction functions


def test_construct_workflow_run_url() -> None:
    """Test constructing workflow run URL."""
    url = construct_workflow_run_url("dagster-io", "erk", 1234567890)
    assert url == "https://github.com/dagster-io/erk/actions/runs/1234567890"


def test_construct_workflow_run_url_with_string_id() -> None:
    """Test constructing workflow run URL with string run ID."""
    url = construct_workflow_run_url("owner", "repo", "9876543210")
    assert url == "https://github.com/owner/repo/actions/runs/9876543210"


def test_construct_pr_url() -> None:
    """Test constructing PR URL."""
    url = construct_pr_url("dagster-io", "erk", 123)
    assert url == "https://github.com/dagster-io/erk/pull/123"


def test_construct_issue_url() -> None:
    """Test constructing issue URL."""
    url = construct_issue_url("dagster-io", "erk", 456)
    assert url == "https://github.com/dagster-io/erk/issues/456"
