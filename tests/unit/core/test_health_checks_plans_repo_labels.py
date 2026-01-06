"""Tests for check_plans_repo_labels health check.

These tests verify the health check correctly reports label status in the plans repository.
Uses FakeGitHubIssues to test label checking behavior.
"""

from tests.test_utils.paths import sentinel_path

from erk.core.health_checks import check_plans_repo_labels
from erk_shared.github.issues import FakeGitHubIssues


def test_check_returns_passed_when_all_labels_exist() -> None:
    """Test that check returns success when all erk labels exist."""
    github_issues = FakeGitHubIssues(labels={"erk-plan", "erk-extraction", "erk-objective"})

    result = check_plans_repo_labels(
        repo_root=sentinel_path(),
        plans_repo="owner/plans-repo",
        github_issues=github_issues,
    )

    assert result.passed is True
    assert result.name == "plans-repo-labels"
    assert "configured" in result.message.lower()
    assert "owner/plans-repo" in result.message


def test_check_returns_failed_when_one_label_missing() -> None:
    """Test that check fails when one label is missing."""
    github_issues = FakeGitHubIssues(labels={"erk-plan", "erk-objective"})  # Missing erk-extraction

    result = check_plans_repo_labels(
        repo_root=sentinel_path(),
        plans_repo="owner/plans-repo",
        github_issues=github_issues,
    )

    assert result.passed is False
    assert "erk-extraction" in result.message
    assert result.remediation is not None
    assert "erk init" in result.remediation.lower()


def test_check_returns_failed_when_all_labels_missing() -> None:
    """Test that check fails when all labels are missing."""
    github_issues = FakeGitHubIssues()  # No labels

    result = check_plans_repo_labels(
        repo_root=sentinel_path(),
        plans_repo="owner/plans-repo",
        github_issues=github_issues,
    )

    assert result.passed is False
    assert "erk-plan" in result.message
    assert "erk-extraction" in result.message
    assert "erk-objective" in result.message


def test_check_returns_failed_message_includes_plans_repo() -> None:
    """Test that failure message includes the plans repo name."""
    github_issues = FakeGitHubIssues()

    result = check_plans_repo_labels(
        repo_root=sentinel_path(),
        plans_repo="myorg/engineering-plans",
        github_issues=github_issues,
    )

    assert result.passed is False
    assert "myorg/engineering-plans" in result.message


def test_check_passes_with_extra_labels() -> None:
    """Test that check passes when repo has extra labels beyond erk labels."""
    github_issues = FakeGitHubIssues(
        labels={"erk-plan", "erk-extraction", "erk-objective", "bug", "enhancement"}
    )

    result = check_plans_repo_labels(
        repo_root=sentinel_path(),
        plans_repo="owner/plans-repo",
        github_issues=github_issues,
    )

    assert result.passed is True
