"""Integration tests for agent type extraction using real session data patterns.

Based on session 085a5ec2-14e1-4020-8be8-be5275674674.
"""

import json
import time

from click.testing import CliRunner

from erk.cli.commands.cc.session.show_cmd import show_session
from erk_shared.learn.extraction.claude_installation.fake import (
    FakeClaudeInstallation,
    FakeProject,
    FakeSessionData,
)
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.output_helpers import strip_ansi


def _make_session_with_tasks_and_results(
    tasks: list[tuple[str, str, str]],
    include_timestamps: bool = False,
    base_timestamp: float | None = None,
) -> str:
    """Create session content with multiple Task invocations and results.

    Uses deterministic metadata linking:
    - Task tool_use contains: tool_use.id -> subagent_type
    - tool_result contains: tool_use_id + toolUseResult.agentId

    Args:
        tasks: List of (tool_use_id, subagent_type, agent_id) tuples
        include_timestamps: Whether to include timestamps in entries
        base_timestamp: Base timestamp to use (tasks will be offset from this)
    """
    entries: list[dict] = [{"type": "user", "message": {"content": "Run tasks"}}]

    for i, (tool_use_id, subagent_type, agent_id) in enumerate(tasks):
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
                            "description": f"Run {subagent_type}",
                            "prompt": "...",
                        },
                    }
                ],
            },
        }
        if include_timestamps and base_timestamp is not None:
            task_entry["timestamp"] = base_timestamp + (i * 100)
        entries.append(task_entry)

        # tool_result with agentId in toolUseResult
        result_entry: dict = {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": "Completed",
                    }
                ],
            },
            "toolUseResult": {
                "agentId": agent_id,
                "status": "completed",
            },
        }
        if include_timestamps and base_timestamp is not None:
            result_entry["timestamp"] = base_timestamp + (i * 100) + 30  # 30s duration
        entries.append(result_entry)

    return "\n".join(json.dumps(e) for e in entries)


def test_agent_type_extraction_with_real_data_format() -> None:
    """Test agent type extraction using real session data format.

    Uses deterministic matching via tool_use.id <-> toolUseResult.agentId:
    - toolu_01Mzn -> devrun -> agent-a65aee7
    - toolu_01Jr4 -> Explore -> agent-a3ea803
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        parent_session_id = "085a5ec2-14e1-4020-8be8-be5275674674"

        parent_content = _make_session_with_tasks_and_results(
            [
                ("toolu_01Mzn", "devrun", "a65aee7"),
                ("toolu_01Jr4", "Explore", "a3ea803"),
            ]
        )

        session_store = FakeClaudeInstallation.for_test(
            projects={
                env.cwd: FakeProject(
                    sessions={
                        parent_session_id: FakeSessionData(
                            content=parent_content,
                            size_bytes=1024,
                            modified_at=now - 60,
                        ),
                        "agent-a65aee7": FakeSessionData(
                            content='{"type": "user", "message": {"content": "..."}}',
                            size_bytes=512,
                            modified_at=now - 50,
                            parent_session_id=parent_session_id,
                        ),
                        "agent-a3ea803": FakeSessionData(
                            content='{"type": "user", "message": {"content": "..."}}',
                            size_bytes=256,
                            modified_at=now - 40,
                            parent_session_id=parent_session_id,
                        ),
                    }
                )
            }
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

        result = runner.invoke(show_session, [parent_session_id], obj=ctx)

        assert result.exit_code == 0
        assert "Agent Sessions:" in result.output

        # Verify format: type("prompt") - strip ANSI codes for matching
        output = strip_ansi(result.output)
        assert 'devrun("...")' in output
        assert 'Explore("...")' in output


def test_agent_type_no_match_without_tool_result() -> None:
    """Test that agents without tool_result don't get types.

    If a Task tool_use exists but no matching tool_result with agentId,
    the agent type cannot be determined.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        parent_session_id = "test-session-id"

        # Task tool_use without tool_result (agent still running or crashed)
        parent_content = json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_orphan",
                            "name": "Task",
                            "input": {"subagent_type": "devrun"},
                        }
                    ]
                },
            }
        )

        session_store = FakeClaudeInstallation.for_test(
            projects={
                env.cwd: FakeProject(
                    sessions={
                        parent_session_id: FakeSessionData(
                            content=parent_content,
                            size_bytes=100,
                            modified_at=now - 60,
                        ),
                        "agent-orphan": FakeSessionData(
                            content='{"type": "user", "message": {"content": "..."}}',
                            size_bytes=50,
                            modified_at=now - 50,
                            parent_session_id=parent_session_id,
                        ),
                    }
                )
            }
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

        result = runner.invoke(show_session, [parent_session_id], obj=ctx)

        assert result.exit_code == 0
        # Agent should appear but without type (no tool_result to link)
        assert "agent-orphan" in result.output
        # devrun should NOT appear since no tool_result links to this agent
        assert "devrun" not in result.output


def test_agent_duration_with_timestamps() -> None:
    """Test that agent duration is displayed when timestamps are present."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        now = time.time()
        parent_session_id = "test-session-with-duration"

        # Include timestamps - each task gets 30s duration
        parent_content = _make_session_with_tasks_and_results(
            [
                ("toolu_01Mzn", "devrun", "a65aee7"),
                ("toolu_01Jr4", "Explore", "a3ea803"),
            ],
            include_timestamps=True,
            base_timestamp=now - 200,
        )

        session_store = FakeClaudeInstallation.for_test(
            projects={
                env.cwd: FakeProject(
                    sessions={
                        parent_session_id: FakeSessionData(
                            content=parent_content,
                            size_bytes=1024,
                            modified_at=now - 60,
                        ),
                        "agent-a65aee7": FakeSessionData(
                            content='{"type": "user", "message": {"content": "..."}}',
                            size_bytes=512,
                            modified_at=now - 50,
                            parent_session_id=parent_session_id,
                        ),
                        "agent-a3ea803": FakeSessionData(
                            content='{"type": "user", "message": {"content": "..."}}',
                            size_bytes=256,
                            modified_at=now - 40,
                            parent_session_id=parent_session_id,
                        ),
                    }
                )
            }
        )

        ctx = build_workspace_test_context(env, claude_installation=session_store)

        result = runner.invoke(show_session, [parent_session_id], obj=ctx)

        assert result.exit_code == 0
        output = strip_ansi(result.output)
        # Both agents should show 30s duration
        assert output.count("30s") == 2
