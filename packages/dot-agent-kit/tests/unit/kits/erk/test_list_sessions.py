"""Unit tests for list_sessions kit CLI command.

Tests session discovery, relative time formatting, branch context detection,
and summary extraction.
"""

import json
import os
import time
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
from erk_shared.git.fake import FakeGit

from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.list_sessions import (
    extract_summary,
    format_display_time,
    format_relative_time,
    get_branch_context,
    get_current_session_id,
    list_sessions,
    list_sessions_cli,
)

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
# 2. Session ID Extraction Tests (4 tests)
# ============================================================================


def test_get_current_session_id_from_env() -> None:
    """Test extraction of session ID from SESSION_CONTEXT env var."""
    with patch.dict(os.environ, {"SESSION_CONTEXT": "session_id=abc123-def456"}):
        assert get_current_session_id() == "abc123-def456"


def test_get_current_session_id_no_env() -> None:
    """Test that None is returned when env var not set."""
    with patch.dict(os.environ, {}, clear=True):
        # Remove SESSION_CONTEXT if it exists
        env_copy = dict(os.environ)
        env_copy.pop("SESSION_CONTEXT", None)
        with patch.dict(os.environ, env_copy, clear=True):
            assert get_current_session_id() is None


def test_get_current_session_id_empty_env() -> None:
    """Test that None is returned when env var is empty."""
    with patch.dict(os.environ, {"SESSION_CONTEXT": ""}):
        assert get_current_session_id() is None


def test_get_current_session_id_invalid_format() -> None:
    """Test that None is returned when format is invalid."""
    with patch.dict(os.environ, {"SESSION_CONTEXT": "not_a_session_id"}):
        assert get_current_session_id() is None


# ============================================================================
# 3. Summary Extraction Tests (8 tests)
# ============================================================================


def test_extract_summary_string_content(tmp_path: Path) -> None:
    """Test extraction from user message with string content."""
    log_file = tmp_path / "session.jsonl"
    entry = {
        "type": "user",
        "message": {"content": "how many session ids does this correspond to?"},
    }
    log_file.write_text(json.dumps(entry), encoding="utf-8")

    result = extract_summary(log_file)
    assert result == "how many session ids does this correspond to?"


def test_extract_summary_structured_content(tmp_path: Path) -> None:
    """Test extraction from user message with structured content."""
    log_file = tmp_path / "session.jsonl"
    entry = {
        "type": "user",
        "message": {"content": [{"type": "text", "text": "Please help with this task"}]},
    }
    log_file.write_text(json.dumps(entry), encoding="utf-8")

    result = extract_summary(log_file)
    assert result == "Please help with this task"


def test_extract_summary_truncates_long_text(tmp_path: Path) -> None:
    """Test that long summaries are truncated with ellipsis."""
    log_file = tmp_path / "session.jsonl"
    long_text = "x" * 100
    entry = {"type": "user", "message": {"content": long_text}}
    log_file.write_text(json.dumps(entry), encoding="utf-8")

    result = extract_summary(log_file, max_length=60)
    assert len(result) == 60
    assert result.endswith("...")


def test_extract_summary_skips_assistant_messages(tmp_path: Path) -> None:
    """Test that assistant messages are skipped to find first user message."""
    log_file = tmp_path / "session.jsonl"
    entries = [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hello there"}]}},
        {"type": "user", "message": {"content": "My actual question"}},
    ]
    log_file.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

    result = extract_summary(log_file)
    assert result == "My actual question"


def test_extract_summary_empty_file(tmp_path: Path) -> None:
    """Test handling of empty log file."""
    log_file = tmp_path / "session.jsonl"
    log_file.write_text("", encoding="utf-8")

    result = extract_summary(log_file)
    assert result == ""


def test_extract_summary_no_user_messages(tmp_path: Path) -> None:
    """Test handling of file with no user messages."""
    log_file = tmp_path / "session.jsonl"
    entry = {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi"}]}}
    log_file.write_text(json.dumps(entry), encoding="utf-8")

    result = extract_summary(log_file)
    assert result == ""


def test_extract_summary_handles_malformed_json(tmp_path: Path) -> None:
    """Test handling of malformed JSON in log file."""
    log_file = tmp_path / "session.jsonl"
    log_file.write_text(
        "{invalid json}\n" + json.dumps({"type": "user", "message": {"content": "Valid"}}),
        encoding="utf-8",
    )

    result = extract_summary(log_file)
    # Should find the valid entry after skipping malformed
    assert result == "Valid"


def test_extract_summary_nonexistent_file(tmp_path: Path) -> None:
    """Test handling of nonexistent file."""
    log_file = tmp_path / "nonexistent.jsonl"

    result = extract_summary(log_file)
    assert result == ""


# ============================================================================
# 4. Session Discovery Tests (7 tests)
# ============================================================================


def test_list_sessions_finds_all_sessions(tmp_path: Path) -> None:
    """Test that all session files are discovered."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create session files
    for name in ["abc123.jsonl", "def456.jsonl", "ghi789.jsonl"]:
        (project_dir / name).write_text(
            json.dumps({"type": "user", "message": {"content": f"Session {name}"}}),
            encoding="utf-8",
        )

    sessions = list_sessions(project_dir, None, limit=10)
    assert len(sessions) == 3


def test_list_sessions_excludes_agent_logs(tmp_path: Path) -> None:
    """Test that agent-* files are excluded."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create session and agent files
    (project_dir / "main123.jsonl").write_text(
        json.dumps({"type": "user", "message": {"content": "Main session"}}),
        encoding="utf-8",
    )
    (project_dir / "agent-abc.jsonl").write_text(
        json.dumps({"type": "user", "message": {"content": "Agent log"}}),
        encoding="utf-8",
    )

    sessions = list_sessions(project_dir, None, limit=10)
    assert len(sessions) == 1
    assert sessions[0].session_id == "main123"


def test_list_sessions_sorted_by_mtime(tmp_path: Path) -> None:
    """Test that sessions are sorted by mtime (newest first)."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create files with different mtimes
    old = project_dir / "old.jsonl"
    old.write_text(json.dumps({"type": "user", "message": {"content": "Old"}}), encoding="utf-8")
    time.sleep(0.02)

    new = project_dir / "new.jsonl"
    new.write_text(json.dumps({"type": "user", "message": {"content": "New"}}), encoding="utf-8")

    sessions = list_sessions(project_dir, None, limit=10)
    assert len(sessions) == 2
    assert sessions[0].session_id == "new"  # Newest first
    assert sessions[1].session_id == "old"


def test_list_sessions_respects_limit(tmp_path: Path) -> None:
    """Test that limit parameter is respected."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create many session files
    for i in range(20):
        (project_dir / f"session{i:02d}.jsonl").write_text(
            json.dumps({"type": "user", "message": {"content": f"Session {i}"}}),
            encoding="utf-8",
        )
        time.sleep(0.001)  # Ensure different mtimes

    sessions = list_sessions(project_dir, None, limit=5)
    assert len(sessions) == 5


def test_list_sessions_marks_current(tmp_path: Path) -> None:
    """Test that current session is marked correctly."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    (project_dir / "current123.jsonl").write_text(
        json.dumps({"type": "user", "message": {"content": "Current"}}),
        encoding="utf-8",
    )
    (project_dir / "other456.jsonl").write_text(
        json.dumps({"type": "user", "message": {"content": "Other"}}),
        encoding="utf-8",
    )

    sessions = list_sessions(project_dir, "current123", limit=10)

    current = next(s for s in sessions if s.session_id == "current123")
    other = next(s for s in sessions if s.session_id == "other456")

    assert current.is_current is True
    assert other.is_current is False


def test_list_sessions_empty_directory(tmp_path: Path) -> None:
    """Test handling of empty directory."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    sessions = list_sessions(project_dir, None, limit=10)
    assert sessions == []


def test_list_sessions_nonexistent_directory(tmp_path: Path) -> None:
    """Test handling of nonexistent directory."""
    project_dir = tmp_path / "nonexistent"

    sessions = list_sessions(project_dir, None, limit=10)
    assert sessions == []


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
# 6. CLI Command Tests (5 tests)
# ============================================================================


def test_cli_success(tmp_path: Path, monkeypatch) -> None:
    """Test CLI command with successful session listing."""
    # Setup project directory structure
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    # Create test cwd and project dir
    test_cwd = tmp_path / "test"
    test_cwd.mkdir()

    from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.find_project_dir import (
        encode_path_to_project_folder,
    )

    encoded_name = encode_path_to_project_folder(test_cwd)
    project_dir = projects_dir / encoded_name
    project_dir.mkdir()

    # Create session file
    (project_dir / "abc123.jsonl").write_text(
        json.dumps({"type": "user", "message": {"content": "Test session"}}),
        encoding="utf-8",
    )

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create context with FakeGit configured for test_cwd
    git = FakeGit(
        current_branches={test_cwd: "feature-branch"},
        trunk_branches={test_cwd: "main"},
    )
    context = DotAgentContext.for_test(git=git, cwd=test_cwd)

    runner = CliRunner()
    original_cwd = os.getcwd()
    try:
        os.chdir(test_cwd)
        result = runner.invoke(list_sessions_cli, [], obj=context)

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert len(output["sessions"]) == 1
        assert output["sessions"][0]["session_id"] == "abc123"
    finally:
        os.chdir(original_cwd)


def test_cli_project_not_found(tmp_path: Path, monkeypatch) -> None:
    """Test CLI command error when project not found."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    test_dir = tmp_path / "test"
    test_dir.mkdir()

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create context with FakeGit
    git = FakeGit(
        current_branches={test_dir: "main"},
        trunk_branches={test_dir: "main"},
    )
    context = DotAgentContext.for_test(git=git, cwd=test_dir)

    runner = CliRunner()
    original_cwd = os.getcwd()
    try:
        os.chdir(test_dir)
        result = runner.invoke(list_sessions_cli, [], obj=context)

        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["success"] is False
        assert "error" in output
    finally:
        os.chdir(original_cwd)


def test_cli_output_structure(tmp_path: Path, monkeypatch) -> None:
    """Test that CLI output has expected structure."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    test_cwd = tmp_path / "test"
    test_cwd.mkdir()

    from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.find_project_dir import (
        encode_path_to_project_folder,
    )

    encoded_name = encode_path_to_project_folder(test_cwd)
    project_dir = projects_dir / encoded_name
    project_dir.mkdir()

    (project_dir / "session.jsonl").write_text(
        json.dumps({"type": "user", "message": {"content": "Test"}}),
        encoding="utf-8",
    )

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create context with FakeGit
    git = FakeGit(
        current_branches={test_cwd: "feature-branch"},
        trunk_branches={test_cwd: "main"},
    )
    context = DotAgentContext.for_test(git=git, cwd=test_cwd)

    runner = CliRunner()
    original_cwd = os.getcwd()
    try:
        os.chdir(test_cwd)
        result = runner.invoke(list_sessions_cli, [], obj=context)

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
    finally:
        os.chdir(original_cwd)


def test_cli_limit_option(tmp_path: Path, monkeypatch) -> None:
    """Test CLI --limit option."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    test_cwd = tmp_path / "test"
    test_cwd.mkdir()

    from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.find_project_dir import (
        encode_path_to_project_folder,
    )

    encoded_name = encode_path_to_project_folder(test_cwd)
    project_dir = projects_dir / encoded_name
    project_dir.mkdir()

    # Create many sessions
    for i in range(10):
        (project_dir / f"session{i:02d}.jsonl").write_text(
            json.dumps({"type": "user", "message": {"content": f"Session {i}"}}),
            encoding="utf-8",
        )
        time.sleep(0.001)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create context with FakeGit
    git = FakeGit(
        current_branches={test_cwd: "feature-branch"},
        trunk_branches={test_cwd: "main"},
    )
    context = DotAgentContext.for_test(git=git, cwd=test_cwd)

    runner = CliRunner()
    original_cwd = os.getcwd()
    try:
        os.chdir(test_cwd)
        result = runner.invoke(list_sessions_cli, ["--limit", "3"], obj=context)

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output["sessions"]) == 3
    finally:
        os.chdir(original_cwd)


def test_cli_marks_current_session(tmp_path: Path, monkeypatch) -> None:
    """Test that CLI marks current session from SESSION_CONTEXT env."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    test_cwd = tmp_path / "test"
    test_cwd.mkdir()

    from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.find_project_dir import (
        encode_path_to_project_folder,
    )

    encoded_name = encode_path_to_project_folder(test_cwd)
    project_dir = projects_dir / encoded_name
    project_dir.mkdir()

    (project_dir / "current-session.jsonl").write_text(
        json.dumps({"type": "user", "message": {"content": "Current"}}),
        encoding="utf-8",
    )
    (project_dir / "other-session.jsonl").write_text(
        json.dumps({"type": "user", "message": {"content": "Other"}}),
        encoding="utf-8",
    )

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create context with FakeGit
    git = FakeGit(
        current_branches={test_cwd: "feature-branch"},
        trunk_branches={test_cwd: "main"},
    )
    context = DotAgentContext.for_test(git=git, cwd=test_cwd)

    runner = CliRunner(env={"SESSION_CONTEXT": "session_id=current-session"})
    original_cwd = os.getcwd()
    try:
        os.chdir(test_cwd)
        result = runner.invoke(list_sessions_cli, [], obj=context)

        assert result.exit_code == 0
        output = json.loads(result.output)

        current = next(s for s in output["sessions"] if s["session_id"] == "current-session")
        other = next(s for s in output["sessions"] if s["session_id"] == "other-session")

        assert current["is_current"] is True
        assert other["is_current"] is False
    finally:
        os.chdir(original_cwd)
