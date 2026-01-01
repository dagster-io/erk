"""Tests for session schema parsing utilities."""

from erk_shared.extraction.session_schema import (
    extract_agent_id_from_tool_result,
    extract_task_tool_use_id,
    extract_tool_use_id_from_content,
)


class TestExtractToolUseIdFromContent:
    """Tests for extract_tool_use_id_from_content function."""

    def test_extracts_tool_use_id_from_tool_result(self) -> None:
        """Extracts tool_use_id from tool_result block."""
        content = [{"type": "tool_result", "tool_use_id": "toolu_abc123"}]

        result = extract_tool_use_id_from_content(content)

        assert result == "toolu_abc123"

    def test_returns_none_for_empty_content(self) -> None:
        """Returns None when content is empty."""
        result = extract_tool_use_id_from_content([])

        assert result is None

    def test_returns_none_for_non_tool_result(self) -> None:
        """Returns None when no tool_result block exists."""
        content = [{"type": "text", "text": "some text"}]

        result = extract_tool_use_id_from_content(content)

        assert result is None

    def test_skips_non_dict_blocks(self) -> None:
        """Skips non-dict blocks gracefully."""
        content = ["string", 123, {"type": "tool_result", "tool_use_id": "toolu_xyz"}]

        result = extract_tool_use_id_from_content(content)

        assert result == "toolu_xyz"

    def test_returns_first_tool_use_id(self) -> None:
        """Returns first tool_use_id when multiple tool_result blocks exist."""
        content = [
            {"type": "tool_result", "tool_use_id": "toolu_first"},
            {"type": "tool_result", "tool_use_id": "toolu_second"},
        ]

        result = extract_tool_use_id_from_content(content)

        assert result == "toolu_first"


class TestExtractTaskToolUseId:
    """Tests for extract_task_tool_use_id function."""

    def test_extracts_id_from_plan_task(self) -> None:
        """Extracts tool_use_id from Task with subagent_type='Plan'."""
        entry = {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_plan_123",
                        "name": "Task",
                        "input": {"subagent_type": "Plan", "prompt": "Plan something"},
                    }
                ]
            },
        }

        result = extract_task_tool_use_id(entry, subagent_type="Plan")

        assert result == "toolu_plan_123"

    def test_returns_none_for_non_matching_subagent_type(self) -> None:
        """Returns None for Task with different subagent_type."""
        entry = {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_devrun_123",
                        "name": "Task",
                        "input": {"subagent_type": "devrun", "prompt": "Run tests"},
                    }
                ]
            },
        }

        result = extract_task_tool_use_id(entry, subagent_type="Plan")

        assert result is None

    def test_extracts_devrun_task(self) -> None:
        """Extracts tool_use_id when matching devrun subagent_type."""
        entry = {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_devrun_123",
                        "name": "Task",
                        "input": {"subagent_type": "devrun", "prompt": "Run tests"},
                    }
                ]
            },
        }

        result = extract_task_tool_use_id(entry, subagent_type="devrun")

        assert result == "toolu_devrun_123"

    def test_returns_none_for_non_task_tool(self) -> None:
        """Returns None for non-Task tool_use."""
        entry = {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_read_123",
                        "name": "Read",
                        "input": {"file_path": "/some/file"},
                    }
                ]
            },
        }

        result = extract_task_tool_use_id(entry, subagent_type="Plan")

        assert result is None

    def test_returns_none_for_empty_content(self) -> None:
        """Returns None when message content is empty."""
        entry = {"type": "assistant", "message": {"content": []}}

        result = extract_task_tool_use_id(entry, subagent_type="Plan")

        assert result is None

    def test_returns_none_for_missing_message(self) -> None:
        """Returns None when message is missing."""
        entry = {"type": "assistant"}

        result = extract_task_tool_use_id(entry, subagent_type="Plan")

        assert result is None


class TestExtractAgentIdFromToolResult:
    """Tests for extract_agent_id_from_tool_result function."""

    def test_extracts_agent_id_and_tool_use_id(self) -> None:
        """Extracts (tool_use_id, agent_id) tuple from entry."""
        entry = {
            "type": "user",
            "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_123"}]},
            "toolUseResult": {"agentId": "abc789", "status": "completed"},
        }

        result = extract_agent_id_from_tool_result(entry)

        assert result == ("toolu_123", "abc789")

    def test_returns_none_for_missing_tool_use_result(self) -> None:
        """Returns None when toolUseResult is missing."""
        entry = {
            "type": "user",
            "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_123"}]},
        }

        result = extract_agent_id_from_tool_result(entry)

        assert result is None

    def test_returns_none_for_missing_agent_id(self) -> None:
        """Returns None when agentId is missing from toolUseResult."""
        entry = {
            "type": "user",
            "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_123"}]},
            "toolUseResult": {"status": "completed"},
        }

        result = extract_agent_id_from_tool_result(entry)

        assert result is None

    def test_returns_none_for_missing_tool_use_id(self) -> None:
        """Returns None when tool_use_id not in content."""
        entry = {
            "type": "user",
            "message": {"content": [{"type": "text", "text": "some text"}]},
            "toolUseResult": {"agentId": "abc789", "status": "completed"},
        }

        result = extract_agent_id_from_tool_result(entry)

        assert result is None

    def test_returns_none_for_empty_content(self) -> None:
        """Returns None when content is empty."""
        entry = {
            "type": "user",
            "message": {"content": []},
            "toolUseResult": {"agentId": "abc789", "status": "completed"},
        }

        result = extract_agent_id_from_tool_result(entry)

        assert result is None
