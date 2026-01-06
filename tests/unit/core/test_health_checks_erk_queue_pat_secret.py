"""Tests for check_erk_queue_pat_secret health check.

These tests verify the health check correctly reports whether the ERK_QUEUE_GH_PAT
secret is configured in the repository. Uses FakeGitHubAdmin to test secret checking
behavior.
"""

from click.testing import CliRunner
from tests.test_utils.env_helpers import erk_isolated_fs_env

from erk.core.health_checks import check_erk_queue_pat_secret
from erk_shared.github_admin.fake import FakeGitHubAdmin


def test_check_returns_passed_when_secret_exists() -> None:
    """Test that check returns success when ERK_QUEUE_GH_PAT secret exists."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        admin = FakeGitHubAdmin(secrets={"ERK_QUEUE_GH_PAT"})
        ctx = env.build_context()  # Default env has GitHub remote

        result = check_erk_queue_pat_secret(ctx, env.cwd, admin)

        assert result.passed is True
        assert result.name == "erk-queue-pat-secret"
        assert "ERK_QUEUE_GH_PAT" in result.message
        assert "configured" in result.message.lower()
        assert result.info is False  # Not info level when secret exists


def test_check_returns_info_when_secret_missing() -> None:
    """Test that check returns info-level when secret is not configured."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        admin = FakeGitHubAdmin(secrets=set())  # No secrets
        ctx = env.build_context()

        result = check_erk_queue_pat_secret(ctx, env.cwd, admin)

        assert result.passed is True  # Info level - always passes
        assert "ERK_QUEUE_GH_PAT" in result.message
        assert "not configured" in result.message.lower()
        assert result.info is True
        assert result.details is not None
        assert "remote implementation" in result.details.lower()


def test_check_returns_info_when_api_error() -> None:
    """Test that check returns info-level when secret check fails (e.g., no permission)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        admin = FakeGitHubAdmin(secret_check_error=True)  # Simulate API error
        ctx = env.build_context()

        result = check_erk_queue_pat_secret(ctx, env.cwd, admin)

        assert result.passed is True  # Info level - always passes
        assert "could not check" in result.message.lower()
        assert result.info is True


def test_check_returns_info_when_no_origin_remote() -> None:
    """Test that check returns info-level when no origin remote configured."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        from erk_shared.git.fake import FakeGit

        # FakeGit with no remote URLs configured - will raise ValueError
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            # No remote_urls - get_remote_url will raise ValueError
        )

        admin = FakeGitHubAdmin(secrets={"ERK_QUEUE_GH_PAT"})
        ctx = env.build_context(git=git)

        result = check_erk_queue_pat_secret(ctx, env.cwd, admin)

        assert result.passed is True  # Info level - always passes
        assert "no origin remote" in result.message.lower()
        assert result.info is True


def test_check_returns_info_when_not_github_repo() -> None:
    """Test that check returns info-level for non-GitHub repositories."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        from erk_shared.git.fake import FakeGit

        # Non-GitHub remote URL
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://gitlab.com/owner/repo.git"},
        )

        admin = FakeGitHubAdmin(secrets={"ERK_QUEUE_GH_PAT"})
        ctx = env.build_context(git=git)

        result = check_erk_queue_pat_secret(ctx, env.cwd, admin)

        assert result.passed is True  # Info level - always passes
        assert "not a github repository" in result.message.lower()
        assert result.info is True


def test_check_handles_https_github_url() -> None:
    """Test that check works with HTTPS GitHub URLs."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        from erk_shared.git.fake import FakeGit

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://github.com/test-owner/test-repo.git"},
        )

        admin = FakeGitHubAdmin(secrets={"ERK_QUEUE_GH_PAT"})
        ctx = env.build_context(git=git)

        result = check_erk_queue_pat_secret(ctx, env.cwd, admin)

        assert result.passed is True
        assert "ERK_QUEUE_GH_PAT" in result.message
        assert "configured" in result.message.lower()
