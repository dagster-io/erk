"""Tests for diff extraction operation.

Tests the execute_diff_extraction function that gets PR diff from GitHub API
and writes it to a scratch file for AI analysis.
"""

from pathlib import Path

from erk_shared.context.testing import context_for_test
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.pr.diff_extraction import execute_diff_extraction


def test_execute_diff_extraction_success(tmp_path: Path) -> None:
    """Test successful diff extraction."""
    # Create repo root structure
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    scratch_dir = repo_root / ".tmp" / "test-session"
    scratch_dir.mkdir(parents=True)

    git = FakeGit(
        git_common_dirs={tmp_path: repo_root},
        repository_roots={tmp_path: str(repo_root)},
    )

    github = FakeGitHub(
        pr_diffs={123: "diff --git a/file.py b/file.py\n+new line"},
    )

    ctx = context_for_test(git=git, github=github, graphite=FakeGraphite(), cwd=tmp_path)

    # Collect events
    events = list(execute_diff_extraction(ctx, tmp_path, pr_number=123, session_id="test-session"))

    # Should have progress events and completion
    progress_events = [e for e in events if isinstance(e, ProgressEvent)]
    completion_events = [e for e in events if isinstance(e, CompletionEvent)]

    assert len(progress_events) >= 2  # "Getting PR diff..." and "Diff written to..."
    assert len(completion_events) == 1

    # Check result is a Path
    result = completion_events[0].result
    assert isinstance(result, Path)
    assert result.exists()

    # Verify diff content was written
    content = result.read_text(encoding="utf-8")
    assert "diff --git" in content
    assert "+new line" in content


def test_execute_diff_extraction_truncates_large_diff(tmp_path: Path) -> None:
    """Test that large diffs are truncated."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    scratch_dir = repo_root / ".tmp" / "test-session"
    scratch_dir.mkdir(parents=True)

    git = FakeGit(
        git_common_dirs={tmp_path: repo_root},
        repository_roots={tmp_path: str(repo_root)},
    )

    # Create a very large diff (over 1M chars - the MAX_DIFF_CHARS threshold)
    large_diff = "diff --git a/file.py b/file.py\n" + "+" + "a" * 1_100_000

    github = FakeGitHub(
        pr_diffs={123: large_diff},
    )

    ctx = context_for_test(git=git, github=github, graphite=FakeGraphite(), cwd=tmp_path)

    events = list(execute_diff_extraction(ctx, tmp_path, pr_number=123, session_id="test-session"))

    # Should have a warning about truncation
    progress_events = [e for e in events if isinstance(e, ProgressEvent)]
    warning_events = [e for e in progress_events if e.style == "warning"]
    assert len(warning_events) == 1
    assert "truncated" in warning_events[0].message.lower()

    # Result should still be a valid path
    completion_events = [e for e in events if isinstance(e, CompletionEvent)]
    result = completion_events[0].result
    assert isinstance(result, Path)
    assert result.exists()


def test_execute_diff_extraction_progress_messages(tmp_path: Path) -> None:
    """Test that appropriate progress messages are emitted."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    scratch_dir = repo_root / ".tmp" / "test-session"
    scratch_dir.mkdir(parents=True)

    git = FakeGit(
        git_common_dirs={tmp_path: repo_root},
        repository_roots={tmp_path: str(repo_root)},
    )

    github = FakeGitHub(
        pr_diffs={123: "diff content\nline 2\nline 3"},
    )

    ctx = context_for_test(git=git, github=github, graphite=FakeGraphite(), cwd=tmp_path)

    events = list(execute_diff_extraction(ctx, tmp_path, pr_number=123, session_id="test-session"))

    progress_events = [e for e in events if isinstance(e, ProgressEvent)]
    messages = [e.message for e in progress_events]

    # Should report getting diff
    assert any("Getting PR diff" in m for m in messages)
    # Should report diff retrieved with line count
    assert any("3 lines" in m for m in messages)
    # Should report diff written
    assert any("Diff written" in m for m in messages)
