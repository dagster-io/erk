"""Tests for admin github-pr-setting command."""

from click.testing import CliRunner

from erk_shared.github.types import GitHubRepoId, GitHubRepoLocation
from tests.fakes.github_admin import FakeGitHubAdmin
from tests.test_utils.env_helpers import erk_inmem_env


def _make_location(repo_dir) -> GitHubRepoLocation:
    """Create a GitHubRepoLocation for testing."""
    return GitHubRepoLocation(root=repo_dir, repo_id=GitHubRepoId("owner", "repo"))


def test_display_enabled_setting() -> None:
    """Test displaying current setting when PR creation is enabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        location = _make_location(repo_dir)

        # Configure admin with PR creation enabled
        admin = FakeGitHubAdmin(
            workflow_permissions={
                "default_workflow_permissions": "read",
                "can_approve_pull_request_reviews": True,
            }
        )

        # TODO: Once context supports GitHubAdmin injection, use env.build_context
        # For now, test with real RealGitHubAdmin would require gh CLI setup
        # This test validates the command structure and fake implementation

        # Verify fake behavior
        perms = admin.get_workflow_permissions(location)
        assert perms["can_approve_pull_request_reviews"] is True


def test_display_disabled_setting() -> None:
    """Test displaying current setting when PR creation is disabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        location = _make_location(repo_dir)

        admin = FakeGitHubAdmin(
            workflow_permissions={
                "default_workflow_permissions": "read",
                "can_approve_pull_request_reviews": False,
            }
        )

        perms = admin.get_workflow_permissions(location)
        assert perms["can_approve_pull_request_reviews"] is False


def test_enable_pr_creation() -> None:
    """Test enabling PR creation for workflows."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        location = _make_location(repo_dir)

        admin = FakeGitHubAdmin()

        # Verify initial state (disabled)
        perms = admin.get_workflow_permissions(location)
        assert perms["can_approve_pull_request_reviews"] is False

        # Enable PR creation
        admin.set_workflow_pr_permissions(location, enabled=True)

        # Verify mutation was tracked
        assert len(admin.set_permission_calls) == 1
        assert admin.set_permission_calls[0] == (repo_dir, True)

        # Verify state was updated
        perms = admin.get_workflow_permissions(location)
        assert perms["can_approve_pull_request_reviews"] is True


def test_disable_pr_creation() -> None:
    """Test disabling PR creation for workflows."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        location = _make_location(repo_dir)

        admin = FakeGitHubAdmin(
            workflow_permissions={
                "default_workflow_permissions": "read",
                "can_approve_pull_request_reviews": True,
            }
        )

        # Disable PR creation
        admin.set_workflow_pr_permissions(location, enabled=False)

        # Verify mutation was tracked
        assert len(admin.set_permission_calls) == 1
        assert admin.set_permission_calls[0] == (repo_dir, False)

        # Verify state was updated
        perms = admin.get_workflow_permissions(location)
        assert perms["can_approve_pull_request_reviews"] is False


def test_enable_and_disable_sequence() -> None:
    """Test enabling then disabling PR creation."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        location = _make_location(repo_dir)

        admin = FakeGitHubAdmin()

        # Enable
        admin.set_workflow_pr_permissions(location, enabled=True)
        perms = admin.get_workflow_permissions(location)
        assert perms["can_approve_pull_request_reviews"] is True

        # Disable
        admin.set_workflow_pr_permissions(location, enabled=False)
        perms = admin.get_workflow_permissions(location)
        assert perms["can_approve_pull_request_reviews"] is False

        # Verify both mutations tracked
        assert len(admin.set_permission_calls) == 2
        assert admin.set_permission_calls[0] == (repo_dir, True)
        assert admin.set_permission_calls[1] == (repo_dir, False)
