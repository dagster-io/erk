"""Unit tests for FakeGitRemoteOps query methods."""

from pathlib import Path

from erk_shared.gateway.git.remote_ops.fake import FakeGitRemoteOps


def test_get_remote_ref_returns_configured_sha(tmp_path: Path) -> None:
    """get_remote_ref returns SHA when configured for the given key."""
    fake = FakeGitRemoteOps(remote_refs={(tmp_path, "origin", "main"): "abc123def456"})
    assert fake.get_remote_ref(tmp_path, "origin", "main") == "abc123def456"


def test_get_remote_ref_returns_none_for_missing(tmp_path: Path) -> None:
    """get_remote_ref returns None when no ref is configured."""
    fake = FakeGitRemoteOps()
    assert fake.get_remote_ref(tmp_path, "origin", "nonexistent") is None


def test_get_local_tracking_ref_sha_returns_configured(tmp_path: Path) -> None:
    """get_local_tracking_ref_sha returns SHA when configured."""
    fake = FakeGitRemoteOps(local_tracking_refs={(tmp_path, "origin", "main"): "abc123"})
    assert fake.get_local_tracking_ref_sha(tmp_path, "origin", "main") == "abc123"


def test_get_local_tracking_ref_sha_returns_none_for_missing(tmp_path: Path) -> None:
    """get_local_tracking_ref_sha returns None when not configured."""
    fake = FakeGitRemoteOps()
    assert fake.get_local_tracking_ref_sha(tmp_path, "origin", "nonexistent") is None
