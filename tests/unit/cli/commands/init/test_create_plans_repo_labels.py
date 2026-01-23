"""Tests for create_plans_repo_labels().

These tests verify the label creation logic for the plans repository.
Uses FakeGitHubIssues to test label creation behavior.
"""

from erk.cli.commands.init.main import create_plans_repo_labels
from erk_shared.github.issues.fake import FakeGitHubIssues
from tests.test_utils.paths import sentinel_path


def test_create_plans_repo_labels_creates_all_labels() -> None:
    """Test that all four erk labels are created."""
    github_issues = FakeGitHubIssues()

    result = create_plans_repo_labels(
        repo_root=sentinel_path(),
        plans_repo="owner/plans-repo",
        github_issues=github_issues,
    )

    assert result is None  # Success
    assert "erk-plan" in github_issues.labels
    assert "erk-learn" in github_issues.labels
    assert "erk-objective" in github_issues.labels
    assert "no-changes" in github_issues.labels


def test_create_plans_repo_labels_tracks_created_labels() -> None:
    """Test that label creation is tracked with correct details."""
    github_issues = FakeGitHubIssues()

    create_plans_repo_labels(
        repo_root=sentinel_path(),
        plans_repo="owner/plans-repo",
        github_issues=github_issues,
    )

    # Verify all labels were created with correct details
    created = github_issues.created_labels
    assert len(created) == 4

    label_names = [label[0] for label in created]
    assert "erk-plan" in label_names
    assert "erk-learn" in label_names
    assert "erk-objective" in label_names
    assert "no-changes" in label_names


def test_create_plans_repo_labels_idempotent_with_existing() -> None:
    """Test that existing labels are not recreated."""
    github_issues = FakeGitHubIssues(labels={"erk-plan", "erk-objective"})

    create_plans_repo_labels(
        repo_root=sentinel_path(),
        plans_repo="owner/plans-repo",
        github_issues=github_issues,
    )

    # Two labels should be created (erk-learn and no-changes were missing)
    assert len(github_issues.created_labels) == 2
    created_names = [label[0] for label in github_issues.created_labels]
    assert "erk-learn" in created_names
    assert "no-changes" in created_names


def test_create_plans_repo_labels_all_exist_no_creation() -> None:
    """Test that no labels are created when all already exist."""
    github_issues = FakeGitHubIssues(
        labels={"erk-plan", "erk-learn", "erk-objective", "no-changes"}
    )

    create_plans_repo_labels(
        repo_root=sentinel_path(),
        plans_repo="owner/plans-repo",
        github_issues=github_issues,
    )

    # No labels should be created
    assert github_issues.created_labels == []
