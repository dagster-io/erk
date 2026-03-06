"""Agent log discovery tests for session log preprocessing."""

import json
from pathlib import Path

from erk.cli.commands.exec.scripts.preprocess_session import (
    discover_agent_logs,
    discover_planning_agent_logs,
)

# ============================================================================
# Agent Log Discovery Tests
# ============================================================================


def test_discover_agent_logs_returns_sorted(tmp_path: Path) -> None:
    """Test that agent logs are returned in sorted order."""
    session_log = tmp_path / "session-123.jsonl"
    session_log.write_text("{}", encoding="utf-8")
    session_id = "session-123"

    agent_z = tmp_path / "agent-zzz.jsonl"
    agent_a = tmp_path / "agent-aaa.jsonl"
    agent_z.write_text(
        json.dumps({"sessionId": session_id, "type": "user", "message": {"content": "z"}}),
        encoding="utf-8",
    )
    agent_a.write_text(
        json.dumps({"sessionId": session_id, "type": "user", "message": {"content": "a"}}),
        encoding="utf-8",
    )

    agents = discover_agent_logs(session_log, session_id)
    assert agents[0].name == "agent-aaa.jsonl"
    assert agents[1].name == "agent-zzz.jsonl"


def test_discover_agent_logs_ignores_other_files(tmp_path: Path) -> None:
    """Test that non-agent files are ignored."""
    session_log = tmp_path / "session-123.jsonl"
    session_log.write_text("{}", encoding="utf-8")
    session_id = "session-123"

    agent = tmp_path / "agent-abc.jsonl"
    other = tmp_path / "other-file.jsonl"
    agent.write_text(
        json.dumps({"sessionId": session_id, "type": "user", "message": {"content": "test"}}),
        encoding="utf-8",
    )
    other.write_text("{}", encoding="utf-8")

    agents = discover_agent_logs(session_log, session_id)
    assert len(agents) == 1
    assert agents[0] == agent


def test_discover_agent_logs_empty_directory(tmp_path: Path) -> None:
    """Test handling of directory with no agent logs."""
    session_log = tmp_path / "session-123.jsonl"
    session_log.write_text("{}", encoding="utf-8")

    agents = discover_agent_logs(session_log, "session-123")
    assert agents == []


def test_discover_agent_logs_filters_by_session_id(tmp_path: Path) -> None:
    """Test that agent logs are filtered by session ID."""
    session_log = tmp_path / "session-123.jsonl"
    session_log.write_text("{}", encoding="utf-8")

    # Agent belonging to session-123
    agent_match = tmp_path / "agent-abc.jsonl"
    agent_match.write_text(
        json.dumps({"sessionId": "session-123", "type": "user", "message": {"content": "test"}}),
        encoding="utf-8",
    )

    # Agent belonging to different session
    agent_no_match = tmp_path / "agent-def.jsonl"
    agent_no_match.write_text(
        json.dumps({"sessionId": "session-456", "type": "user", "message": {"content": "test"}}),
        encoding="utf-8",
    )

    agents = discover_agent_logs(session_log, "session-123")
    assert len(agents) == 1
    assert agent_match in agents
    assert agent_no_match not in agents


def test_discover_agent_logs_filters_multiple_agents(tmp_path: Path) -> None:
    """Test filtering when multiple agent logs match session ID."""
    session_log = tmp_path / "session-xyz.jsonl"
    session_log.write_text("{}", encoding="utf-8")

    # Two agents belonging to session-xyz
    agent1 = tmp_path / "agent-aaa.jsonl"
    agent1.write_text(
        json.dumps({"sessionId": "session-xyz", "type": "user", "message": {"content": "test"}}),
        encoding="utf-8",
    )
    agent2 = tmp_path / "agent-bbb.jsonl"
    agent2.write_text(
        json.dumps({"sessionId": "session-xyz", "type": "user", "message": {"content": "test"}}),
        encoding="utf-8",
    )

    # Agent belonging to different session
    agent_other = tmp_path / "agent-ccc.jsonl"
    agent_other.write_text(
        json.dumps({"sessionId": "other-session", "type": "user", "message": {"content": "test"}}),
        encoding="utf-8",
    )

    agents = discover_agent_logs(session_log, "session-xyz")
    assert len(agents) == 2
    assert agent1 in agents
    assert agent2 in agents
    assert agent_other not in agents


def test_discover_agent_logs_skips_empty_first_line(tmp_path: Path) -> None:
    """Test that agent logs with empty first line are skipped."""
    session_log = tmp_path / "session-123.jsonl"
    session_log.write_text("{}", encoding="utf-8")

    # Agent with empty first line should be skipped
    agent_empty = tmp_path / "agent-empty.jsonl"
    agent_empty.write_text("\n", encoding="utf-8")

    # Agent with valid content should be returned
    agent_valid = tmp_path / "agent-valid.jsonl"
    agent_valid.write_text(
        json.dumps({"sessionId": "session-123", "type": "user", "message": {"content": "test"}}),
        encoding="utf-8",
    )

    agents = discover_agent_logs(session_log, "session-123")
    assert len(agents) == 1
    assert agent_valid in agents


def test_discover_agent_logs_returns_empty_when_no_match(tmp_path: Path) -> None:
    """Test that empty list is returned when no agents match session ID."""
    session_log = tmp_path / "session-target.jsonl"
    session_log.write_text("{}", encoding="utf-8")

    # Agent belonging to different session
    agent = tmp_path / "agent-abc.jsonl"
    agent.write_text(
        json.dumps({"sessionId": "other-session", "type": "user", "message": {"content": "test"}}),
        encoding="utf-8",
    )

    agents = discover_agent_logs(session_log, "session-target")
    assert agents == []


# ============================================================================
# Planning Agent Discovery Tests
# ============================================================================


def test_discover_planning_agent_logs_finds_plan_subagents(tmp_path: Path) -> None:
    """Test that Plan subagents are correctly identified."""
    session_log = tmp_path / "session-123.jsonl"

    # Create session log with Plan Task tool invocation
    session_entries = [
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Task",
                            "input": {"subagent_type": "Plan", "prompt": "Create plan"},
                        }
                    ],
                    "timestamp": 1000.0,
                },
            }
        )
    ]
    session_log.write_text("\n".join(session_entries), encoding="utf-8")

    # Create matching agent log
    agent1 = tmp_path / "agent-abc.jsonl"
    agent1_entry = json.dumps(
        {
            "sessionId": "session-123",
            "message": {"timestamp": 1000.5},  # Within 1 second of Task
        }
    )
    agent1.write_text(agent1_entry, encoding="utf-8")

    # Create non-matching agent log
    agent2 = tmp_path / "agent-def.jsonl"
    agent2_entry = json.dumps(
        {
            "sessionId": "other-session",
            "message": {"timestamp": 1000.5},
        }
    )
    agent2.write_text(agent2_entry, encoding="utf-8")

    agents = discover_planning_agent_logs(session_log, "session-123")
    assert len(agents) == 1
    assert agent1 in agents
    assert agent2 not in agents


def test_discover_planning_agent_logs_filters_non_plan(tmp_path: Path) -> None:
    """Test that Explore/devrun subagents are filtered out."""
    session_log = tmp_path / "session-123.jsonl"

    # Create session with mixed subagent types
    session_entries = [
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Task",
                            "input": {"subagent_type": "Plan", "prompt": "Create plan"},
                        }
                    ],
                    "timestamp": 1000.0,
                },
            }
        ),
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Task",
                            "input": {"subagent_type": "Explore", "prompt": "Explore code"},
                        }
                    ],
                    "timestamp": 2000.0,
                },
            }
        ),
    ]
    session_log.write_text("\n".join(session_entries), encoding="utf-8")

    # Create agent logs matching both
    agent_plan = tmp_path / "agent-plan.jsonl"
    agent_plan.write_text(
        json.dumps(
            {
                "sessionId": "session-123",
                "message": {"timestamp": 1000.5},
            }
        ),
        encoding="utf-8",
    )

    agent_explore = tmp_path / "agent-explore.jsonl"
    agent_explore.write_text(
        json.dumps(
            {
                "sessionId": "session-123",
                "message": {"timestamp": 2000.5},
            }
        ),
        encoding="utf-8",
    )

    agents = discover_planning_agent_logs(session_log, "session-123")

    # Only Plan agent should be returned
    assert len(agents) == 1
    assert agent_plan in agents
    assert agent_explore not in agents


def test_discover_planning_agent_logs_empty_when_none(tmp_path: Path) -> None:
    """Test that empty list returned when no Plan subagents."""
    session_log = tmp_path / "session-123.jsonl"

    # Create session with no Task invocations
    session_entries = [
        json.dumps({"type": "user", "message": {"content": "Hello"}}),
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi"}]}}),
    ]
    session_log.write_text("\n".join(session_entries), encoding="utf-8")

    # Create some agent logs (should not be returned)
    agent = tmp_path / "agent-abc.jsonl"
    agent.write_text(
        json.dumps(
            {
                "sessionId": "session-123",
                "message": {"timestamp": 1000.0},
            }
        ),
        encoding="utf-8",
    )

    agents = discover_planning_agent_logs(session_log, "session-123")
    assert agents == []


def test_discover_planning_agent_logs_matches_agent_ids(tmp_path: Path) -> None:
    """Test that agent IDs are correctly extracted and matched."""
    session_log = tmp_path / "session-123.jsonl"

    # Create session with Plan Tasks
    session_entries = [
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Task",
                            "input": {"subagent_type": "Plan", "prompt": "First plan"},
                        }
                    ],
                    "timestamp": 1000.0,
                },
            }
        ),
    ]
    session_log.write_text("\n".join(session_entries), encoding="utf-8")

    # Create agent logs with different sessionIds and timestamps
    # This one matches: correct sessionId and within 1 second
    agent_match = tmp_path / "agent-match.jsonl"
    agent_match.write_text(
        json.dumps(
            {
                "sessionId": "session-123",
                "message": {"timestamp": 1000.8},  # Within 1 second
            }
        ),
        encoding="utf-8",
    )

    # This one doesn't match: wrong sessionId
    agent_wrong_session = tmp_path / "agent-wrong.jsonl"
    agent_wrong_session.write_text(
        json.dumps(
            {
                "sessionId": "other-session",
                "message": {"timestamp": 1000.5},
            }
        ),
        encoding="utf-8",
    )

    # This one doesn't match: timestamp too far
    agent_wrong_time = tmp_path / "agent-late.jsonl"
    agent_wrong_time.write_text(
        json.dumps(
            {
                "sessionId": "session-123",
                "message": {"timestamp": 1005.0},  # More than 1 second away
            }
        ),
        encoding="utf-8",
    )

    agents = discover_planning_agent_logs(session_log, "session-123")

    # Only the matching agent should be returned
    assert len(agents) == 1
    assert agent_match in agents
