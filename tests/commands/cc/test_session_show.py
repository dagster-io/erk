"""Tests for erk cc session show command."""

import json
import time

from click.testing import CliRunner

from erk.cli.commands.cc.session.show_cmd import show_session
from erk_shared.extraction.claude_code_session_store import FakeClaudeCodeSessionStore
from erk_shared.extraction.claude_code_session_store.fake import (
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


def test_show_session_displays_metadata() -> None:
    """Test that show_session displays session metadata correctly."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        session_id = "abc12345-1234-5678-9abc-def012345678"
        session_store = FakeClaudeCodeSessionStore(
            projects={
                env.cwd: FakeProject(
                    sessions={
                        session_id: FakeSessionData(
                            content=_make_session_jsonl("Hello, help me with tests"),
                            size_bytes=1024,
                            modified_at=now - 60,
                        ),
                    }
                )
            }
        )

        ctx = build_workspace_test_context(env, session_store=session_store)

        result = runner.invoke(show_session, [session_id], obj=ctx)

        assert result.exit_code == 0
        # Check metadata is displayed
        assert "ID:" in result.output
        assert session_id in result.output
        assert "Size:" in result.output
        assert "1KB" in result.output
        assert "Modified:" in result.output
        assert "Summary:" in result.output
        assert "Hello, help me with tests" in result.output
        assert "Path:" in result.output


def test_show_session_not_found_error() -> None:
    """Test that show_session returns error for non-existent session."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        session_store = FakeClaudeCodeSessionStore(
            projects={
                env.cwd: FakeProject(
                    sessions={
                        "existing-session-id": FakeSessionData(
                            content=_make_session_jsonl("Existing session"),
                            size_bytes=100,
                            modified_at=now,
                        ),
                    }
                )
            }
        )

        ctx = build_workspace_test_context(env, session_store=session_store)

        result = runner.invoke(show_session, ["nonexistent-session-id"], obj=ctx)

        assert result.exit_code == 1
        assert "Session not found" in result.output
        assert "nonexistent-session-id" in result.output


def test_show_session_agent_session_error() -> None:
    """Test that show_session returns helpful error when agent session is passed."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        parent_session_id = "parent12-3456-7890-abcd-ef1234567890"
        agent_session_id = "agent-abc12345"
        session_store = FakeClaudeCodeSessionStore(
            projects={
                env.cwd: FakeProject(
                    sessions={
                        parent_session_id: FakeSessionData(
                            content=_make_session_jsonl("Main session"),
                            size_bytes=1024,
                            modified_at=now - 60,
                        ),
                        agent_session_id: FakeSessionData(
                            content=_make_session_jsonl("Agent task"),
                            size_bytes=512,
                            modified_at=now - 30,
                            parent_session_id=parent_session_id,
                        ),
                    }
                )
            }
        )

        ctx = build_workspace_test_context(env, session_store=session_store)

        result = runner.invoke(show_session, [agent_session_id], obj=ctx)

        assert result.exit_code == 1
        assert "Cannot show agent session directly" in result.output
        assert "Use parent session instead" in result.output
        assert parent_session_id in result.output


def test_show_session_displays_child_agents() -> None:
    """Test that show_session displays child agent sessions in a table."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        parent_session_id = "parent12-3456-7890-abcd-ef1234567890"
        session_store = FakeClaudeCodeSessionStore(
            projects={
                env.cwd: FakeProject(
                    sessions={
                        parent_session_id: FakeSessionData(
                            content=_make_session_jsonl("Main session"),
                            size_bytes=1024,
                            modified_at=now - 60,
                        ),
                        "agent-abc12345": FakeSessionData(
                            content=_make_session_jsonl("First agent task"),
                            size_bytes=512,
                            modified_at=now - 30,
                            parent_session_id=parent_session_id,
                        ),
                        "agent-def67890": FakeSessionData(
                            content=_make_session_jsonl("Second agent task"),
                            size_bytes=256,
                            modified_at=now - 15,
                            parent_session_id=parent_session_id,
                        ),
                    }
                )
            }
        )

        ctx = build_workspace_test_context(env, session_store=session_store)

        result = runner.invoke(show_session, [parent_session_id], obj=ctx)

        assert result.exit_code == 0
        # Check that Agent Sessions section is shown
        assert "Agent Sessions:" in result.output
        # Check that agent sessions are listed
        assert "agent-abc12345" in result.output
        assert "agent-def67890" in result.output
        assert "First agent task" in result.output
        assert "Second agent task" in result.output


def test_show_session_no_child_agents() -> None:
    """Test that show_session shows message when no child agents exist."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        session_id = "abc12345-1234-5678-9abc-def012345678"
        session_store = FakeClaudeCodeSessionStore(
            projects={
                env.cwd: FakeProject(
                    sessions={
                        session_id: FakeSessionData(
                            content=_make_session_jsonl("Session with no agents"),
                            size_bytes=1024,
                            modified_at=now - 60,
                        ),
                    }
                )
            }
        )

        ctx = build_workspace_test_context(env, session_store=session_store)

        result = runner.invoke(show_session, [session_id], obj=ctx)

        assert result.exit_code == 0
        # Check that "No agent sessions" message is shown
        assert "No agent sessions" in result.output


def test_show_session_no_project_error() -> None:
    """Test error when no Claude Code project exists."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Empty session store - no projects
        session_store = FakeClaudeCodeSessionStore(projects={})

        ctx = build_workspace_test_context(env, session_store=session_store)

        result = runner.invoke(show_session, ["any-session-id"], obj=ctx)

        assert result.exit_code == 1
        assert "No Claude Code sessions found" in result.output


def test_show_session_infers_most_recent() -> None:
    """Test that show_session infers the most recent session when no ID provided."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        recent_session_id = "recent12-3456-7890-abcd-ef1234567890"
        old_session_id = "old12345-1234-5678-9abc-def012345678"
        session_store = FakeClaudeCodeSessionStore(
            projects={
                env.cwd: FakeProject(
                    sessions={
                        recent_session_id: FakeSessionData(
                            content=_make_session_jsonl("Most recent session"),
                            size_bytes=1024,
                            modified_at=now - 60,  # 1 minute ago (more recent)
                        ),
                        old_session_id: FakeSessionData(
                            content=_make_session_jsonl("Older session"),
                            size_bytes=2048,
                            modified_at=now - 3600,  # 1 hour ago
                        ),
                    }
                )
            }
        )

        ctx = build_workspace_test_context(env, session_store=session_store)

        # Call without session_id argument
        result = runner.invoke(show_session, [], obj=ctx)

        assert result.exit_code == 0
        # Check that inferred message is shown
        assert "Using most recent session for this worktree" in result.output
        assert recent_session_id in result.output
        # Check that the recent session details are shown
        assert "Most recent session" in result.output


def test_show_session_infer_no_sessions_error() -> None:
    """Test error when inferring session but no sessions exist."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Project exists but has no sessions
        session_store = FakeClaudeCodeSessionStore(
            projects={env.cwd: FakeProject(sessions={})}
        )

        ctx = build_workspace_test_context(env, session_store=session_store)

        result = runner.invoke(show_session, [], obj=ctx)

        assert result.exit_code == 1
        assert "No sessions found" in result.output
