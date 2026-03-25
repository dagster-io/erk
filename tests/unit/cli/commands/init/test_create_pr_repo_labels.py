"""Tests for create_pr_repo_labels().

These tests verify the label creation logic for the PR repository.
Uses FakeGitHubIssues to test label creation behavior.
"""

from erk.cli.commands.init.main import create_pr_repo_labels
from tests.fakes.gateway.github_issues import FakeGitHubIssues
from tests.test_utils.paths import sentinel_path


def test_create_pr_repo_labels_creates_all_labels() -> None:
    """Test that all five erk labels are created."""
    github_issues = FakeGitHubIssues()

    result = create_pr_repo_labels(
        repo_root=sentinel_path(),
        pr_repo="owner/plans-repo",
        github_issues=github_issues,
    )

    assert result is None  # Success
    assert "erk-pr" in github_issues.labels
    assert "erk-learn" in github_issues.labels
    assert "erk-objective" in github_issues.labels
    assert "no-changes" in github_issues.labels


def test_create_pr_repo_labels_tracks_created_labels() -> None:
    """Test that label creation is tracked with correct details."""
    github_issues = FakeGitHubIssues()

    create_pr_repo_labels(
        repo_root=sentinel_path(),
        pr_repo="owner/plans-repo",
        github_issues=github_issues,
    )

    # Verify all labels were created with correct details
    created = github_issues.created_labels
    assert len(created) == 4

    label_names = [label[0] for label in created]
    assert "erk-pr" in label_names
    assert "erk-learn" in label_names
    assert "erk-objective" in label_names
    assert "no-changes" in label_names


def test_create_pr_repo_labels_idempotent_with_existing() -> None:
    """Test that existing labels are not recreated."""
    github_issues = FakeGitHubIssues(labels={"erk-pr", "erk-objective"})

    create_pr_repo_labels(
        repo_root=sentinel_path(),
        pr_repo="owner/plans-repo",
        github_issues=github_issues,
    )

    # Two labels should be created (erk-learn and no-changes were missing)
    assert len(github_issues.created_labels) == 2
    created_names = [label[0] for label in github_issues.created_labels]
    assert "erk-learn" in created_names
    assert "no-changes" in created_names


def test_create_pr_repo_labels_all_exist_no_creation() -> None:
    """Test that no labels are created when all already exist."""
    github_issues = FakeGitHubIssues(
        labels={"erk-pr", "erk-learn", "erk-objective", "no-changes"},
    )

    create_pr_repo_labels(
        repo_root=sentinel_path(),
        pr_repo="owner/plans-repo",
        github_issues=github_issues,
    )

    # No labels should be created
    assert github_issues.created_labels == []
