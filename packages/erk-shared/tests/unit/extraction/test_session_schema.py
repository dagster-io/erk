"""Tests for session schema parsing utilities."""

import json

import pytest

from erk_shared.extraction.session_schema import (
    TaskInfo,
    extract_agent_id_from_tool_result,
    extract_agent_info_from_jsonl,
    extract_first_user_message_text,
    extract_task_info_from_entry,
    extract_task_tool_use_id,
    extract_text_from_content_blocks,
    extract_tool_use_id_from_content,
    extract_user_prompts_from_jsonl,
    iter_jsonl_entries,
    parse_session_timestamp,
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


class TestExtractTextFromContentBlocks:
    """Tests for extract_text_from_content_blocks function."""

    def test_extracts_text_from_text_block(self) -> None:
        """Extracts text from text type block."""
        content = [{"type": "text", "text": "Hello world"}]

        result = extract_text_from_content_blocks(content)

        assert result == "Hello world"

    def test_extracts_string_directly(self) -> None:
        """Extracts string when content is string."""
        content = ["Direct string content"]

        result = extract_text_from_content_blocks(content)

        assert result == "Direct string content"

    def test_returns_none_for_empty_content(self) -> None:
        """Returns None when content is empty."""
        result = extract_text_from_content_blocks([])

        assert result is None

    def test_returns_none_for_non_text_blocks(self) -> None:
        """Returns None when no text blocks exist."""
        content = [{"type": "tool_use", "name": "Read"}]

        result = extract_text_from_content_blocks(content)

        assert result is None

    def test_skips_empty_text_blocks(self) -> None:
        """Skips text blocks with empty text."""
        content = [
            {"type": "text", "text": ""},
            {"type": "text", "text": "Second text"},
        ]

        result = extract_text_from_content_blocks(content)

        assert result == "Second text"

    def test_returns_first_text(self) -> None:
        """Returns first text when multiple exist."""
        content = [
            {"type": "text", "text": "First"},
            {"type": "text", "text": "Second"},
        ]

        result = extract_text_from_content_blocks(content)

        assert result == "First"


class TestParseSessionTimestamp:
    """Tests for parse_session_timestamp function."""

    def test_returns_none_for_none(self) -> None:
        """Returns None when input is None."""
        result = parse_session_timestamp(None)

        assert result is None

    def test_converts_int_to_float(self) -> None:
        """Converts int timestamp to float."""
        result = parse_session_timestamp(1703246400)

        assert result == 1703246400.0
        assert isinstance(result, float)

    def test_returns_float_as_is(self) -> None:
        """Returns float timestamp as-is."""
        result = parse_session_timestamp(1703246400.5)

        assert result == 1703246400.5

    def test_parses_iso_string_with_z(self) -> None:
        """Parses ISO 8601 string with Z suffix."""
        result = parse_session_timestamp("2024-12-22T13:20:00.000Z")

        assert result is not None
        # Just check it's a reasonable timestamp (after year 2024)
        assert result > 1700000000

    def test_parses_iso_string_with_offset(self) -> None:
        """Parses ISO 8601 string with timezone offset."""
        result = parse_session_timestamp("2024-12-22T13:20:00+00:00")

        assert result is not None
        assert result > 1700000000

    def test_raises_for_invalid_type(self) -> None:
        """Raises TypeError for unexpected type."""
        with pytest.raises(TypeError, match="Unexpected timestamp type"):
            parse_session_timestamp([1, 2, 3])  # type: ignore[arg-type]


class TestIterJsonlEntries:
    """Tests for iter_jsonl_entries function."""

    def test_yields_parsed_entries(self) -> None:
        """Yields parsed JSON entries from JSONL content."""
        content = '{"type": "user"}\n{"type": "assistant"}'

        result = list(iter_jsonl_entries(content))

        assert len(result) == 2
        assert result[0] == {"type": "user"}
        assert result[1] == {"type": "assistant"}

    def test_skips_blank_lines(self) -> None:
        """Skips blank lines."""
        content = '{"type": "user"}\n\n\n{"type": "assistant"}'

        result = list(iter_jsonl_entries(content))

        assert len(result) == 2

    def test_skips_non_json_lines(self) -> None:
        """Skips lines that don't start with {."""
        content = '# comment\n{"type": "user"}\nnot json'

        result = list(iter_jsonl_entries(content))

        assert len(result) == 1
        assert result[0] == {"type": "user"}

    def test_handles_empty_content(self) -> None:
        """Handles empty content gracefully."""
        result = list(iter_jsonl_entries(""))

        assert result == []

    def test_handles_whitespace_lines(self) -> None:
        """Handles lines with only whitespace."""
        content = '   \n{"type": "user"}\n   '

        result = list(iter_jsonl_entries(content))

        assert len(result) == 1


class TestExtractTaskInfoFromEntry:
    """Tests for extract_task_info_from_entry function."""

    def test_extracts_task_info(self) -> None:
        """Extracts TaskInfo from assistant entry with Task tool_use."""
        entry = {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_abc123",
                        "name": "Task",
                        "input": {
                            "subagent_type": "Plan",
                            "prompt": "Plan the implementation",
                        },
                    }
                ]
            },
        }

        result = extract_task_info_from_entry(entry)

        assert result == TaskInfo(
            tool_use_id="toolu_abc123",
            subagent_type="Plan",
            prompt="Plan the implementation",
        )

    def test_returns_none_for_non_assistant(self) -> None:
        """Returns None for non-assistant entry."""
        entry = {
            "type": "user",
            "message": {"content": []},
        }

        result = extract_task_info_from_entry(entry)

        assert result is None

    def test_returns_none_for_non_task_tool(self) -> None:
        """Returns None when no Task tool_use exists."""
        entry = {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_read",
                        "name": "Read",
                        "input": {"file_path": "/some/file"},
                    }
                ]
            },
        }

        result = extract_task_info_from_entry(entry)

        assert result is None

    def test_returns_none_for_missing_id(self) -> None:
        """Returns None when tool_use has no id."""
        entry = {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Task",
                        "input": {"subagent_type": "Plan"},
                    }
                ]
            },
        }

        result = extract_task_info_from_entry(entry)

        assert result is None


class TestExtractFirstUserMessageText:
    """Tests for extract_first_user_message_text function."""

    def test_extracts_string_content(self) -> None:
        """Extracts text from user message with string content."""
        content = json.dumps({"type": "user", "message": {"content": "Hello world"}})

        result = extract_first_user_message_text(content, max_length=None)

        assert result == "Hello world"

    def test_extracts_from_content_blocks(self) -> None:
        """Extracts text from user message with content blocks."""
        entry = {
            "type": "user",
            "message": {
                "content": [
                    {"type": "text", "text": "Hello from blocks"},
                ]
            },
        }
        content = json.dumps(entry)

        result = extract_first_user_message_text(content, max_length=None)

        assert result == "Hello from blocks"

    def test_truncates_with_ellipsis(self) -> None:
        """Truncates long text with ellipsis."""
        entry = {
            "type": "user",
            "message": {"content": "This is a very long message that needs truncation"},
        }
        content = json.dumps(entry)

        result = extract_first_user_message_text(content, max_length=20)

        assert result == "This is a very lo..."
        assert len(result) == 20

    def test_no_truncation_when_none(self) -> None:
        """No truncation when max_length is None."""
        long_text = "x" * 1000
        entry = {"type": "user", "message": {"content": long_text}}
        content = json.dumps(entry)

        result = extract_first_user_message_text(content, max_length=None)

        assert result == long_text

    def test_skips_non_user_entries(self) -> None:
        """Skips non-user entries."""
        entries = [
            {"type": "assistant", "message": {"content": "Assistant message"}},
            {"type": "user", "message": {"content": "User message"}},
        ]
        content = "\n".join(json.dumps(e) for e in entries)

        result = extract_first_user_message_text(content, max_length=None)

        assert result == "User message"

    def test_returns_empty_for_no_user_entries(self) -> None:
        """Returns empty string when no user entries exist."""
        entry = {"type": "assistant", "message": {"content": "Only assistant"}}
        content = json.dumps(entry)

        result = extract_first_user_message_text(content, max_length=None)

        assert result == ""

    def test_skips_empty_text_entries(self) -> None:
        """Skips user entries with empty text."""
        entries = [
            {"type": "user", "message": {"content": "   "}},
            {"type": "user", "message": {"content": "Actual message"}},
        ]
        content = "\n".join(json.dumps(e) for e in entries)

        result = extract_first_user_message_text(content, max_length=None)

        assert result == "Actual message"


class TestExtractAgentInfoFromJsonl:
    """Tests for extract_agent_info_from_jsonl function."""

    def test_extracts_agent_info(self) -> None:
        """Extracts agent info from Task invocation and result."""
        entries = [
            {
                "type": "assistant",
                "timestamp": 1703246400.0,
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_task_123",
                            "name": "Task",
                            "input": {
                                "subagent_type": "Plan",
                                "prompt": "Plan the feature",
                            },
                        }
                    ]
                },
            },
            {
                "type": "user",
                "timestamp": 1703246460.0,
                "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_task_123"}]},
                "toolUseResult": {"agentId": "abc789"},
            },
        ]
        content = "\n".join(json.dumps(e) for e in entries)

        result = extract_agent_info_from_jsonl(content)

        assert "agent-abc789" in result
        agent = result["agent-abc789"]
        assert agent.agent_type == "Plan"
        assert agent.prompt == "Plan the feature"
        assert agent.duration_secs == 60.0

    def test_handles_iso_timestamps(self) -> None:
        """Handles ISO 8601 timestamps correctly."""
        entries = [
            {
                "type": "assistant",
                "timestamp": "2024-12-22T13:20:00.000Z",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_task_123",
                            "name": "Task",
                            "input": {"subagent_type": "devrun", "prompt": "Run tests"},
                        }
                    ]
                },
            },
            {
                "type": "user",
                "timestamp": "2024-12-22T13:21:00.000Z",
                "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_task_123"}]},
                "toolUseResult": {"agentId": "xyz456"},
            },
        ]
        content = "\n".join(json.dumps(e) for e in entries)

        result = extract_agent_info_from_jsonl(content)

        assert "agent-xyz456" in result
        agent = result["agent-xyz456"]
        assert agent.agent_type == "devrun"
        assert agent.duration_secs is not None
        assert abs(agent.duration_secs - 60.0) < 1  # ~60 seconds

    def test_returns_empty_for_no_agents(self) -> None:
        """Returns empty dict when no agents exist."""
        entries = [
            {"type": "user", "message": {"content": "Hello"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi"}]}},
        ]
        content = "\n".join(json.dumps(e) for e in entries)

        result = extract_agent_info_from_jsonl(content)

        assert result == {}

    def test_handles_missing_timestamps(self) -> None:
        """Handles missing timestamps (duration_secs is None)."""
        entries = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_task_123",
                            "name": "Task",
                            "input": {"subagent_type": "Explore", "prompt": "Find files"},
                        }
                    ]
                },
            },
            {
                "type": "user",
                "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_task_123"}]},
                "toolUseResult": {"agentId": "no_time"},
            },
        ]
        content = "\n".join(json.dumps(e) for e in entries)

        result = extract_agent_info_from_jsonl(content)

        assert "agent-no_time" in result
        agent = result["agent-no_time"]
        assert agent.duration_secs is None

    def test_handles_multiple_agents(self) -> None:
        """Handles multiple agent invocations."""
        entries = [
            {
                "type": "assistant",
                "timestamp": 1000.0,
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_1",
                            "name": "Task",
                            "input": {"subagent_type": "Plan", "prompt": "First"},
                        }
                    ]
                },
            },
            {
                "type": "user",
                "timestamp": 1010.0,
                "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_1"}]},
                "toolUseResult": {"agentId": "agent1"},
            },
            {
                "type": "assistant",
                "timestamp": 1020.0,
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_2",
                            "name": "Task",
                            "input": {"subagent_type": "devrun", "prompt": "Second"},
                        }
                    ]
                },
            },
            {
                "type": "user",
                "timestamp": 1030.0,
                "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_2"}]},
                "toolUseResult": {"agentId": "agent2"},
            },
        ]
        content = "\n".join(json.dumps(e) for e in entries)

        result = extract_agent_info_from_jsonl(content)

        assert len(result) == 2
        assert result["agent-agent1"].agent_type == "Plan"
        assert result["agent-agent2"].agent_type == "devrun"


class TestExtractUserPromptsFromJsonl:
    """Tests for extract_user_prompts_from_jsonl function."""

    def test_extracts_prompts_from_string_content(self) -> None:
        """Extracts prompts from user messages with string content."""
        entries = [
            {"type": "user", "message": {"content": "First prompt"}},
            {"type": "assistant", "message": {"content": "Response"}},
            {"type": "user", "message": {"content": "Second prompt"}},
        ]
        content = "\n".join(json.dumps(e) for e in entries)

        result = extract_user_prompts_from_jsonl(content, max_prompts=10, max_prompt_length=100)

        assert result == ["First prompt", "Second prompt"]

    def test_extracts_prompts_from_content_blocks(self) -> None:
        """Extracts prompts from user messages with content blocks."""
        entries = [
            {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Hello from blocks"}]},
            }
        ]
        content = "\n".join(json.dumps(e) for e in entries)

        result = extract_user_prompts_from_jsonl(content, max_prompts=10, max_prompt_length=100)

        assert result == ["Hello from blocks"]

    def test_limits_to_max_prompts(self) -> None:
        """Stops extracting after max_prompts is reached."""
        entries = [{"type": "user", "message": {"content": f"Prompt {i}"}} for i in range(10)]
        content = "\n".join(json.dumps(e) for e in entries)

        result = extract_user_prompts_from_jsonl(content, max_prompts=3, max_prompt_length=100)

        assert len(result) == 3
        assert result == ["Prompt 0", "Prompt 1", "Prompt 2"]

    def test_truncates_long_prompts(self) -> None:
        """Truncates prompts longer than max_prompt_length."""
        long_text = "This is a very long prompt that needs truncation"
        entries = [{"type": "user", "message": {"content": long_text}}]
        content = "\n".join(json.dumps(e) for e in entries)

        result = extract_user_prompts_from_jsonl(content, max_prompts=10, max_prompt_length=20)

        assert len(result) == 1
        assert result[0] == "This is a very lo..."
        assert len(result[0]) == 20

    def test_skips_empty_prompts(self) -> None:
        """Skips user entries with empty or whitespace-only content."""
        entries = [
            {"type": "user", "message": {"content": "   "}},
            {"type": "user", "message": {"content": ""}},
            {"type": "user", "message": {"content": "Valid prompt"}},
        ]
        content = "\n".join(json.dumps(e) for e in entries)

        result = extract_user_prompts_from_jsonl(content, max_prompts=10, max_prompt_length=100)

        assert result == ["Valid prompt"]

    def test_skips_non_user_entries(self) -> None:
        """Only extracts prompts from user entries."""
        entries = [
            {"type": "assistant", "message": {"content": "Assistant message"}},
            {"type": "tool_result", "message": {"content": "Tool result"}},
            {"type": "user", "message": {"content": "User prompt"}},
        ]
        content = "\n".join(json.dumps(e) for e in entries)

        result = extract_user_prompts_from_jsonl(content, max_prompts=10, max_prompt_length=100)

        assert result == ["User prompt"]

    def test_returns_empty_for_no_user_entries(self) -> None:
        """Returns empty list when no user entries exist."""
        entries = [{"type": "assistant", "message": {"content": "Only assistant"}}]
        content = "\n".join(json.dumps(e) for e in entries)

        result = extract_user_prompts_from_jsonl(content, max_prompts=10, max_prompt_length=100)

        assert result == []

    def test_returns_empty_for_empty_content(self) -> None:
        """Returns empty list for empty JSONL content."""
        result = extract_user_prompts_from_jsonl("", max_prompts=10, max_prompt_length=100)

        assert result == []

    def test_handles_content_blocks_without_text(self) -> None:
        """Skips user entries where content blocks have no text."""
        entries = [
            {
                "type": "user",
                "message": {"content": [{"type": "tool_use", "name": "Read"}]},
            },
            {"type": "user", "message": {"content": "Has text"}},
        ]
        content = "\n".join(json.dumps(e) for e in entries)

        result = extract_user_prompts_from_jsonl(content, max_prompts=10, max_prompt_length=100)

        assert result == ["Has text"]
