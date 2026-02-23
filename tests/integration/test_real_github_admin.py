"""Tests for RealGitHubAdmin with mocked subprocess execution.

These tests verify that RealGitHubAdmin correctly calls gh CLI commands and handles
responses. We use pytest monkeypatch to mock subprocess calls.
"""

import subprocess

from pytest import MonkeyPatch

from erk_shared.gateway.github_admin.real import RealGitHubAdmin
from tests.integration.test_helpers import mock_subprocess_run

# ============================================================================
# check_auth_status() Tests
# ============================================================================


def test_check_auth_status_authenticated(monkeypatch: MonkeyPatch) -> None:
    """Test check_auth_status when user is logged in."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        assert cmd == ["gh", "auth", "status"]
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="github.com\n  ✓ Logged in to github.com account testuser (keyring)\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        result = admin.check_auth_status()

        assert result.authenticated is True
        assert result.username == "testuser"
        assert result.error is None


def test_check_auth_status_authenticated_with_parens(monkeypatch: MonkeyPatch) -> None:
    """Test check_auth_status parses username correctly when followed by parens."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=(
                "github.com\n  ✓ Logged in to github.com account schrockn (github.com/schrockn)\n"
            ),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        result = admin.check_auth_status()

        assert result.authenticated is True
        assert result.username == "schrockn"
        assert result.error is None


def test_check_auth_status_not_authenticated(monkeypatch: MonkeyPatch) -> None:
    """Test check_auth_status when user is not logged in."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=1,
            stdout="",
            stderr="You are not logged into any GitHub hosts. Run gh auth login to authenticate.",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        result = admin.check_auth_status()

        assert result.authenticated is False
        assert result.username is None
        assert result.error is None


def test_check_auth_status_timeout(monkeypatch: MonkeyPatch) -> None:
    """Test check_auth_status handles timeout gracefully."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise subprocess.TimeoutExpired(cmd, 10)

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        result = admin.check_auth_status()

        assert result.authenticated is False
        assert result.username is None
        assert result.error == "Auth check timed out"


def test_check_auth_status_os_error(monkeypatch: MonkeyPatch) -> None:
    """Test check_auth_status handles OSError (e.g., gh not installed)."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise OSError("No such file or directory: 'gh'")

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        result = admin.check_auth_status()

        assert result.authenticated is False
        assert result.username is None
        assert result.error == "No such file or directory: 'gh'"


def test_check_auth_status_output_in_stderr(monkeypatch: MonkeyPatch) -> None:
    """Test check_auth_status reads from stderr when stdout is empty."""
    # Some versions of gh output to stderr

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="github.com\n  ✓ Logged in to github.com account anotheruser (keyring)\n",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        result = admin.check_auth_status()

        assert result.authenticated is True
        assert result.username == "anotheruser"
        assert result.error is None


# ============================================================================
# secret_exists() Tests
# ============================================================================


def test_secret_exists_returns_true_when_secret_found(monkeypatch: MonkeyPatch) -> None:
    """Test secret_exists returns True when secret is found."""
    from pathlib import Path

    from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Verify command structure
        assert cmd[:2] == ["gh", "api"]
        assert "/repos/test-owner/test-repo/actions/secrets/MY_SECRET" in cmd[-1]
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout='{"name": "MY_SECRET", "created_at": "2024-01-01T00:00:00Z"}',
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        location = GitHubRepoLocation(
            root=Path("/test/repo"),
            repo_id=GitHubRepoId(owner="test-owner", repo="test-repo"),
        )
        result = admin.secret_exists(location, "MY_SECRET")

        assert result is True


def test_secret_exists_returns_false_when_secret_not_found(monkeypatch: MonkeyPatch) -> None:
    """Test secret_exists returns False when secret returns 404."""
    from pathlib import Path

    from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=1,
            stdout="",
            stderr="gh: Not Found (HTTP 404)",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        location = GitHubRepoLocation(
            root=Path("/test/repo"),
            repo_id=GitHubRepoId(owner="test-owner", repo="test-repo"),
        )
        result = admin.secret_exists(location, "NONEXISTENT_SECRET")

        assert result is False


def test_secret_exists_returns_none_on_permission_error(monkeypatch: MonkeyPatch) -> None:
    """Test secret_exists returns None when user lacks permission."""
    from pathlib import Path

    from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=1,
            stdout="",
            stderr="gh: Forbidden (HTTP 403)",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        location = GitHubRepoLocation(
            root=Path("/test/repo"),
            repo_id=GitHubRepoId(owner="test-owner", repo="test-repo"),
        )
        result = admin.secret_exists(location, "MY_SECRET")

        assert result is None


def test_secret_exists_returns_none_on_timeout(monkeypatch: MonkeyPatch) -> None:
    """Test secret_exists returns None when gh command times out."""
    from pathlib import Path

    from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise subprocess.TimeoutExpired(cmd, 10)

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        location = GitHubRepoLocation(
            root=Path("/test/repo"),
            repo_id=GitHubRepoId(owner="test-owner", repo="test-repo"),
        )
        result = admin.secret_exists(location, "MY_SECRET")

        assert result is None


def test_secret_exists_returns_none_on_os_error(monkeypatch: MonkeyPatch) -> None:
    """Test secret_exists returns None when gh not found."""
    from pathlib import Path

    from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise OSError("No such file or directory: 'gh'")

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        location = GitHubRepoLocation(
            root=Path("/test/repo"),
            repo_id=GitHubRepoId(owner="test-owner", repo="test-repo"),
        )
        result = admin.secret_exists(location, "MY_SECRET")

        assert result is None


# ============================================================================
# set_secret() Tests
# ============================================================================


def test_set_secret_constructs_correct_command(monkeypatch: MonkeyPatch) -> None:
    """Test set_secret calls gh secret set with correct args and passes value via stdin."""
    from pathlib import Path

    from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        assert cmd == [
            "gh",
            "secret",
            "set",
            "ANTHROPIC_API_KEY",
            "--repo",
            "test-owner/test-repo",
        ]
        assert kwargs.get("input") == "sk-secret-123"
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        location = GitHubRepoLocation(
            root=Path("/test/repo"),
            repo_id=GitHubRepoId(owner="test-owner", repo="test-repo"),
        )
        admin.set_secret(location, "ANTHROPIC_API_KEY", "sk-secret-123")


def test_set_secret_raises_on_failure(monkeypatch: MonkeyPatch) -> None:
    """Test set_secret raises RuntimeError when gh command fails."""
    from pathlib import Path

    import pytest

    from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=cmd,
            stderr="gh: permission denied",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        location = GitHubRepoLocation(
            root=Path("/test/repo"),
            repo_id=GitHubRepoId(owner="test-owner", repo="test-repo"),
        )
        with pytest.raises(RuntimeError):
            admin.set_secret(location, "MY_SECRET", "my-value")


# ============================================================================
# delete_secret() Tests
# ============================================================================


def test_delete_secret_constructs_correct_command(monkeypatch: MonkeyPatch) -> None:
    """Test delete_secret calls gh secret delete with correct args."""
    from pathlib import Path

    from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        assert cmd == [
            "gh",
            "secret",
            "delete",
            "ANTHROPIC_API_KEY",
            "--repo",
            "test-owner/test-repo",
        ]
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        location = GitHubRepoLocation(
            root=Path("/test/repo"),
            repo_id=GitHubRepoId(owner="test-owner", repo="test-repo"),
        )
        admin.delete_secret(location, "ANTHROPIC_API_KEY")


def test_delete_secret_raises_on_failure(monkeypatch: MonkeyPatch) -> None:
    """Test delete_secret raises RuntimeError when gh command fails."""
    from pathlib import Path

    import pytest

    from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=cmd,
            stderr="gh: secret not found",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        location = GitHubRepoLocation(
            root=Path("/test/repo"),
            repo_id=GitHubRepoId(owner="test-owner", repo="test-repo"),
        )
        with pytest.raises(RuntimeError):
            admin.delete_secret(location, "NONEXISTENT_SECRET")


# ============================================================================
# get_variable() Tests
# ============================================================================


def test_get_variable_returns_value_when_found(monkeypatch: MonkeyPatch) -> None:
    """Test get_variable returns the variable value when it exists."""
    from pathlib import Path

    from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        assert cmd == [
            "gh",
            "variable",
            "get",
            "CLAUDE_ENABLED",
            "--repo",
            "test-owner/test-repo",
        ]
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="true\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        location = GitHubRepoLocation(
            root=Path("/test/repo"),
            repo_id=GitHubRepoId(owner="test-owner", repo="test-repo"),
        )
        result = admin.get_variable(location, "CLAUDE_ENABLED")

        assert result == "true"


def test_get_variable_returns_none_when_not_found(monkeypatch: MonkeyPatch) -> None:
    """Test get_variable returns None when the variable doesn't exist."""
    from pathlib import Path

    from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=1,
            stdout="",
            stderr="variable CLAUDE_ENABLED was not found",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        location = GitHubRepoLocation(
            root=Path("/test/repo"),
            repo_id=GitHubRepoId(owner="test-owner", repo="test-repo"),
        )
        result = admin.get_variable(location, "CLAUDE_ENABLED")

        assert result is None


def test_get_variable_returns_none_on_timeout(monkeypatch: MonkeyPatch) -> None:
    """Test get_variable returns None when gh command times out."""
    from pathlib import Path

    from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise subprocess.TimeoutExpired(cmd, 10)

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        location = GitHubRepoLocation(
            root=Path("/test/repo"),
            repo_id=GitHubRepoId(owner="test-owner", repo="test-repo"),
        )
        result = admin.get_variable(location, "CLAUDE_ENABLED")

        assert result is None


def test_get_variable_returns_none_on_os_error(monkeypatch: MonkeyPatch) -> None:
    """Test get_variable returns None when gh not found."""
    from pathlib import Path

    from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise OSError("No such file or directory: 'gh'")

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        location = GitHubRepoLocation(
            root=Path("/test/repo"),
            repo_id=GitHubRepoId(owner="test-owner", repo="test-repo"),
        )
        result = admin.get_variable(location, "CLAUDE_ENABLED")

        assert result is None


# ============================================================================
# set_variable() Tests
# ============================================================================


def test_set_variable_constructs_correct_command(monkeypatch: MonkeyPatch) -> None:
    """Test set_variable calls gh variable set with correct args."""
    from pathlib import Path

    from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        assert cmd == [
            "gh",
            "variable",
            "set",
            "CLAUDE_ENABLED",
            "--body",
            "true",
            "--repo",
            "test-owner/test-repo",
        ]
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        location = GitHubRepoLocation(
            root=Path("/test/repo"),
            repo_id=GitHubRepoId(owner="test-owner", repo="test-repo"),
        )
        admin.set_variable(location, "CLAUDE_ENABLED", "true")


def test_set_variable_raises_on_failure(monkeypatch: MonkeyPatch) -> None:
    """Test set_variable raises RuntimeError when gh command fails."""
    from pathlib import Path

    import pytest

    from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=cmd,
            stderr="gh: permission denied",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        admin = RealGitHubAdmin()
        location = GitHubRepoLocation(
            root=Path("/test/repo"),
            repo_id=GitHubRepoId(owner="test-owner", repo="test-repo"),
        )
        with pytest.raises(RuntimeError):
            admin.set_variable(location, "CLAUDE_ENABLED", "true")
