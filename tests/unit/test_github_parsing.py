"""Unit tests for GitHub parsing functions with JSON fixtures."""

import pytest
from erk_shared.github.parsing import (
    parse_aggregated_check_counts,
    parse_gh_auth_status_output,
    parse_git_remote_url,
    parse_github_pr_status,
)

from tests.conftest import load_fixture

# Tests for parse_git_remote_url


def test_parse_git_remote_url_https_with_git():
    """Test parsing HTTPS URL with .git suffix."""
    result = parse_git_remote_url("https://github.com/dagster-io/erk.git")
    assert result == ("dagster-io", "erk")


def test_parse_git_remote_url_https_without_git():
    """Test parsing HTTPS URL without .git suffix."""
    result = parse_git_remote_url("https://github.com/dagster-io/erk")
    assert result == ("dagster-io", "erk")


def test_parse_git_remote_url_ssh_with_git():
    """Test parsing SSH URL with .git suffix."""
    result = parse_git_remote_url("git@github.com:dagster-io/erk.git")
    assert result == ("dagster-io", "erk")


def test_parse_git_remote_url_ssh_without_git():
    """Test parsing SSH URL without .git suffix."""
    result = parse_git_remote_url("git@github.com:dagster-io/erk")
    assert result == ("dagster-io", "erk")


def test_parse_git_remote_url_non_github():
    """Test parsing non-GitHub URL raises ValueError."""
    with pytest.raises(ValueError, match="Not a valid GitHub URL"):
        parse_git_remote_url("https://gitlab.com/user/repo.git")


def test_parse_git_remote_url_invalid_format():
    """Test parsing invalid URL format raises ValueError."""
    with pytest.raises(ValueError, match="Not a valid GitHub URL"):
        parse_git_remote_url("not-a-valid-url")


def test_parse_git_remote_url_github_with_subdirectory():
    """Test parsing GitHub URL with subdirectory raises ValueError."""
    with pytest.raises(ValueError, match="Not a valid GitHub URL"):
        parse_git_remote_url("https://github.com/owner/repo/subdir")


# Tests for parse_aggregated_check_counts


def test_parse_aggregated_check_counts_all_passing():
    """Test count parsing when all checks pass."""
    check_run_counts = [
        {"state": "SUCCESS", "count": 5},
        {"state": "SKIPPED", "count": 2},
    ]
    status_context_counts = [
        {"state": "SUCCESS", "count": 1},
    ]

    result = parse_aggregated_check_counts(check_run_counts, status_context_counts, 8)
    assert result == (8, 8)


def test_parse_aggregated_check_counts_mixed():
    """Test count parsing with mixed results."""
    check_run_counts = [
        {"state": "SUCCESS", "count": 3},
        {"state": "FAILURE", "count": 2},
    ]
    status_context_counts = [
        {"state": "SUCCESS", "count": 1},
        {"state": "FAILURE", "count": 1},
    ]

    result = parse_aggregated_check_counts(check_run_counts, status_context_counts, 7)
    assert result == (4, 7)  # 3 SUCCESS + 1 SUCCESS = 4 passing


def test_parse_aggregated_check_counts_empty():
    """Test with empty state arrays."""
    result = parse_aggregated_check_counts([], [], 0)
    assert result == (0, 0)


def test_parse_aggregated_check_counts_neutral_counts_as_passing():
    """Test that NEUTRAL state counts as passing."""
    check_run_counts = [{"state": "NEUTRAL", "count": 2}]
    result = parse_aggregated_check_counts(check_run_counts, [], 2)
    assert result == (2, 2)


def test_parse_aggregated_check_counts_skipped_counts_as_passing():
    """Test that SKIPPED state counts as passing."""
    check_run_counts = [{"state": "SKIPPED", "count": 3}]
    result = parse_aggregated_check_counts(check_run_counts, [], 3)
    assert result == (3, 3)


def test_parse_aggregated_check_counts_status_context_failure_not_passing():
    """Test that FAILURE StatusContext does not count as passing."""
    status_context_counts = [
        {"state": "SUCCESS", "count": 2},
        {"state": "FAILURE", "count": 1},
        {"state": "PENDING", "count": 1},
    ]
    result = parse_aggregated_check_counts([], status_context_counts, 4)
    # Only SUCCESS counts as passing for StatusContext
    assert result == (2, 4)


def test_parse_aggregated_check_counts_check_run_in_progress_not_passing():
    """Test that IN_PROGRESS CheckRun does not count as passing."""
    check_run_counts = [
        {"state": "SUCCESS", "count": 2},
        {"state": "IN_PROGRESS", "count": 1},
    ]
    result = parse_aggregated_check_counts(check_run_counts, [], 3)
    # Only SUCCESS, SKIPPED, NEUTRAL count as passing for CheckRun
    assert result == (2, 3)


def test_parse_aggregated_check_counts_missing_state_field():
    """Test handling of items with missing state field."""
    check_run_counts = [
        {"state": "SUCCESS", "count": 2},
        {"count": 1},  # Missing state
    ]
    result = parse_aggregated_check_counts(check_run_counts, [], 3)
    # Missing state should not count as passing (empty string not in passing set)
    assert result == (2, 3)


def test_parse_aggregated_check_counts_missing_count_field():
    """Test handling of items with missing count field."""
    check_run_counts = [
        {"state": "SUCCESS", "count": 2},
        {"state": "SUCCESS"},  # Missing count, defaults to 0
    ]
    result = parse_aggregated_check_counts(check_run_counts, [], 2)
    assert result == (2, 2)


def test_parse_github_pr_status_single():
    """Test parsing single PR status."""
    json_data = load_fixture("github/pr_status_single.json")
    state, number, title = parse_github_pr_status(json_data)

    assert state == "OPEN"
    assert number == 456
    assert title == "Add new feature for improved performance"


def test_parse_github_pr_status_no_pr():
    """Test parsing status when no PR exists."""
    state, number, title = parse_github_pr_status("[]")

    assert state == "NONE"
    assert number is None
    assert title is None


# Tests for parse_gh_auth_status_output


def test_parse_gh_auth_status_output_new_format():
    """Test parsing new gh CLI format with 'account' keyword."""
    output = """github.com
  ✓ Logged in to github.com account schrockn (keyring)
  - Active account: true
  - Git operations protocol: https
  - Token: gho_************************************
  - Token scopes: 'gist', 'read:org', 'repo', 'workflow'
"""
    authenticated, username, hostname = parse_gh_auth_status_output(output)

    assert authenticated is True
    assert username == "schrockn"
    assert hostname == "github.com"


def test_parse_gh_auth_status_output_old_format():
    """Test parsing old gh CLI format with 'as' keyword."""
    output = """github.com
  ✓ Logged in to github.com as testuser
  - Git operations for github.com configured to use https protocol.
  - Token: ghp_************************************
"""
    authenticated, username, hostname = parse_gh_auth_status_output(output)

    assert authenticated is True
    assert username == "testuser"
    assert hostname == "github.com"


def test_parse_gh_auth_status_output_github_enterprise():
    """Test parsing with GitHub Enterprise hostname."""
    output = """enterprise.github.com
  ✓ Logged in to enterprise.github.com account admin (keyring)
  - Active account: true
"""
    authenticated, username, hostname = parse_gh_auth_status_output(output)

    assert authenticated is True
    assert username == "admin"
    assert hostname == "enterprise.github.com"


def test_parse_gh_auth_status_output_checkmark_only():
    """Test fallback when checkmark present but format unrecognized."""
    output = """github.com
  ✓ Some unrecognized format line here
"""
    authenticated, username, hostname = parse_gh_auth_status_output(output)

    assert authenticated is True
    assert username is None
    assert hostname is None


def test_parse_gh_auth_status_output_not_authenticated():
    """Test handling of unauthenticated state."""
    output = """You are not logged in to any GitHub hosts.
To log in, run: gh auth login
"""
    authenticated, username, hostname = parse_gh_auth_status_output(output)

    assert authenticated is False
    assert username is None
    assert hostname is None


def test_parse_gh_auth_status_output_empty_string():
    """Test handling of empty output."""
    authenticated, username, hostname = parse_gh_auth_status_output("")

    assert authenticated is False
    assert username is None
    assert hostname is None
