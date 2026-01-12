"""Tests for erk cc session list command."""

import json
import time

from click.testing import CliRunner

from erk.cli.commands.cc.session.list_cmd import list_sessions
from erk_shared.learn.extraction.claude_installation.fake import (
    FakeClaudeInstallation,
    FakeProject,
    FakeSessionData,
)
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def _make_session_jsonl(user_message: str) -> str:
    """Create minimal JSONL content with a user message."""
    entry = {
        "type": "user",
        "message": {"content": user_message},
    }
    return json.dumps(entry)


def test_list_sessions_shows_sessions() -> None:
    """Test that list_sessions shows sessions with correct info."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Create fake session data
        now = time.time()
        session_store = FakeClaudeInstallation.for_test(
            projects={
                env.cwd: FakeProject(
                    sessions={
                        "abc12345-1234-5678-9abc-def012345678": FakeSessionData(
                            content=_make_session_jsonl("Hello, help me with tests"),
                            size_bytes=1024,
                            modified_at=now - 60,  # 1 minute ago
                        ),
                        "def67890-abcd-efgh-ijkl-mnopqrstuvwx": FakeSessionData(
                            content=_make_session_jsonl("Fix the bug in main.py"),
                            size_bytes=2048,
                            modified_at=now - 3600,  # 1 hour ago
                        ),
                    }
                )
            },
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

        result = runner.invoke(list_sessions, [], obj=ctx)

        assert result.exit_code == 0
        # Check session IDs are shown (full UUIDs)
        assert "abc12345-1234-5678-9abc-def012345678" in result.output
        assert "def67890-abcd-efgh-ijkl-mnopqrstuvwx" in result.output
        # Check summaries are shown
        assert "Hello, help me with tests" in result.output
        assert "Fix the bug in main.py" in result.output
        # Check relative times
        assert "1m ago" in result.output
        assert "1h ago" in result.output


def test_list_sessions_respects_limit() -> None:
    """Test that --limit option limits the number of sessions shown."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        # Create 5 sessions
        sessions = {
            f"session-{i}-1234-5678-9abc-def012345": FakeSessionData(
                content=_make_session_jsonl(f"Session {i}"),
                size_bytes=100 * i,
                modified_at=now - (i * 60),
            )
            for i in range(5)
        }
        session_store = FakeClaudeInstallation.for_test(
            projects={env.cwd: FakeProject(sessions=sessions)},
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

        result = runner.invoke(list_sessions, ["--limit", "2"], obj=ctx)

        assert result.exit_code == 0
        # Only 2 sessions should be shown (the 2 most recent)
        assert "Session 0" in result.output
        assert "Session 1" in result.output
        assert "Session 2" not in result.output
        assert "Session 3" not in result.output
        assert "Session 4" not in result.output


def test_list_sessions_no_project() -> None:
    """Test error when no Claude Code project exists."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Empty session store - no projects
        session_store = FakeClaudeInstallation.for_test()

        ctx = build_workspace_test_context(env, claude_installation=session_store)

        result = runner.invoke(list_sessions, [], obj=ctx)

        assert result.exit_code == 1
        assert "No Claude Code sessions found" in result.output


def test_list_sessions_empty_project() -> None:
    """Test message when project exists but has no sessions."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Project exists but has no sessions
        session_store = FakeClaudeInstallation.for_test(
            projects={env.cwd: FakeProject(sessions={})},
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

        result = runner.invoke(list_sessions, [], obj=ctx)

        assert result.exit_code == 0
        assert "No sessions found" in result.output


def test_list_sessions_sorted_by_time() -> None:
    """Test that sessions are sorted by modification time (newest first)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        session_store = FakeClaudeInstallation.for_test(
            projects={
                env.cwd: FakeProject(
                    sessions={
                        "old-session-1234-5678-9abc-def012345": FakeSessionData(
                            content=_make_session_jsonl("Old session"),
                            size_bytes=100,
                            modified_at=now - 3600,  # 1 hour ago
                        ),
                        "new-session-abcd-efgh-ijkl-mnopqrst": FakeSessionData(
                            content=_make_session_jsonl("New session"),
                            size_bytes=200,
                            modified_at=now - 60,  # 1 minute ago
                        ),
                    }
                )
            },
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

        result = runner.invoke(list_sessions, [], obj=ctx)

        assert result.exit_code == 0
        # New session should appear before old session
        new_pos = result.output.find("New session")
        old_pos = result.output.find("Old session")
        assert new_pos < old_pos, "New session should appear before old session"


def test_list_sessions_excludes_agents_by_default() -> None:
    """Test that agent sessions are excluded by default."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        parent_session_id = "parent12-3456-7890-abcd-ef1234567890"
        session_store = FakeClaudeInstallation.for_test(
            projects={
                env.cwd: FakeProject(
                    sessions={
                        parent_session_id: FakeSessionData(
                            content=_make_session_jsonl("Main session"),
                            size_bytes=1024,
                            modified_at=now - 60,
                        ),
                        "agent-abc12345": FakeSessionData(
                            content=_make_session_jsonl("Agent task"),
                            size_bytes=512,
                            modified_at=now - 30,
                            parent_session_id=parent_session_id,
                        ),
                    }
                )
            },
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

        result = runner.invoke(list_sessions, [], obj=ctx)

        assert result.exit_code == 0
        # Main session should be shown
        assert "Main session" in result.output
        # Agent session should NOT be shown
        assert "agent-abc12345" not in result.output
        assert "Agent task" not in result.output


def test_list_sessions_include_agents_flag() -> None:
    """Test that --include-agents flag includes agent sessions with parent column."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        parent_session_id = "parent12-3456-7890-abcd-ef1234567890"
        session_store = FakeClaudeInstallation.for_test(
            projects={
                env.cwd: FakeProject(
                    sessions={
                        parent_session_id: FakeSessionData(
                            content=_make_session_jsonl("Main session"),
                            size_bytes=1024,
                            modified_at=now - 60,
                        ),
                        "agent-abc12345": FakeSessionData(
                            content=_make_session_jsonl("Agent task"),
                            size_bytes=512,
                            modified_at=now - 30,
                            parent_session_id=parent_session_id,
                        ),
                    }
                )
            },
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

        result = runner.invoke(list_sessions, ["--include-agents"], obj=ctx)

        assert result.exit_code == 0
        # Both sessions should be shown
        assert "Main session" in result.output
        assert "agent-abc12345" in result.output
        assert "Agent task" in result.output
        # Parent column header should be shown
        assert "parent" in result.output
        # First 8 chars of parent session ID should be shown for agent
        assert "parent12" in result.output
