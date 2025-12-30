"""Tests for PR reference parsing utility."""

import pytest

from erk.cli.commands.pr.parse_pr_reference import parse_pr_reference


def test_parse_plain_number() -> None:
    """Test parsing a plain PR number."""
    assert parse_pr_reference("123") == 123


def test_parse_plain_number_with_leading_zeros() -> None:
    """Test parsing a plain number with leading zeros."""
    assert parse_pr_reference("0042") == 42


def test_parse_github_pull_url() -> None:
    """Test parsing a GitHub pull request URL."""
    url = "https://github.com/owner/repo/pull/456"
    assert parse_pr_reference(url) == 456


def test_parse_github_url_with_query_string() -> None:
    """Test parsing a GitHub URL with query parameters."""
    url = "https://github.com/owner/repo/pull/789?diff=unified"
    assert parse_pr_reference(url) == 789


def test_parse_github_url_with_fragment() -> None:
    """Test parsing a GitHub URL with a fragment (anchor)."""
    url = "https://github.com/owner/repo/pull/101#issuecomment-12345"
    assert parse_pr_reference(url) == 101


def test_parse_github_url_with_query_and_fragment() -> None:
    """Test parsing a GitHub URL with both query and fragment."""
    url = "https://github.com/owner/repo/pull/202?diff=split#discussion_r12345"
    assert parse_pr_reference(url) == 202


def test_parse_invalid_text() -> None:
    """Test that non-numeric text raises SystemExit."""
    with pytest.raises(SystemExit) as exc_info:
        parse_pr_reference("not-a-number")
    assert exc_info.value.code == 1


def test_parse_empty_string() -> None:
    """Test that empty string raises SystemExit."""
    with pytest.raises(SystemExit) as exc_info:
        parse_pr_reference("")
    assert exc_info.value.code == 1


def test_parse_url_without_number() -> None:
    """Test that URL without PR number raises SystemExit."""
    with pytest.raises(SystemExit) as exc_info:
        parse_pr_reference("https://github.com/owner/repo")
    assert exc_info.value.code == 1


def test_parse_issues_url_rejected() -> None:
    """Test that /issues/ URLs are rejected (only /pull/ URLs accepted)."""
    with pytest.raises(SystemExit) as exc_info:
        parse_pr_reference("https://github.com/owner/repo/issues/303")
    assert exc_info.value.code == 1


def test_parse_large_pr_number() -> None:
    """Test parsing a large PR number."""
    assert parse_pr_reference("99999") == 99999


def test_parse_github_enterprise_url_not_supported() -> None:
    """Test that GitHub Enterprise URLs are not supported (require github.com)."""
    with pytest.raises(SystemExit) as exc_info:
        parse_pr_reference("https://github.company.com/org/repo/pull/888")
    assert exc_info.value.code == 1


def test_parse_branch_name_with_numbers_fails() -> None:
    """Test that branch names with embedded numbers are rejected."""
    with pytest.raises(SystemExit) as exc_info:
        parse_pr_reference("P3465-eliminate-kit-yaml-and-cl-12-30-0922")
    assert exc_info.value.code == 1
