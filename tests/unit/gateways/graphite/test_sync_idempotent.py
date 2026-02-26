"""Tests for Graphite.sync_idempotent template method."""

from pathlib import Path

from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.gt.types import SyncError, SyncSuccess


def test_sync_idempotent_returns_success_on_happy_path(tmp_path: Path) -> None:
    """sync_idempotent returns SyncSuccess when sync() succeeds."""
    graphite = FakeGraphite()

    result = graphite.sync_idempotent(tmp_path, force=True, quiet=False)

    assert isinstance(result, SyncSuccess)
    assert result.success is True
    assert result.message == "Synced with remote."


def test_sync_idempotent_classifies_unstaged_changes_as_other_branch_conflict(
    tmp_path: Path,
) -> None:
    """sync_idempotent classifies 'unstaged changes' error as other-branch-conflict."""
    graphite = FakeGraphite(
        sync_raises=RuntimeError("cannot sync: unstaged changes in /other/worktree"),
    )

    result = graphite.sync_idempotent(tmp_path, force=True, quiet=False)

    assert isinstance(result, SyncError)
    assert result.success is False
    assert result.error_type == "other-branch-conflict"
    assert "unstaged changes" in result.message


def test_sync_idempotent_classifies_unknown_errors_as_sync_failed(
    tmp_path: Path,
) -> None:
    """sync_idempotent classifies unknown errors as sync-failed."""
    graphite = FakeGraphite(
        sync_raises=RuntimeError("network timeout"),
    )

    result = graphite.sync_idempotent(tmp_path, force=True, quiet=False)

    assert isinstance(result, SyncError)
    assert result.success is False
    assert result.error_type == "sync-failed"
    assert "network timeout" in result.message


def test_sync_idempotent_passes_force_and_quiet_through(tmp_path: Path) -> None:
    """sync_idempotent passes force and quiet parameters to underlying sync()."""
    graphite = FakeGraphite()

    graphite.sync_idempotent(tmp_path, force=False, quiet=True)

    assert len(graphite.sync_calls) == 1
    assert graphite.sync_calls[0] == (tmp_path, False, True)
