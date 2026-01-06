"""Tests for check_plans_repo_labels health check.

These tests verify the health check correctly reports label status in the plans repository.
Uses FakeGitHubIssues to test label checking behavior.

Note: The doctor check only verifies erk-plan and erk-objective labels.
erk-extraction is optional (for documentation workflows) and not checked.
"""

from tests.test_utils.paths import sentinel_path

from erk.core.health_checks import check_plans_repo_labels
from erk_shared.github.issues import FakeGitHubIssues


def test_check_returns_passed_when_all_required_labels_exist() -> None:
    """Test that check returns success when required erk labels exist."""
    github_issues = FakeGitHubIssues(labels={"erk-plan", "erk-objective"})

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
    """Test that check fails when one required label is missing."""
    github_issues = FakeGitHubIssues(labels={"erk-plan"})  # Missing erk-objective

    result = check_plans_repo_labels(
        repo_root=sentinel_path(),
        plans_repo="owner/plans-repo",
        github_issues=github_issues,
    )

    assert result.passed is False
    assert "erk-objective" in result.message
    assert result.remediation is not None
    assert "gh label create" in result.remediation


def test_check_returns_failed_when_all_labels_missing() -> None:
    """Test that check fails when all required labels are missing."""
    github_issues = FakeGitHubIssues()  # No labels

    result = check_plans_repo_labels(
        repo_root=sentinel_path(),
        plans_repo="owner/plans-repo",
        github_issues=github_issues,
    )

    assert result.passed is False
    assert "erk-plan" in result.message
    assert "erk-objective" in result.message
    # erk-extraction is NOT checked (optional for documentation workflows)
    assert "erk-extraction" not in result.message


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
    """Test that check passes when repo has extra labels beyond required erk labels."""
    github_issues = FakeGitHubIssues(
        labels={"erk-plan", "erk-objective", "erk-extraction", "bug", "enhancement"}
    )

    result = check_plans_repo_labels(
        repo_root=sentinel_path(),
        plans_repo="owner/plans-repo",
        github_issues=github_issues,
    )

    assert result.passed is True


def test_check_passes_without_erk_extraction() -> None:
    """Test that check passes when erk-extraction is missing (it's optional)."""
    github_issues = FakeGitHubIssues(labels={"erk-plan", "erk-objective"})

    result = check_plans_repo_labels(
        repo_root=sentinel_path(),
        plans_repo="owner/plans-repo",
        github_issues=github_issues,
    )

    assert result.passed is True


def test_remediation_contains_gh_label_create_commands() -> None:
    """Test that remediation contains copy-paste gh label create commands."""
    github_issues = FakeGitHubIssues(labels={"erk-plan"})  # Missing erk-objective

    result = check_plans_repo_labels(
        repo_root=sentinel_path(),
        plans_repo="owner/plans-repo",
        github_issues=github_issues,
    )

    assert result.remediation is not None
    assert 'gh label create "erk-objective"' in result.remediation
    assert "--description" in result.remediation
    assert "--color" in result.remediation
    assert "-R owner/plans-repo" in result.remediation


def test_remediation_contains_multiple_commands_when_multiple_missing() -> None:
    """Test that remediation contains commands for all missing labels."""
    github_issues = FakeGitHubIssues()  # No labels

    result = check_plans_repo_labels(
        repo_root=sentinel_path(),
        plans_repo="owner/plans-repo",
        github_issues=github_issues,
    )

    assert result.remediation is not None
    assert 'gh label create "erk-plan"' in result.remediation
    assert 'gh label create "erk-objective"' in result.remediation
