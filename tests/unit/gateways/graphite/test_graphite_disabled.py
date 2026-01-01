"""Tests for GraphiteDisabled sentinel implementation.

These tests verify that the GraphiteDisabled sentinel properly implements
the graceful degradation pattern: read-only methods return empty results,
mutating methods raise GraphiteDisabledError with helpful messages.
"""

from pathlib import Path

import pytest

from erk_shared.gateway.graphite.disabled import (
    GraphiteDisabled,
    GraphiteDisabledError,
    GraphiteDisabledReason,
)
from erk_shared.git.fake import FakeGit
from erk_shared.github.types import GitHubRepoId


def test_graphite_disabled_is_frozen() -> None:
    """GraphiteDisabled sentinel is immutable (frozen dataclass)."""
    sentinel = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)

    with pytest.raises(AttributeError):
        sentinel.reason = GraphiteDisabledReason.NOT_INSTALLED  # type: ignore[misc]


def test_graphite_url_always_works() -> None:
    """get_graphite_url works regardless of disabled reason."""
    sentinel = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)
    repo_id = GitHubRepoId(owner="dagster-io", repo="erk")

    url = sentinel.get_graphite_url(repo_id, 123)

    assert url == "https://app.graphite.dev/github/pr/dagster-io/erk/123"


def test_graphite_url_works_when_not_installed() -> None:
    """get_graphite_url works even when gt is not installed."""
    sentinel = GraphiteDisabled(reason=GraphiteDisabledReason.NOT_INSTALLED)
    repo_id = GitHubRepoId(owner="acme", repo="project")

    url = sentinel.get_graphite_url(repo_id, 456)

    assert url == "https://app.graphite.dev/github/pr/acme/project/456"


# Read-only methods return empty results


def test_get_prs_from_graphite_returns_empty(tmp_path: Path) -> None:
    """get_prs_from_graphite returns empty dict when disabled."""
    sentinel = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)
    git = FakeGit()

    result = sentinel.get_prs_from_graphite(git, tmp_path)

    assert result == {}


def test_get_all_branches_returns_empty(tmp_path: Path) -> None:
    """get_all_branches returns empty dict when disabled."""
    sentinel = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)
    git = FakeGit()

    result = sentinel.get_all_branches(git, tmp_path)

    assert result == {}


def test_get_branch_stack_returns_none(tmp_path: Path) -> None:
    """get_branch_stack returns None when disabled."""
    sentinel = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)
    git = FakeGit()

    result = sentinel.get_branch_stack(git, tmp_path, "feature")

    assert result is None


def test_check_auth_status_returns_not_authenticated() -> None:
    """check_auth_status returns not authenticated tuple when disabled."""
    sentinel = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)

    is_auth, username, repo_info = sentinel.check_auth_status()

    assert is_auth is False
    assert username is None
    assert repo_info is None


def test_is_branch_tracked_returns_false(tmp_path: Path) -> None:
    """is_branch_tracked returns False when disabled."""
    sentinel = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)

    result = sentinel.is_branch_tracked(tmp_path, "any-branch")

    assert result is False


# Inherited convenience methods work via empty base data


def test_get_parent_branch_returns_none(tmp_path: Path) -> None:
    """get_parent_branch (inherited) returns None since get_all_branches is empty."""
    sentinel = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)
    git = FakeGit()

    result = sentinel.get_parent_branch(git, tmp_path, "feature")

    assert result is None


def test_get_child_branches_returns_empty(tmp_path: Path) -> None:
    """get_child_branches (inherited) returns empty list since get_all_branches is empty."""
    sentinel = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)
    git = FakeGit()

    result = sentinel.get_child_branches(git, tmp_path, "feature")

    assert result == []


# Mutating methods raise GraphiteDisabledError


def test_sync_raises_error_when_config_disabled(tmp_path: Path) -> None:
    """sync raises GraphiteDisabledError when disabled via config."""
    sentinel = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)

    with pytest.raises(GraphiteDisabledError) as exc_info:
        sentinel.sync(tmp_path, force=False, quiet=False)

    assert exc_info.value.reason == GraphiteDisabledReason.CONFIG_DISABLED
    assert "requires Graphite to be enabled" in str(exc_info.value)
    assert "erk config set use_graphite true" in str(exc_info.value)


def test_sync_raises_error_when_not_installed(tmp_path: Path) -> None:
    """sync raises GraphiteDisabledError when gt not installed."""
    sentinel = GraphiteDisabled(reason=GraphiteDisabledReason.NOT_INSTALLED)

    with pytest.raises(GraphiteDisabledError) as exc_info:
        sentinel.sync(tmp_path, force=False, quiet=False)

    assert exc_info.value.reason == GraphiteDisabledReason.NOT_INSTALLED
    assert "requires Graphite to be installed" in str(exc_info.value)
    assert "npm install -g @withgraphite/graphite-cli" in str(exc_info.value)


def test_restack_raises_error(tmp_path: Path) -> None:
    """restack raises GraphiteDisabledError."""
    sentinel = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)

    with pytest.raises(GraphiteDisabledError):
        sentinel.restack(tmp_path, no_interactive=True, quiet=False)


def test_track_branch_raises_error(tmp_path: Path) -> None:
    """track_branch raises GraphiteDisabledError."""
    sentinel = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)

    with pytest.raises(GraphiteDisabledError):
        sentinel.track_branch(tmp_path, "feature", "main")


def test_submit_branch_raises_error(tmp_path: Path) -> None:
    """submit_branch raises GraphiteDisabledError."""
    sentinel = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)

    with pytest.raises(GraphiteDisabledError):
        sentinel.submit_branch(tmp_path, "feature", quiet=False)


def test_squash_branch_raises_error(tmp_path: Path) -> None:
    """squash_branch raises GraphiteDisabledError."""
    sentinel = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)

    with pytest.raises(GraphiteDisabledError):
        sentinel.squash_branch(tmp_path, quiet=False)


def test_submit_stack_raises_error(tmp_path: Path) -> None:
    """submit_stack raises GraphiteDisabledError."""
    sentinel = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)

    with pytest.raises(GraphiteDisabledError):
        sentinel.submit_stack(tmp_path, publish=False, restack=False)


def test_continue_restack_raises_error(tmp_path: Path) -> None:
    """continue_restack raises GraphiteDisabledError."""
    sentinel = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)

    with pytest.raises(GraphiteDisabledError):
        sentinel.continue_restack(tmp_path, quiet=False)


# Error message differences


def test_config_disabled_error_message() -> None:
    """CONFIG_DISABLED error includes config command."""
    error = GraphiteDisabledError(GraphiteDisabledReason.CONFIG_DISABLED)

    message = str(error)

    assert "requires Graphite to be enabled" in message
    assert "erk config set use_graphite true" in message


def test_not_installed_error_message() -> None:
    """NOT_INSTALLED error includes installation instructions."""
    error = GraphiteDisabledError(GraphiteDisabledReason.NOT_INSTALLED)

    message = str(error)

    assert "requires Graphite to be installed" in message
    assert "npm install -g @withgraphite/graphite-cli" in message
    assert "erk config set use_graphite true" in message
