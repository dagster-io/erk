"""Unit tests for FakeGitCommitOps.read_file_from_ref()."""

from pathlib import Path

from erk_shared.fakes.git_commit_ops import FakeGitCommitOps


def test_read_file_from_ref_returns_configured_content() -> None:
    """Returns bytes for a configured (ref, file_path) entry."""
    content = b'{"version": 1}'
    fake = FakeGitCommitOps(
        ref_file_contents={("origin/main", "manifest.json"): content},
    )
    result = fake.read_file_from_ref(Path("/repo"), ref="origin/main", file_path="manifest.json")
    assert result == content


def test_read_file_from_ref_returns_none_for_missing_entry() -> None:
    """Returns None when (ref, file_path) is not configured."""
    fake = FakeGitCommitOps(
        ref_file_contents={("origin/main", "manifest.json"): b"data"},
    )
    result = fake.read_file_from_ref(Path("/repo"), ref="origin/main", file_path="other.json")
    assert result is None


def test_read_file_from_ref_returns_none_with_empty_config() -> None:
    """Returns None when no ref_file_contents configured."""
    fake = FakeGitCommitOps()
    result = fake.read_file_from_ref(Path("/repo"), ref="origin/main", file_path="manifest.json")
    assert result is None
