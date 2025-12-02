"""Unit tests for GitHubAdmin implementations."""

from pathlib import Path

from erk_shared.github.types import GitHubRepoId, GitHubRepoLocation

from tests.fakes.github_admin import FakeGitHubAdmin

REPO_ROOT = Path("/test/repo")
LOCATION = GitHubRepoLocation(root=REPO_ROOT, repo_id=GitHubRepoId("test-owner", "test-repo"))


def test_get_workflow_permissions_fake() -> None:
    """Test getting workflow permissions returns configured state."""
    admin = FakeGitHubAdmin(
        workflow_permissions={
            "default_workflow_permissions": "read",
            "can_approve_pull_request_reviews": True,
        }
    )

    result = admin.get_workflow_permissions(LOCATION)

    assert result["default_workflow_permissions"] == "read"
    assert result["can_approve_pull_request_reviews"] is True


def test_set_workflow_pr_permissions_enable() -> None:
    """Test enabling PR permissions tracks mutation."""
    admin = FakeGitHubAdmin()

    # Verify initial state (disabled)
    perms = admin.get_workflow_permissions(LOCATION)
    assert perms["can_approve_pull_request_reviews"] is False

    # Enable permissions
    admin.set_workflow_pr_permissions(LOCATION, enabled=True)

    # Verify mutation was tracked
    assert len(admin.set_permission_calls) == 1
    assert admin.set_permission_calls[0] == (REPO_ROOT, True)

    # Verify internal state was updated
    perms = admin.get_workflow_permissions(LOCATION)
    assert perms["can_approve_pull_request_reviews"] is True


def test_set_workflow_pr_permissions_disable() -> None:
    """Test disabling PR permissions tracks mutation."""
    admin = FakeGitHubAdmin(
        workflow_permissions={
            "default_workflow_permissions": "read",
            "can_approve_pull_request_reviews": True,
        }
    )

    # Disable permissions
    admin.set_workflow_pr_permissions(LOCATION, enabled=False)

    # Verify mutation was tracked
    assert len(admin.set_permission_calls) == 1
    assert admin.set_permission_calls[0] == (REPO_ROOT, False)

    # Verify internal state was updated
    perms = admin.get_workflow_permissions(LOCATION)
    assert perms["can_approve_pull_request_reviews"] is False


def test_multiple_permission_changes() -> None:
    """Test multiple permission changes are all tracked."""
    admin = FakeGitHubAdmin()

    # Make multiple changes
    admin.set_workflow_pr_permissions(LOCATION, enabled=True)
    admin.set_workflow_pr_permissions(LOCATION, enabled=False)
    admin.set_workflow_pr_permissions(LOCATION, enabled=True)

    # Verify all mutations were tracked
    assert len(admin.set_permission_calls) == 3
    assert admin.set_permission_calls[0] == (REPO_ROOT, True)
    assert admin.set_permission_calls[1] == (REPO_ROOT, False)
    assert admin.set_permission_calls[2] == (REPO_ROOT, True)

    # Final state should match last change
    perms = admin.get_workflow_permissions(LOCATION)
    assert perms["can_approve_pull_request_reviews"] is True
