"""Unit tests for list_sessions kit CLI command.

Tests session discovery, relative time formatting, branch context detection,
and summary extraction using FakeClaudeInstallation.
"""

import json
import time
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.list_sessions import (
    _list_sessions_from_store,
    format_display_time,
    format_relative_time,
    get_branch_context,
    list_sessions,
)
from erk_shared.context import ErkContext
from erk_shared.git.fake import FakeGit
from erk_shared.learn.extraction.claude_installation.fake import (
    FakeClaudeInstallation,
    FakeProject,
    FakeSessionData,
)
from erk_shared.learn.extraction.session_schema import (
    extract_first_user_message_text,
    extract_git_branch,
)


def _user_msg(text: str, *, branch: str | None = None) -> str:
    """Create JSON content for a user message.

    Args:
        text: The message content.
        branch: Optional git branch to include as gitBranch field.

    Returns:
        JSON string representing a user message entry.
    """
    entry: dict[str, object] = {"type": "user", "message": {"content": text}}
    if branch is not None:
        entry["gitBranch"] = branch
    return json.dumps(entry)


# ============================================================================
# 1. Relative Time Formatting Tests (7 tests)
# ============================================================================


def test_format_relative_time_just_now() -> None:
    """Test that times < 30s show 'just now'."""
    now = time.time()
    assert format_relative_time(now - 10) == "just now"
    assert format_relative_time(now - 29) == "just now"


def test_format_relative_time_minutes() -> None:
    """Test that times < 1h show minutes."""
    now = time.time()
    assert format_relative_time(now - 60) == "1m ago"
    assert format_relative_time(now - 180) == "3m ago"
    assert format_relative_time(now - 3540) == "59m ago"


def test_format_relative_time_hours() -> None:
    """Test that times < 24h show hours."""
    now = time.time()
    assert format_relative_time(now - 3600) == "1h ago"
    assert format_relative_time(now - 7200) == "2h ago"
    assert format_relative_time(now - 82800) == "23h ago"


def test_format_relative_time_days() -> None:
    """Test that times < 7d show days."""
    now = time.time()
    assert format_relative_time(now - 86400) == "1d ago"
    assert format_relative_time(now - 172800) == "2d ago"
    assert format_relative_time(now - 518400) == "6d ago"


def test_format_relative_time_older_than_week() -> None:
    """Test that times >= 7d show absolute date."""
    now = time.time()
    result = format_relative_time(now - 604800)  # exactly 7 days
    # Should return absolute date format (e.g., "Dec 3, 11:38 AM")
    assert "ago" not in result
    # Should contain month abbreviation and time
    assert any(
        month in result
        for month in [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
    )


def test_format_relative_time_boundary_30_seconds() -> None:
    """Test boundary at 30 seconds."""
    now = time.time()
    assert format_relative_time(now - 29) == "just now"
    assert format_relative_time(now - 31) == "0m ago" or format_relative_time(now - 61) == "1m ago"


def test_format_display_time_format() -> None:
    """Test display time format."""
    # Use a fixed timestamp for predictable output
    # 2024-12-03 11:38:00 UTC
    import datetime

    dt = datetime.datetime(2024, 12, 3, 11, 38, 0)
    mtime = dt.timestamp()
    result = format_display_time(mtime)
    assert "Dec" in result
    assert "3" in result
    assert "11:38" in result or "11:38 AM" in result


# ============================================================================
# 2. Summary Extraction Tests (8 tests)
# ============================================================================


def test_extract_summary_string_content() -> None:
    """Test extraction from user message with string content."""
    content = json.dumps(
        {"type": "user", "message": {"content": "how many session ids does this correspond to?"}}
    )
    result = extract_first_user_message_text(content, max_length=None)
    assert result == "how many session ids does this correspond to?"


def test_extract_summary_structured_content() -> None:
    """Test extraction from user message with structured content."""
    msg = {"type": "user", "message": {"content": [{"type": "text", "text": "Please help"}]}}
    content = json.dumps(msg)
    result = extract_first_user_message_text(content, max_length=None)
    assert result == "Please help"


def test_extract_summary_truncates_long_text() -> None:
    """Test that long summaries are truncated with ellipsis."""
    long_text = "x" * 100
    content = json.dumps({"type": "user", "message": {"content": long_text}})
    result = extract_first_user_message_text(content, max_length=60)
    assert len(result) == 60
    assert result.endswith("...")


def test_extract_summary_skips_assistant_messages() -> None:
    """Test that assistant messages are skipped to find first user message."""
    asst_msg = {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hello"}]}}
    user_msg = {"type": "user", "message": {"content": "My actual question"}}
    lines = [json.dumps(asst_msg), json.dumps(user_msg)]
    content = "\n".join(lines)
    result = extract_first_user_message_text(content, max_length=None)
    assert result == "My actual question"


def test_extract_summary_empty_content() -> None:
    """Test handling of empty content."""
    result = extract_first_user_message_text("", max_length=None)
    assert result == ""


def test_extract_summary_no_user_messages() -> None:
    """Test handling of content with no user messages."""
    msg = {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi"}]}}
    content = json.dumps(msg)
    result = extract_first_user_message_text(content, max_length=None)
    assert result == ""


def test_extract_summary_handles_malformed_json() -> None:
    """Test handling of malformed JSON in content."""
    content = "{invalid json}\n" + json.dumps({"type": "user", "message": {"content": "Valid"}})
    result = extract_first_user_message_text(content, max_length=None)
    # Should find the valid entry after skipping malformed
    assert result == "Valid"


def test_extract_summary_content_with_newlines() -> None:
    """Test handling of multi-line content."""
    content = json.dumps({"type": "user", "message": {"content": "Line one"}})
    result = extract_first_user_message_text(content, max_length=None)
    assert result == "Line one"


# ============================================================================
# 3. Git Branch Extraction Tests (4 tests)
# ============================================================================


def test_extract_git_branch_from_first_entry() -> None:
    """Test that gitBranch is extracted from the first entry with that field."""
    content = _user_msg("Hello", branch="feature-xyz")
    result = extract_git_branch(content)
    assert result == "feature-xyz"


def test_extract_git_branch_finds_first_branch() -> None:
    """Test that gitBranch returns the first branch found."""
    # First entry with branch, second entry with different branch
    line1 = json.dumps({"type": "user", "message": {"content": "First"}, "gitBranch": "feature-a"})
    line2 = json.dumps({"type": "user", "message": {"content": "Second"}, "gitBranch": "feature-b"})
    content = f"{line1}\n{line2}"
    result = extract_git_branch(content)
    assert result == "feature-a"


def test_extract_git_branch_no_branch_field() -> None:
    """Test that None is returned when no gitBranch field exists."""
    content = _user_msg("No branch here")
    result = extract_git_branch(content)
    assert result is None


def test_extract_git_branch_empty_content() -> None:
    """Test handling of empty content."""
    result = extract_git_branch("")
    assert result is None


# ============================================================================
# 4. Session Discovery Tests (7 tests) - Using FakeClaudeInstallation
# ============================================================================


def test_list_sessions_finds_all_sessions(tmp_path: Path) -> None:
    """Test that all sessions are discovered from store."""
    fake_store = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "abc123": FakeSessionData(
                        content=_user_msg("Session abc123"),
                        size_bytes=100,
                        modified_at=1000.0,
                    ),
                    "def456": FakeSessionData(
                        content=_user_msg("Session def456"),
                        size_bytes=100,
                        modified_at=2000.0,
                    ),
                    "ghi789": FakeSessionData(
                        content=_user_msg("Session ghi789"),
                        size_bytes=100,
                        modified_at=3000.0,
                    ),
                }
            )
        }
    )

    sessions, filtered_count = _list_sessions_from_store(
        claude_installation=fake_store, cwd=tmp_path, current_session_id=None, limit=10, min_size=0
    )
    assert len(sessions) == 3
    assert filtered_count == 0


def test_list_sessions_sorted_by_mtime(tmp_path: Path) -> None:
    """Test that sessions are sorted by mtime (newest first)."""
    fake_store = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "old": FakeSessionData(
                        content=json.dumps({"type": "user", "message": {"content": "Old"}}),
                        size_bytes=100,
                        modified_at=1000.0,
                    ),
                    "new": FakeSessionData(
                        content=json.dumps({"type": "user", "message": {"content": "New"}}),
                        size_bytes=100,
                        modified_at=2000.0,
                    ),
                }
            )
        }
    )

    sessions, filtered_count = _list_sessions_from_store(
        claude_installation=fake_store, cwd=tmp_path, current_session_id=None, limit=10, min_size=0
    )
    assert len(sessions) == 2
    assert sessions[0].session_id == "new"  # Newest first
    assert sessions[1].session_id == "old"
    assert filtered_count == 0


def test_list_sessions_respects_limit(tmp_path: Path) -> None:
    """Test that limit parameter is respected."""
    fake_store = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    f"session{i:02d}": FakeSessionData(
                        content=_user_msg(f"Session {i}"),
                        size_bytes=100,
                        modified_at=float(i),
                    )
                    for i in range(20)
                }
            )
        }
    )

    sessions, filtered_count = _list_sessions_from_store(
        claude_installation=fake_store, cwd=tmp_path, current_session_id=None, limit=5, min_size=0
    )
    assert len(sessions) == 5
    assert filtered_count == 0


def test_list_sessions_marks_current(tmp_path: Path) -> None:
    """Test that current session is marked correctly."""
    fake_store = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "current123": FakeSessionData(
                        content=_user_msg("Current"),
                        size_bytes=100,
                        modified_at=2000.0,
                    ),
                    "other456": FakeSessionData(
                        content=_user_msg("Other"),
                        size_bytes=100,
                        modified_at=1000.0,
                    ),
                }
            )
        }
    )

    sessions, filtered_count = _list_sessions_from_store(
        claude_installation=fake_store,
        cwd=tmp_path,
        current_session_id="current123",
        limit=10,
        min_size=0,
    )

    current = next(s for s in sessions if s.session_id == "current123")
    other = next(s for s in sessions if s.session_id == "other456")

    assert current.is_current is True
    assert other.is_current is False
    assert filtered_count == 0


def test_list_sessions_empty_project(tmp_path: Path) -> None:
    """Test handling of project with no sessions."""
    fake_store = FakeClaudeInstallation.for_test(projects={tmp_path: FakeProject(sessions={})})

    sessions, filtered_count = _list_sessions_from_store(
        claude_installation=fake_store, cwd=tmp_path, current_session_id=None, limit=10, min_size=0
    )
    assert sessions == []
    assert filtered_count == 0


def test_list_sessions_nonexistent_project(tmp_path: Path) -> None:
    """Test handling of nonexistent project."""
    fake_store = FakeClaudeInstallation.for_test()  # No projects

    sessions, filtered_count = _list_sessions_from_store(
        claude_installation=fake_store, cwd=tmp_path, current_session_id=None, limit=10, min_size=0
    )
    assert sessions == []
    assert filtered_count == 0


def test_list_sessions_extracts_summaries(tmp_path: Path) -> None:
    """Test that summaries are extracted from session content."""
    fake_store = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "session1": FakeSessionData(
                        content=json.dumps({"type": "user", "message": {"content": "Hello world"}}),
                        size_bytes=100,
                        modified_at=1000.0,
                    )
                }
            )
        }
    )

    sessions, _ = _list_sessions_from_store(
        claude_installation=fake_store, cwd=tmp_path, current_session_id=None, limit=10, min_size=0
    )
    assert len(sessions) == 1
    assert sessions[0].summary == "Hello world"


def test_list_sessions_extracts_branch(tmp_path: Path) -> None:
    """Test that branch is extracted from session content."""
    fake_store = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "session1": FakeSessionData(
                        content=_user_msg("Hello", branch="feature-xyz"),
                        size_bytes=100,
                        modified_at=1000.0,
                    )
                }
            )
        }
    )

    sessions, _ = _list_sessions_from_store(
        claude_installation=fake_store, cwd=tmp_path, current_session_id=None, limit=10, min_size=0
    )
    assert len(sessions) == 1
    assert sessions[0].branch == "feature-xyz"


def test_list_sessions_branch_none_when_missing(tmp_path: Path) -> None:
    """Test that branch is None when session has no gitBranch field."""
    fake_store = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "session1": FakeSessionData(
                        content=_user_msg("Hello"),  # No branch
                        size_bytes=100,
                        modified_at=1000.0,
                    )
                }
            )
        }
    )

    sessions, _ = _list_sessions_from_store(
        claude_installation=fake_store, cwd=tmp_path, current_session_id=None, limit=10, min_size=0
    )
    assert len(sessions) == 1
    assert sessions[0].branch is None


def test_list_sessions_populates_session_path(tmp_path: Path) -> None:
    """Test that session_path is populated with absolute path to session file."""
    fake_store = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "abc123": FakeSessionData(
                        content=_user_msg("Test session"),
                        size_bytes=100,
                        modified_at=1000.0,
                    )
                }
            )
        }
    )

    sessions, _ = _list_sessions_from_store(
        claude_installation=fake_store, cwd=tmp_path, current_session_id=None, limit=10, min_size=0
    )
    assert len(sessions) == 1
    # FakeClaudeInstallation returns project_path / "<session_id>.jsonl"
    expected_path = str(tmp_path / "abc123.jsonl")
    assert sessions[0].session_path == expected_path


# ============================================================================
# 5. Branch Context Tests (5 tests)
# ============================================================================


def test_get_branch_context_on_feature_branch(tmp_path: Path) -> None:
    """Test branch context detection on feature branch."""
    git = FakeGit(
        current_branches={tmp_path: "feature-xyz"},
        trunk_branches={tmp_path: "main"},
    )

    context = get_branch_context(git, tmp_path)
    assert context.current_branch == "feature-xyz"
    assert context.trunk_branch == "main"
    assert context.is_on_trunk is False


def test_get_branch_context_on_main_branch(tmp_path: Path) -> None:
    """Test branch context detection on main branch."""
    git = FakeGit(
        current_branches={tmp_path: "main"},
        trunk_branches={tmp_path: "main"},
    )

    context = get_branch_context(git, tmp_path)
    assert context.current_branch == "main"
    assert context.trunk_branch == "main"
    assert context.is_on_trunk is True


def test_get_branch_context_detects_master_trunk(tmp_path: Path) -> None:
    """Test that master is detected as trunk when it exists."""
    git = FakeGit(
        current_branches={tmp_path: "master"},
        trunk_branches={tmp_path: "master"},
    )

    context = get_branch_context(git, tmp_path)
    assert context.current_branch == "master"
    assert context.trunk_branch == "master"
    assert context.is_on_trunk is True


def test_get_branch_context_no_git_repo(tmp_path: Path) -> None:
    """Test branch context when no branch is available (defaults to empty)."""
    # FakeGit with no current_branches configured returns None for get_current_branch
    git = FakeGit()

    context = get_branch_context(git, tmp_path)
    assert context.current_branch == ""
    assert context.trunk_branch == "main"  # FakeGit defaults to "main"
    assert context.is_on_trunk is False


def test_get_branch_context_empty_repo(tmp_path: Path) -> None:
    """Test branch context when current branch is None (empty/new repo)."""
    # Simulates git repo with no commits (no current branch yet)
    git = FakeGit(
        current_branches={tmp_path: None},
        trunk_branches={tmp_path: "main"},
    )

    context = get_branch_context(git, tmp_path)
    # When current_branch is None, we get empty string (per or "" fallback)
    assert context.current_branch == ""
    assert context.trunk_branch == "main"
    assert context.is_on_trunk is False


# ============================================================================
# 6. CLI Command Tests (5 tests) - Using FakeClaudeInstallation
# ============================================================================


def test_cli_success(tmp_path: Path) -> None:
    """Test CLI command with successful session listing."""
    git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        trunk_branches={tmp_path: "main"},
    )
    fake_store = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "abc123": FakeSessionData(
                        content=_user_msg("Test session"),
                        size_bytes=100,
                        modified_at=1234567890.0,
                    )
                }
            )
        }
    )
    context = ErkContext.for_test(git=git, claude_installation=fake_store, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(list_sessions, [], obj=context)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert len(output["sessions"]) == 1
    assert output["sessions"][0]["session_id"] == "abc123"


def test_cli_project_not_found(tmp_path: Path) -> None:
    """Test CLI command error when project not found."""
    git = FakeGit(
        current_branches={tmp_path: "main"},
        trunk_branches={tmp_path: "main"},
    )
    # Empty installation - no projects
    fake_store = FakeClaudeInstallation.for_test()
    context = ErkContext.for_test(git=git, claude_installation=fake_store, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(list_sessions, [], obj=context)

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "error" in output


def test_cli_output_structure(tmp_path: Path) -> None:
    """Test that CLI output has expected structure."""
    git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        trunk_branches={tmp_path: "main"},
    )
    fake_store = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "session": FakeSessionData(
                        content=json.dumps({"type": "user", "message": {"content": "Test"}}),
                        size_bytes=100,
                        modified_at=1234567890.0,
                    )
                }
            )
        }
    )
    context = ErkContext.for_test(git=git, claude_installation=fake_store, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(list_sessions, [], obj=context)

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "branch_context" in output
    assert "current_session_id" in output
    assert "sessions" in output
    assert "project_dir" in output

    # Verify branch_context structure
    assert "current_branch" in output["branch_context"]
    assert "trunk_branch" in output["branch_context"]
    assert "is_on_trunk" in output["branch_context"]

    # Verify session structure
    if output["sessions"]:
        session = output["sessions"][0]
        assert "session_id" in session
        assert "mtime_display" in session
        assert "mtime_relative" in session
        assert "mtime_unix" in session
        assert "size_bytes" in session
        assert "summary" in session
        assert "is_current" in session
        assert "branch" in session
        assert "session_path" in session


def test_cli_limit_option(tmp_path: Path) -> None:
    """Test CLI --limit option."""
    git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        trunk_branches={tmp_path: "main"},
    )
    fake_store = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    f"session{i:02d}": FakeSessionData(
                        content=_user_msg(f"Session {i}"),
                        size_bytes=100,
                        modified_at=float(i),
                    )
                    for i in range(10)
                }
            )
        }
    )
    context = ErkContext.for_test(git=git, claude_installation=fake_store, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(list_sessions, ["--limit", "3"], obj=context)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert len(output["sessions"]) == 3


def test_cli_marks_current_session(tmp_path: Path) -> None:
    """Test that CLI marks current session from --session-id option."""
    git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        trunk_branches={tmp_path: "main"},
    )
    fake_store = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "current-session": FakeSessionData(
                        content=json.dumps({"type": "user", "message": {"content": "Current"}}),
                        size_bytes=100,
                        modified_at=2000.0,
                    ),
                    "other-session": FakeSessionData(
                        content=json.dumps({"type": "user", "message": {"content": "Other"}}),
                        size_bytes=100,
                        modified_at=1000.0,
                    ),
                }
            )
        }
    )
    context = ErkContext.for_test(git=git, claude_installation=fake_store, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(list_sessions, ["--session-id", "current-session"], obj=context)

    assert result.exit_code == 0
    output = json.loads(result.output)

    current = next(s for s in output["sessions"] if s["session_id"] == "current-session")
    other = next(s for s in output["sessions"] if s["session_id"] == "other-session")

    assert current["is_current"] is True
    assert other["is_current"] is False


# ============================================================================
# 7. Size Filtering Tests (4 tests)
# ============================================================================


def test_list_sessions_min_size_filters_tiny_sessions(tmp_path: Path) -> None:
    """Test that --min-size filters out tiny sessions."""
    fake_store = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "tiny": FakeSessionData(
                        content="x",
                        size_bytes=10,
                        modified_at=1000.0,
                    ),
                    "large": FakeSessionData(
                        content=json.dumps({"type": "user", "message": {"content": "x" * 2000}}),
                        size_bytes=2000,
                        modified_at=2000.0,
                    ),
                }
            )
        }
    )

    sessions, filtered_count = _list_sessions_from_store(
        claude_installation=fake_store,
        cwd=tmp_path,
        current_session_id=None,
        limit=10,
        min_size=100,
    )

    assert len(sessions) == 1
    assert sessions[0].session_id == "large"
    assert filtered_count == 1


def test_list_sessions_min_size_zero_no_filtering(tmp_path: Path) -> None:
    """Test that min_size=0 (default) does not filter."""
    fake_store = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "tiny": FakeSessionData(
                        content="x",
                        size_bytes=1,
                        modified_at=1000.0,
                    ),
                    "large": FakeSessionData(
                        content="x" * 1000,
                        size_bytes=1000,
                        modified_at=2000.0,
                    ),
                }
            )
        }
    )

    sessions, filtered_count = _list_sessions_from_store(
        claude_installation=fake_store, cwd=tmp_path, current_session_id=None, limit=10, min_size=0
    )

    assert len(sessions) == 2
    assert filtered_count == 0


def test_list_sessions_all_filtered(tmp_path: Path) -> None:
    """Test when all sessions are filtered by size."""
    fake_store = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "tiny1": FakeSessionData(
                        content="x",
                        size_bytes=1,
                        modified_at=1000.0,
                    ),
                    "tiny2": FakeSessionData(
                        content="xx",
                        size_bytes=2,
                        modified_at=2000.0,
                    ),
                }
            )
        }
    )

    sessions, filtered_count = _list_sessions_from_store(
        claude_installation=fake_store,
        cwd=tmp_path,
        current_session_id=None,
        limit=10,
        min_size=1000,
    )

    assert len(sessions) == 0
    assert filtered_count == 2


def test_cli_min_size_option(tmp_path: Path) -> None:
    """Test CLI --min-size option."""
    git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )
    fake_store = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "tiny": FakeSessionData(
                        content="x",
                        size_bytes=10,
                        modified_at=1000.0,
                    ),
                    "large": FakeSessionData(
                        content=json.dumps({"type": "user", "message": {"content": "x" * 2000}}),
                        size_bytes=2000,
                        modified_at=2000.0,
                    ),
                }
            )
        }
    )
    context = ErkContext.for_test(git=git, claude_installation=fake_store, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(list_sessions, ["--min-size", "100"], obj=context)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert len(output["sessions"]) == 1
    assert output["filtered_count"] == 1
