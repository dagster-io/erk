"""Tests for FakeCodespaceGitHub test infrastructure.

These tests verify that FakeCodespaceGitHub correctly simulates GitHub codespace
operations, providing reliable test doubles for codespace command tests.
"""

from datetime import datetime

import pytest

from erk.core.codespace.github_fake import FakeCodespaceGitHub
from erk.core.codespace.types import GitHubCodespaceInfo


def _make_gh_codespace(
    name: str = "schrockn-abc123",
    state: str = "Available",
    repository: str = "schrockn/erk",
    branch: str = "main",
) -> GitHubCodespaceInfo:
    """Helper to create test GitHub codespace info."""
    return GitHubCodespaceInfo(
        name=name,
        state=state,
        repository=repository,
        branch=branch,
        machine_type="standardLinux32gb",
        created_at=datetime(2025, 1, 1, 12, 0, 0),
    )


def test_fake_github_initializes_empty() -> None:
    """Test that FakeCodespaceGitHub initializes with empty state."""
    github = FakeCodespaceGitHub()

    assert github.list_codespaces() == []
    assert github.get_codespace("any-name") is None


def test_fake_github_initializes_with_codespaces() -> None:
    """Test initialization with pre-configured codespaces."""
    cs = _make_gh_codespace("test-space")
    github = FakeCodespaceGitHub(codespaces=[cs])

    codespaces = github.list_codespaces()
    assert len(codespaces) == 1
    assert codespaces[0].name == "test-space"


def test_fake_github_get_codespace_returns_match() -> None:
    """Test that get_codespace returns matching codespace."""
    cs = _make_gh_codespace("my-space")
    github = FakeCodespaceGitHub(codespaces=[cs])

    result = github.get_codespace("my-space")

    assert result is not None
    assert result.name == "my-space"


def test_fake_github_get_codespace_returns_none_for_missing() -> None:
    """Test that get_codespace returns None for non-existent codespace."""
    cs = _make_gh_codespace("my-space")
    github = FakeCodespaceGitHub(codespaces=[cs])

    result = github.get_codespace("nonexistent")

    assert result is None


def test_fake_github_create_codespace_returns_info() -> None:
    """Test that create_codespace creates and returns codespace info."""
    github = FakeCodespaceGitHub()

    result = github.create_codespace(repo="owner/repo", branch="feature")

    assert result.repository == "owner/repo"
    assert result.branch == "feature"
    assert result.state == "Available"


def test_fake_github_create_codespace_adds_to_list() -> None:
    """Test that created codespace appears in list."""
    github = FakeCodespaceGitHub()

    result = github.create_codespace(repo="owner/repo", branch="feature")

    codespaces = github.list_codespaces()
    assert len(codespaces) == 1
    assert codespaces[0].name == result.name


def test_fake_github_create_codespace_failure() -> None:
    """Test that create_codespace can be configured to fail."""
    github = FakeCodespaceGitHub(create_should_fail=True)

    with pytest.raises(RuntimeError, match="creation failure"):
        github.create_codespace(repo="owner/repo", branch="feature")


def test_fake_github_wait_for_available_returns_true_if_exists() -> None:
    """Test that wait_for_available returns True if codespace exists."""
    cs = _make_gh_codespace("my-space", state="Available")
    github = FakeCodespaceGitHub(codespaces=[cs])

    result = github.wait_for_available("my-space")

    assert result is True


def test_fake_github_wait_for_available_returns_false_if_missing() -> None:
    """Test that wait_for_available returns False if codespace doesn't exist."""
    github = FakeCodespaceGitHub()

    result = github.wait_for_available("nonexistent")

    assert result is False


def test_fake_github_ssh_interactive_returns_configured_code() -> None:
    """Test that ssh_interactive returns configured exit code."""
    github = FakeCodespaceGitHub(ssh_exit_code=0)

    result = github.ssh_interactive("any-space")

    assert result == 0


def test_fake_github_ssh_interactive_returns_nonzero() -> None:
    """Test that ssh_interactive can return non-zero exit code."""
    github = FakeCodespaceGitHub(ssh_exit_code=1)

    result = github.ssh_interactive("any-space")

    assert result == 1


def test_fake_github_ssh_interactive_tracks_calls() -> None:
    """Test that ssh_interactive tracks connection attempts."""
    github = FakeCodespaceGitHub()

    github.ssh_interactive("space-1")
    github.ssh_interactive("space-2")

    assert github.ssh_connections == ["space-1", "space-2"]


def test_fake_github_ssh_replace_tracks_calls() -> None:
    """Test that ssh_replace tracks connection attempts (doesn't actually exec)."""
    github = FakeCodespaceGitHub()

    github.ssh_replace("my-space")

    assert github.ssh_connections == ["my-space"]


def test_fake_github_ssh_connections_returns_copy() -> None:
    """Test that ssh_connections returns a copy, not internal state."""
    github = FakeCodespaceGitHub()
    github.ssh_interactive("my-space")

    connections = github.ssh_connections
    connections.append("fake")

    assert "fake" not in github.ssh_connections
    assert len(github.ssh_connections) == 1


def test_fake_github_created_codespaces_tracks_creates() -> None:
    """Test that created_codespaces tracks all create calls."""
    github = FakeCodespaceGitHub()

    github.create_codespace(repo="owner/repo1", branch="main")
    github.create_codespace(repo="owner/repo2", branch="feature")

    created = github.created_codespaces
    assert len(created) == 2
    assert created[0].repository == "owner/repo1"
    assert created[1].repository == "owner/repo2"


def test_fake_github_created_codespaces_returns_copy() -> None:
    """Test that created_codespaces returns a copy."""
    github = FakeCodespaceGitHub()
    github.create_codespace(repo="owner/repo", branch="main")

    created = github.created_codespaces
    created.append(_make_gh_codespace("fake"))

    assert len(github.created_codespaces) == 1


def test_fake_github_add_codespace_helper() -> None:
    """Test that add_codespace helper adds to simulated state."""
    github = FakeCodespaceGitHub()
    cs = _make_gh_codespace("added-space")

    github.add_codespace(cs)

    assert github.get_codespace("added-space") is not None


def test_fake_github_remove_codespace_helper() -> None:
    """Test that remove_codespace helper removes from simulated state."""
    cs = _make_gh_codespace("my-space")
    github = FakeCodespaceGitHub(codespaces=[cs])

    github.remove_codespace("my-space")

    assert github.get_codespace("my-space") is None


def test_fake_github_set_codespace_state_helper() -> None:
    """Test that set_codespace_state helper updates state."""
    cs = _make_gh_codespace("my-space", state="Available")
    github = FakeCodespaceGitHub(codespaces=[cs])

    github.set_codespace_state("my-space", "Shutdown")

    result = github.get_codespace("my-space")
    assert result is not None
    assert result.state == "Shutdown"


def test_fake_github_machine_type_passed_to_create() -> None:
    """Test that machine_type is passed through create_codespace."""
    github = FakeCodespaceGitHub()

    result = github.create_codespace(
        repo="owner/repo",
        branch="main",
        machine_type="largePremiumLinux",
    )

    assert result.machine_type == "largePremiumLinux"
