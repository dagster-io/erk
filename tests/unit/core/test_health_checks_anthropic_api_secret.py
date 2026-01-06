"""Tests for check_anthropic_api_secret health check.

These tests verify the health check correctly reports whether Anthropic API
authentication secrets (ANTHROPIC_API_KEY, CLAUDE_CODE_OAUTH_TOKEN) are
configured in the repository. Uses FakeGitHubAdmin to test secret checking
behavior.
"""

from click.testing import CliRunner
from tests.test_utils.env_helpers import erk_isolated_fs_env

from erk.core.health_checks import check_anthropic_api_secret
from erk_shared.github_admin.fake import FakeGitHubAdmin


def test_check_returns_passed_when_api_key_exists() -> None:
    """Test that check returns success when ANTHROPIC_API_KEY secret exists."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        admin = FakeGitHubAdmin(secrets={"ANTHROPIC_API_KEY"})
        ctx = env.build_context()  # Default env has GitHub remote

        result = check_anthropic_api_secret(ctx, env.cwd, admin)

        assert result.passed is True
        assert result.name == "anthropic-api-secret"
        assert "ANTHROPIC_API_KEY" in result.message
        assert "configured" in result.message.lower()
        assert result.info is False  # Not info level when secret exists


def test_check_returns_passed_when_oauth_token_exists() -> None:
    """Test that check returns success when CLAUDE_CODE_OAUTH_TOKEN secret exists."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        admin = FakeGitHubAdmin(secrets={"CLAUDE_CODE_OAUTH_TOKEN"})
        ctx = env.build_context()

        result = check_anthropic_api_secret(ctx, env.cwd, admin)

        assert result.passed is True
        assert "CLAUDE_CODE_OAUTH_TOKEN" in result.message
        assert "configured" in result.message.lower()
        assert result.info is False


def test_check_returns_passed_with_precedence_note_when_both_exist() -> None:
    """Test that check notes precedence when both secrets exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        admin = FakeGitHubAdmin(secrets={"ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"})
        ctx = env.build_context()

        result = check_anthropic_api_secret(ctx, env.cwd, admin)

        assert result.passed is True
        assert "ANTHROPIC_API_KEY" in result.message
        assert "CLAUDE_CODE_OAUTH_TOKEN" in result.message
        assert result.details is not None
        assert "precedence" in result.details.lower()
        assert result.info is False


def test_check_returns_info_when_neither_secret_exists() -> None:
    """Test that check returns info-level when no secrets are configured."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        admin = FakeGitHubAdmin(secrets=set())  # No secrets
        ctx = env.build_context()

        result = check_anthropic_api_secret(ctx, env.cwd, admin)

        assert result.passed is True  # Info level - always passes
        assert "no anthropic authentication" in result.message.lower()
        assert result.info is True
        assert result.details is not None
        assert "github actions" in result.details.lower()
        # Should have remediation with setup instructions
        assert result.remediation is not None
        assert "ANTHROPIC_API_KEY" in result.remediation
        assert "CLAUDE_CODE_OAUTH_TOKEN" in result.remediation


def test_check_returns_info_when_api_error() -> None:
    """Test that check returns info-level when secret check fails (e.g., no permission)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        admin = FakeGitHubAdmin(secret_check_error=True)  # Simulate API error
        ctx = env.build_context()

        result = check_anthropic_api_secret(ctx, env.cwd, admin)

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

        admin = FakeGitHubAdmin(secrets={"ANTHROPIC_API_KEY"})
        ctx = env.build_context(git=git)

        result = check_anthropic_api_secret(ctx, env.cwd, admin)

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

        admin = FakeGitHubAdmin(secrets={"ANTHROPIC_API_KEY"})
        ctx = env.build_context(git=git)

        result = check_anthropic_api_secret(ctx, env.cwd, admin)

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

        admin = FakeGitHubAdmin(secrets={"ANTHROPIC_API_KEY"})
        ctx = env.build_context(git=git)

        result = check_anthropic_api_secret(ctx, env.cwd, admin)

        assert result.passed is True
        assert "ANTHROPIC_API_KEY" in result.message
        assert "configured" in result.message.lower()
