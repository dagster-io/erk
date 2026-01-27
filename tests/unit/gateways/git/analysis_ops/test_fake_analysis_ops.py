"""Tests for FakeGitAnalysisOps."""

from pathlib import Path

from erk_shared.gateway.git.analysis_ops.fake import FakeGitAnalysisOps


def test_count_commits_ahead_returns_configured_count() -> None:
    """Test that count_commits_ahead returns the configured count."""
    cwd = Path("/repo")
    base_branch = "main"

    fake = FakeGitAnalysisOps(commits_ahead={(cwd, base_branch): 3})

    result = fake.count_commits_ahead(cwd, base_branch)
    assert result == 3


def test_count_commits_ahead_returns_zero_when_not_configured() -> None:
    """Test that count_commits_ahead returns 0 when not configured."""
    fake = FakeGitAnalysisOps(commits_ahead={})

    result = fake.count_commits_ahead(Path("/repo"), "main")
    assert result == 0


def test_get_merge_base_returns_configured_sha() -> None:
    """Test that get_merge_base returns the configured SHA."""
    repo_root = Path("/repo")
    ref1 = "main"
    ref2 = "feature"
    merge_base = "abc123"

    fake = FakeGitAnalysisOps(merge_bases={(repo_root, ref1, ref2): merge_base})

    result = fake.get_merge_base(repo_root, ref1, ref2)
    assert result == merge_base


def test_get_merge_base_returns_none_when_not_configured() -> None:
    """Test that get_merge_base returns None when not configured."""
    fake = FakeGitAnalysisOps(merge_bases={})

    result = fake.get_merge_base(Path("/repo"), "main", "feature")
    assert result is None


def test_get_diff_to_branch_returns_configured_diff() -> None:
    """Test that get_diff_to_branch returns the configured diff."""
    cwd = Path("/repo")
    branch = "main"
    diff_content = "diff --git a/file.txt b/file.txt"

    fake = FakeGitAnalysisOps(diffs={(cwd, branch): diff_content})

    result = fake.get_diff_to_branch(cwd, branch)
    assert result == diff_content


def test_get_diff_to_branch_returns_empty_when_not_configured() -> None:
    """Test that get_diff_to_branch returns empty string when not configured."""
    fake = FakeGitAnalysisOps(diffs={})

    result = fake.get_diff_to_branch(Path("/repo"), "main")
    assert result == ""


def test_link_state_updates_internal_state() -> None:
    """Test that link_state method updates the fake's state."""
    fake = FakeGitAnalysisOps()

    commits_ahead = {(Path("/repo"), "main"): 5}
    merge_bases = {(Path("/repo"), "main", "feature"): "def456"}
    diffs = {(Path("/repo"), "main"): "some diff"}

    fake.link_state(
        commits_ahead=commits_ahead,
        merge_bases=merge_bases,
        diffs=diffs,
    )

    assert fake.count_commits_ahead(Path("/repo"), "main") == 5
    assert fake.get_merge_base(Path("/repo"), "main", "feature") == "def456"
    assert fake.get_diff_to_branch(Path("/repo"), "main") == "some diff"
