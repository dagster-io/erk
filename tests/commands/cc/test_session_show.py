"""Tests for erk cc session show command."""

import json
import time

from click.testing import CliRunner

from erk.cli.commands.cc.session.show_cmd import (
    AgentInfo,
    extract_agent_info,
    format_duration,
    show_session,
)
from erk_shared.extraction.claude_code_session_store import FakeClaudeCodeSessionStore
from erk_shared.extraction.claude_code_session_store.fake import (
    FakeProject,
    FakeSessionData,
)
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def _make_session_with_task_and_result(
    task_timestamp: float,
    result_timestamp: float,
    agent_type: str = "devrun",
    prompt: str = "Run the test suite",
) -> str:
    """Create session JSONL with a Task tool_use and tool_result with timestamps."""
    tool_use_id = "toolu_abc123"

    entries = [
        {
            "type": "user",
            "message": {"content": [{"type": "text", "text": "Help me test"}]},
        },
        {
            "type": "assistant",
            "timestamp": task_timestamp,
            "message": {
                "content": [
                    {"type": "text", "text": "I'll run the tests for you."},
                    {
                        "type": "tool_use",
                        "name": "Task",
                        "id": tool_use_id,
                        "input": {
                            "subagent_type": agent_type,
                            "prompt": prompt,
                            "description": "Run tests",
                        },
                    },
                ]
            },
        },
        {
            "type": "tool_result",
            "timestamp": result_timestamp,
            "message": {
                "tool_use_id": tool_use_id,
                "content": [{"type": "text", "text": "Tests passed"}],
                "is_error": False,
            },
        },
    ]
    return "\n".join(json.dumps(e) for e in entries)


def test_format_duration_seconds() -> None:
    """Test format_duration for values under 60 seconds."""
    assert format_duration(0) == "0s"
    assert format_duration(30) == "30s"
    assert format_duration(59) == "59s"


def test_format_duration_minutes() -> None:
    """Test format_duration for values under 1 hour."""
    assert format_duration(60) == "1m 0s"
    assert format_duration(90) == "1m 30s"
    assert format_duration(3599) == "59m 59s"


def test_format_duration_hours() -> None:
    """Test format_duration for values 1 hour or more."""
    assert format_duration(3600) == "1h 0m"
    assert format_duration(3660) == "1h 1m"
    assert format_duration(7200) == "2h 0m"


def test_extract_agent_info_with_timestamps() -> None:
    """Test extract_agent_info computes duration from timestamps."""
    content = _make_session_with_task_and_result(
        task_timestamp=1000.0,
        result_timestamp=1042.0,
        agent_type="devrun",
        prompt="Run pytest",
    )

    agents = extract_agent_info(content)

    assert len(agents) == 1
    assert agents[0].agent_type == "devrun"
    assert agents[0].prompt == "Run pytest"
    assert agents[0].duration_secs == 42.0


def test_extract_agent_info_multiple_tasks() -> None:
    """Test extract_agent_info handles multiple Task invocations."""
    entries = [
        {
            "type": "assistant",
            "timestamp": 1000.0,
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Task",
                        "id": "toolu_1",
                        "input": {"subagent_type": "devrun", "prompt": "First task"},
                    }
                ]
            },
        },
        {
            "type": "tool_result",
            "timestamp": 1010.0,
            "message": {"tool_use_id": "toolu_1", "content": []},
        },
        {
            "type": "assistant",
            "timestamp": 1020.0,
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Task",
                        "id": "toolu_2",
                        "input": {"subagent_type": "Explore", "prompt": "Second task"},
                    }
                ]
            },
        },
        {
            "type": "tool_result",
            "timestamp": 1050.0,
            "message": {"tool_use_id": "toolu_2", "content": []},
        },
    ]
    content = "\n".join(json.dumps(e) for e in entries)

    agents = extract_agent_info(content)

    assert len(agents) == 2
    assert agents[0].agent_type == "devrun"
    assert agents[0].duration_secs == 10.0
    assert agents[1].agent_type == "Explore"
    assert agents[1].duration_secs == 30.0


def test_extract_agent_info_no_tasks() -> None:
    """Test extract_agent_info returns empty list when no Task tools used."""
    content = json.dumps(
        {"type": "user", "message": {"content": [{"type": "text", "text": "Hello"}]}}
    )

    agents = extract_agent_info(content)

    assert agents == []


def test_extract_agent_info_truncates_long_prompts() -> None:
    """Test that long prompts are truncated to 50 chars with ellipsis."""
    long_prompt = "A" * 100
    content = _make_session_with_task_and_result(
        task_timestamp=1000.0,
        result_timestamp=1010.0,
        prompt=long_prompt,
    )

    agents = extract_agent_info(content)

    assert len(agents[0].prompt) == 50
    assert agents[0].prompt.endswith("...")


def test_show_session_displays_agent_duration() -> None:
    """Test that show_session displays agent task durations."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        session_id = "abc12345-1234-5678-9abc-def012345678"
        content = _make_session_with_task_and_result(
            task_timestamp=now - 100,
            result_timestamp=now - 58,  # 42 second duration
            agent_type="devrun",
            prompt="Run the test suite",
        )

        session_store = FakeClaudeCodeSessionStore(
            projects={
                env.cwd: FakeProject(
                    sessions={
                        session_id: FakeSessionData(
                            content=content,
                            size_bytes=1024,
                            modified_at=now,
                        )
                    }
                )
            }
        )

        ctx = build_workspace_test_context(env, session_store=session_store)

        result = runner.invoke(show_session, [session_id], obj=ctx)

        assert result.exit_code == 0
        assert "devrun" in result.output
        assert "Run the test suite" in result.output
        assert "42s" in result.output


def test_show_session_no_agents() -> None:
    """Test show_session when session has no agent tasks."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        session_id = "abc12345-1234-5678-9abc-def012345678"
        content = json.dumps(
            {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Hello"}]},
            }
        )

        session_store = FakeClaudeCodeSessionStore(
            projects={
                env.cwd: FakeProject(
                    sessions={
                        session_id: FakeSessionData(
                            content=content,
                            size_bytes=100,
                            modified_at=now,
                        )
                    }
                )
            }
        )

        ctx = build_workspace_test_context(env, session_store=session_store)

        result = runner.invoke(show_session, [session_id], obj=ctx)

        assert result.exit_code == 0
        assert "No agent tasks" in result.output


def test_show_session_not_found() -> None:
    """Test show_session returns error for non-existent session."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        session_store = FakeClaudeCodeSessionStore(
            projects={env.cwd: FakeProject(sessions={})}
        )

        ctx = build_workspace_test_context(env, session_store=session_store)

        result = runner.invoke(show_session, ["nonexistent-session"], obj=ctx)

        assert result.exit_code == 1
        assert "Session not found" in result.output


def test_show_session_no_project() -> None:
    """Test show_session returns error when no project exists."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        session_store = FakeClaudeCodeSessionStore(projects={})

        ctx = build_workspace_test_context(env, session_store=session_store)

        result = runner.invoke(show_session, ["any-session"], obj=ctx)

        assert result.exit_code == 1
        assert "No Claude Code sessions found" in result.output
