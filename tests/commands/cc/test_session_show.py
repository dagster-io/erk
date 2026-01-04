"""Tests for erk cc session show command."""

import json
import time

from click.testing import CliRunner

from erk.cli.commands.cc.session.show_cmd import show_session
from erk_shared.extraction.claude_installation import (
    FakeClaudeInstallation,
    FakeProject,
    FakeSessionData,
)
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.output_helpers import strip_ansi


def _make_session_jsonl(user_message: str) -> str:
    """Create minimal JSONL content with a user message."""
    entry = {
        "type": "user",
        "message": {"content": user_message},
    }
    return json.dumps(entry)


def _make_session_with_task_and_result(
    user_message: str,
    tool_use_id: str,
    subagent_type: str,
    agent_id: str,
    start_timestamp: float | None = None,
    end_timestamp: float | None = None,
) -> str:
    """Create session content with Task invocation and tool_result with agentId.

    Uses the deterministic metadata linking:
    - Task tool_use contains: tool_use.id -> subagent_type
    - tool_result contains: tool_use_id + toolUseResult.agentId

    Args:
        user_message: Initial user message
        tool_use_id: Unique tool use ID (links tool_use to tool_result)
        subagent_type: Agent type like "devrun", "Explore", etc.
        agent_id: The agent ID (without "agent-" prefix)
        start_timestamp: Optional timestamp for tool_use entry
        end_timestamp: Optional timestamp for tool_result entry
    """
    entries: list[dict] = [
        {"type": "user", "message": {"content": user_message}},
    ]
    # Task tool_use
    task_entry: dict = {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_use_id,
                    "name": "Task",
                    "input": {
                        "subagent_type": subagent_type,
                        "description": "Run tests",
                        "prompt": "Run the test suite",
                    },
                }
            ],
        },
    }
    if start_timestamp is not None:
        task_entry["timestamp"] = start_timestamp
    entries.append(task_entry)

    # tool_result with agentId in toolUseResult
    result_entry: dict = {
        "type": "user",
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": "Task completed",
                }
            ],
        },
        "toolUseResult": {
            "agentId": agent_id,
            "status": "completed",
        },
    }
    if end_timestamp is not None:
        result_entry["timestamp"] = end_timestamp
    entries.append(result_entry)

    return "\n".join(json.dumps(e) for e in entries)


def test_show_session_displays_metadata() -> None:
    """Test that show_session displays session metadata correctly."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        session_id = "abc12345-1234-5678-9abc-def012345678"
        session_store = FakeClaudeInstallation(
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
            },
            plans=None,
            settings=None,
            local_settings=None,
            session_slugs=None,
            session_planning_agents=None,
            plans_dir_path=None,
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

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
        session_store = FakeClaudeInstallation(
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
            },
            plans=None,
            settings=None,
            local_settings=None,
            session_slugs=None,
            session_planning_agents=None,
            plans_dir_path=None,
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

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
        session_store = FakeClaudeInstallation(
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
            },
            plans=None,
            settings=None,
            local_settings=None,
            session_slugs=None,
            session_planning_agents=None,
            plans_dir_path=None,
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

        result = runner.invoke(show_session, [agent_session_id], obj=ctx)

        assert result.exit_code == 1
        assert "Cannot show agent session directly" in result.output
        assert "Use parent session instead" in result.output
        assert parent_session_id in result.output


def test_show_session_displays_child_agents() -> None:
    """Test that show_session displays child agent sessions."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        parent_session_id = "parent12-3456-7890-abcd-ef1234567890"
        session_store = FakeClaudeInstallation(
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
            },
            plans=None,
            settings=None,
            local_settings=None,
            session_slugs=None,
            session_planning_agents=None,
            plans_dir_path=None,
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

        result = runner.invoke(show_session, [parent_session_id], obj=ctx)

        assert result.exit_code == 0
        # Check that Agent Sessions section is shown
        assert "Agent Sessions:" in result.output
        # Check that agent sessions are listed with IDs and sizes
        assert "agent-abc12345" in result.output
        assert "agent-def67890" in result.output
        assert "512B" in result.output
        assert "256B" in result.output


def test_show_session_no_child_agents() -> None:
    """Test that show_session shows message when no child agents exist."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        session_id = "abc12345-1234-5678-9abc-def012345678"
        session_store = FakeClaudeInstallation(
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
            },
            plans=None,
            settings=None,
            local_settings=None,
            session_slugs=None,
            session_planning_agents=None,
            plans_dir_path=None,
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

        result = runner.invoke(show_session, [session_id], obj=ctx)

        assert result.exit_code == 0
        # Check that "No agent sessions" message is shown
        assert "No agent sessions" in result.output


def test_show_session_no_project_error() -> None:
    """Test error when no Claude Code project exists."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Empty session store - no projects
        session_store = FakeClaudeInstallation(
            projects={},
            plans=None,
            settings=None,
            local_settings=None,
            session_slugs=None,
            session_planning_agents=None,
            plans_dir_path=None,
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

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
        session_store = FakeClaudeInstallation(
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
            },
            plans=None,
            settings=None,
            local_settings=None,
            session_slugs=None,
            session_planning_agents=None,
            plans_dir_path=None,
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

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
        session_store = FakeClaudeInstallation(
            projects={env.cwd: FakeProject(sessions={})},
            plans=None,
            settings=None,
            local_settings=None,
            session_slugs=None,
            session_planning_agents=None,
            plans_dir_path=None,
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

        result = runner.invoke(show_session, [], obj=ctx)

        assert result.exit_code == 1
        assert "No sessions found" in result.output


def test_show_session_displays_agent_type_and_prompt() -> None:
    """Test that show_session displays agent type and prompt from Task."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        parent_session_id = "parent12-3456-7890-abcd-ef1234567890"

        # Parent session with Task invocation and tool_result containing agentId
        parent_content = _make_session_with_task_and_result(
            user_message="Main session",
            tool_use_id="toolu_abc123",
            subagent_type="devrun",
            agent_id="abc12345",
        )

        session_store = FakeClaudeInstallation(
            projects={
                env.cwd: FakeProject(
                    sessions={
                        parent_session_id: FakeSessionData(
                            content=parent_content,
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
            plans=None,
            settings=None,
            local_settings=None,
            session_slugs=None,
            session_planning_agents=None,
            plans_dir_path=None,
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

        result = runner.invoke(show_session, [parent_session_id], obj=ctx)

        assert result.exit_code == 0
        # Check that Agent Sessions section is shown
        assert "Agent Sessions:" in result.output
        # Check format: type("prompt") - strip ANSI codes for matching
        output = strip_ansi(result.output)
        assert 'devrun("Run the test suite")' in output


def test_show_session_handles_string_timestamps() -> None:
    """Test that show_session handles ISO format string timestamps.

    Real session data may have timestamps as ISO strings like "2024-12-22T13:20:00.000Z"
    instead of Unix floats. This test reproduces the TypeError that occurs when
    attempting arithmetic on string timestamps.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        parent_session_id = "parent12-3456-7890-abcd-ef1234567890"

        # Create content with string timestamps (ISO format)
        parent_content = _make_session_with_task_and_result(
            user_message="Main session",
            tool_use_id="toolu_abc123",
            subagent_type="devrun",
            agent_id="abc12345",
            start_timestamp="2024-12-22T13:20:00.000Z",  # type: ignore[arg-type] -- testing with string timestamps instead of floats
            end_timestamp="2024-12-22T13:20:42.000Z",  # type: ignore[arg-type] -- testing with string timestamps instead of floats
        )

        session_store = FakeClaudeInstallation(
            projects={
                env.cwd: FakeProject(
                    sessions={
                        parent_session_id: FakeSessionData(
                            content=parent_content,
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
            plans=None,
            settings=None,
            local_settings=None,
            session_slugs=None,
            session_planning_agents=None,
            plans_dir_path=None,
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

        result = runner.invoke(show_session, [parent_session_id], obj=ctx)

        # Should not crash - gracefully handle string timestamps
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        # Agent should appear with type
        assert 'devrun("Run the test suite")' in output
        # Duration should be shown (42s from the ISO timestamps)
        assert "42s" in output


def test_show_session_displays_agent_duration() -> None:
    """Test that show_session displays agent task duration."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        parent_session_id = "parent12-3456-7890-abcd-ef1234567890"

        # Parent session with Task invocation and tool_result including timestamps
        # Duration: 42 seconds
        start_time = now - 102  # Task started 102 seconds ago
        end_time = now - 60  # Task ended 60 seconds ago (42s duration)
        parent_content = _make_session_with_task_and_result(
            user_message="Main session",
            tool_use_id="toolu_abc123",
            subagent_type="devrun",
            agent_id="abc12345",
            start_timestamp=start_time,
            end_timestamp=end_time,
        )

        session_store = FakeClaudeInstallation(
            projects={
                env.cwd: FakeProject(
                    sessions={
                        parent_session_id: FakeSessionData(
                            content=parent_content,
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
            plans=None,
            settings=None,
            local_settings=None,
            session_slugs=None,
            session_planning_agents=None,
            plans_dir_path=None,
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

        result = runner.invoke(show_session, [parent_session_id], obj=ctx)

        assert result.exit_code == 0
        output = strip_ansi(result.output)
        # Check that duration is displayed (42s)
        assert "42s" in output


def test_show_session_duration_formats_minutes() -> None:
    """Test that duration is formatted correctly for minutes."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        parent_session_id = "parent12-3456-7890-abcd-ef1234567890"

        # Duration: 90 seconds = 1m 30s
        start_time = now - 150
        end_time = now - 60  # 90s duration
        parent_content = _make_session_with_task_and_result(
            user_message="Main session",
            tool_use_id="toolu_abc123",
            subagent_type="devrun",
            agent_id="abc12345",
            start_timestamp=start_time,
            end_timestamp=end_time,
        )

        session_store = FakeClaudeInstallation(
            projects={
                env.cwd: FakeProject(
                    sessions={
                        parent_session_id: FakeSessionData(
                            content=parent_content,
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
            plans=None,
            settings=None,
            local_settings=None,
            session_slugs=None,
            session_planning_agents=None,
            plans_dir_path=None,
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

        result = runner.invoke(show_session, [parent_session_id], obj=ctx)

        assert result.exit_code == 0
        output = strip_ansi(result.output)
        # Check that duration is formatted as minutes
        assert "1m 30s" in output


def test_show_session_no_duration_without_timestamps() -> None:
    """Test that no duration is shown when timestamps are missing."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        parent_session_id = "parent12-3456-7890-abcd-ef1234567890"

        # No timestamps provided
        parent_content = _make_session_with_task_and_result(
            user_message="Main session",
            tool_use_id="toolu_abc123",
            subagent_type="devrun",
            agent_id="abc12345",
        )

        session_store = FakeClaudeInstallation(
            projects={
                env.cwd: FakeProject(
                    sessions={
                        parent_session_id: FakeSessionData(
                            content=parent_content,
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
            plans=None,
            settings=None,
            local_settings=None,
            session_slugs=None,
            session_planning_agents=None,
            plans_dir_path=None,
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

        result = runner.invoke(show_session, [parent_session_id], obj=ctx)

        assert result.exit_code == 0
        output = strip_ansi(result.output)
        # Duration should not appear (no "s" suffix after a number in the agent line)
        # The metadata line should just have time and size, not duration
        lines = output.split("\n")
        agent_metadata_line = None
        for i, line in enumerate(lines):
            if 'devrun("Run the test suite")' in line:
                # Next line should be the metadata line
                if i + 1 < len(lines):
                    agent_metadata_line = lines[i + 1]
                break
        assert agent_metadata_line is not None
        # Should have size (512B) but NOT a duration like "42s"
        assert "512B" in agent_metadata_line
        # The line should end with the size, not a duration
        # Count number of segments separated by double-spaces
        segments = [s for s in agent_metadata_line.strip().split("  ") if s]
        # Should be 2 segments: time and size (no duration)
        assert len(segments) == 2
