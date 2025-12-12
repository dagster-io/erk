"""Layer 3 tests: Pure message parsing tests (no I/O, no mocking)."""

from erk_kits.data.kits.command.scripts.command.message_parsing import (
    build_result_status_string,
    extract_text_from_assistant_message,
    extract_tool_results_from_user_message,
    extract_tool_uses_from_assistant_message,
)


class TestExtractTextFromAssistantMessage:
    """Tests for extract_text_from_assistant_message function."""

    def test_single_text_item(self) -> None:
        """Test extracting single text item from message."""
        msg = {"message": {"content": [{"type": "text", "text": "Hello"}]}}
        result = extract_text_from_assistant_message(msg)
        assert result == ["Hello"]

    def test_multiple_text_items(self) -> None:
        """Test extracting multiple text items from message."""
        msg = {
            "message": {
                "content": [
                    {"type": "text", "text": "Hello"},
                    {"type": "text", "text": "World"},
                ]
            }
        }
        result = extract_text_from_assistant_message(msg)
        assert result == ["Hello", "World"]

    def test_empty_message(self) -> None:
        """Test extracting from empty message dict."""
        result = extract_text_from_assistant_message({})
        assert result == []

    def test_no_text_items(self) -> None:
        """Test message with no text items (only tool use)."""
        msg = {
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Bash"},
                ]
            }
        }
        result = extract_text_from_assistant_message(msg)
        assert result == []

    def test_missing_text_field(self) -> None:
        """Test text item with missing text field."""
        msg = {"message": {"content": [{"type": "text"}]}}
        result = extract_text_from_assistant_message(msg)
        assert result == [""]  # Should default to empty string

    def test_empty_text_field(self) -> None:
        """Test text item with empty string."""
        msg = {"message": {"content": [{"type": "text", "text": ""}]}}
        result = extract_text_from_assistant_message(msg)
        assert result == [""]

    def test_mixed_content_types(self) -> None:
        """Test message with mixed text and tool_use items."""
        msg = {
            "message": {
                "content": [
                    {"type": "text", "text": "First"},
                    {"type": "tool_use", "name": "Bash"},
                    {"type": "text", "text": "Second"},
                ]
            }
        }
        result = extract_text_from_assistant_message(msg)
        assert result == ["First", "Second"]

    def test_missing_message_key(self) -> None:
        """Test dict without 'message' key."""
        msg = {"other_key": "value"}
        result = extract_text_from_assistant_message(msg)
        assert result == []

    def test_missing_content_key(self) -> None:
        """Test message without 'content' key."""
        msg = {"message": {}}
        result = extract_text_from_assistant_message(msg)
        assert result == []


class TestExtractToolUsesFromAssistantMessage:
    """Tests for extract_tool_uses_from_assistant_message function."""

    def test_single_tool_use(self) -> None:
        """Test extracting single tool use item."""
        msg = {
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "ls"},
                    }
                ]
            }
        }
        result = extract_tool_uses_from_assistant_message(msg)
        assert len(result) == 1
        assert result[0].name == "Bash"
        assert result[0].input_params == {"command": "ls"}

    def test_multiple_tool_uses(self) -> None:
        """Test extracting multiple tool uses."""
        msg = {
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "ls"},
                    },
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "input": {"file_path": "/path/to/file"},
                    },
                ]
            }
        }
        result = extract_tool_uses_from_assistant_message(msg)
        assert len(result) == 2
        assert result[0].name == "Bash"
        assert result[1].name == "Read"

    def test_missing_name_defaults_to_unknown(self) -> None:
        """Test tool use with missing name field."""
        msg = {
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "input": {"param": "value"},
                    }
                ]
            }
        }
        result = extract_tool_uses_from_assistant_message(msg)
        assert len(result) == 1
        assert result[0].name == "unknown"

    def test_empty_input(self) -> None:
        """Test tool use with empty input dict."""
        msg = {
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Task",
                        "input": {},
                    }
                ]
            }
        }
        result = extract_tool_uses_from_assistant_message(msg)
        assert len(result) == 1
        assert result[0].input_params == {}

    def test_missing_input(self) -> None:
        """Test tool use with missing input field."""
        msg = {
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Task",
                    }
                ]
            }
        }
        result = extract_tool_uses_from_assistant_message(msg)
        assert len(result) == 1
        assert result[0].input_params == {}

    def test_empty_message(self) -> None:
        """Test extracting from empty message dict."""
        result = extract_tool_uses_from_assistant_message({})
        assert result == []

    def test_no_tool_use_items(self) -> None:
        """Test message with no tool use items (only text)."""
        msg = {
            "message": {
                "content": [
                    {"type": "text", "text": "Just text"},
                ]
            }
        }
        result = extract_tool_uses_from_assistant_message(msg)
        assert result == []

    def test_mixed_content_types(self) -> None:
        """Test message with mixed text and tool_use items."""
        msg = {
            "message": {
                "content": [
                    {"type": "text", "text": "First"},
                    {"type": "tool_use", "name": "Bash", "input": {"cmd": "ls"}},
                    {"type": "text", "text": "Second"},
                    {"type": "tool_use", "name": "Read", "input": {"path": "/foo"}},
                ]
            }
        }
        result = extract_tool_uses_from_assistant_message(msg)
        assert len(result) == 2
        assert result[0].name == "Bash"
        assert result[1].name == "Read"

    def test_complex_input_parameters(self) -> None:
        """Test tool use with complex nested input."""
        msg = {
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "TodoWrite",
                        "input": {
                            "todos": [
                                {"content": "Task 1", "status": "pending"},
                                {"content": "Task 2", "status": "completed"},
                            ]
                        },
                    }
                ]
            }
        }
        result = extract_tool_uses_from_assistant_message(msg)
        assert len(result) == 1
        assert result[0].name == "TodoWrite"
        assert "todos" in result[0].input_params
        assert len(result[0].input_params["todos"]) == 2


class TestExtractToolResultsFromUserMessage:
    """Tests for extract_tool_results_from_user_message function."""

    def test_single_result(self) -> None:
        """Test extracting single tool result."""
        msg = {
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": "Result output",
                        "is_error": False,
                    }
                ]
            }
        }
        result = extract_tool_results_from_user_message(msg)
        assert len(result) == 1
        assert result[0].content == "Result output"
        assert result[0].is_error is False

    def test_multiple_results(self) -> None:
        """Test extracting multiple tool results."""
        msg = {
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": "First result",
                        "is_error": False,
                    },
                    {
                        "type": "tool_result",
                        "content": "Second result",
                        "is_error": False,
                    },
                ]
            }
        }
        result = extract_tool_results_from_user_message(msg)
        assert len(result) == 2
        assert result[0].content == "First result"
        assert result[1].content == "Second result"

    def test_error_result(self) -> None:
        """Test result with error flag set."""
        msg = {
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": "Error message",
                        "is_error": True,
                    }
                ]
            }
        }
        result = extract_tool_results_from_user_message(msg)
        assert len(result) == 1
        assert result[0].is_error is True

    def test_missing_is_error_defaults_to_false(self) -> None:
        """Test result with missing is_error field."""
        msg = {
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": "Result",
                    }
                ]
            }
        }
        result = extract_tool_results_from_user_message(msg)
        assert len(result) == 1
        assert result[0].is_error is False

    def test_skips_none_content(self) -> None:
        """Test that results with None content are skipped."""
        msg = {
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": None,
                        "is_error": False,
                    },
                    {
                        "type": "tool_result",
                        "content": "Valid",
                        "is_error": False,
                    },
                ]
            }
        }
        result = extract_tool_results_from_user_message(msg)
        assert len(result) == 1
        assert result[0].content == "Valid"

    def test_skips_missing_content(self) -> None:
        """Test that results with missing content field are skipped."""
        msg = {
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "is_error": False,
                    },
                    {
                        "type": "tool_result",
                        "content": "Valid",
                        "is_error": False,
                    },
                ]
            }
        }
        result = extract_tool_results_from_user_message(msg)
        assert len(result) == 1
        assert result[0].content == "Valid"

    def test_empty_message(self) -> None:
        """Test extracting from empty message dict."""
        result = extract_tool_results_from_user_message({})
        assert result == []

    def test_no_tool_result_items(self) -> None:
        """Test message with no tool result items."""
        msg = {
            "message": {
                "content": [
                    {"type": "other", "data": "value"},
                ]
            }
        }
        result = extract_tool_results_from_user_message(msg)
        assert result == []

    def test_structured_list_content(self) -> None:
        """Test result with structured list content."""
        msg = {
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": [
                            {"type": "text", "text": "Line 1"},
                            {"type": "text", "text": "Line 2"},
                        ],
                        "is_error": False,
                    }
                ]
            }
        }
        result = extract_tool_results_from_user_message(msg)
        assert len(result) == 1
        assert isinstance(result[0].content, list)
        assert len(result[0].content) == 2

    def test_empty_string_content(self) -> None:
        """Test result with empty string content."""
        msg = {
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": "",
                        "is_error": False,
                    }
                ]
            }
        }
        result = extract_tool_results_from_user_message(msg)
        assert len(result) == 1
        assert result[0].content == ""


class TestBuildResultStatusString:
    """Tests for build_result_status_string function."""

    def test_success_with_cost(self) -> None:
        """Test success status with cost and duration."""
        msg = {
            "is_error": False,
            "total_cost_usd": 0.0123,
            "duration_ms": 5432,
        }
        result = build_result_status_string(msg)
        assert "✅ Success" in result
        assert "$0.0123" in result
        assert "5432ms" in result

    def test_error_status(self) -> None:
        """Test error status."""
        msg = {
            "is_error": True,
            "total_cost_usd": 0.0050,
            "duration_ms": 1000,
        }
        result = build_result_status_string(msg)
        assert "❌ Error" in result
        assert "$0.0050" in result
        assert "1000ms" in result

    def test_missing_cost(self) -> None:
        """Test status with missing cost field."""
        msg = {
            "is_error": False,
            "duration_ms": 1000,
        }
        result = build_result_status_string(msg)
        assert "✅ Success" in result
        assert "N/A" in result
        assert "1000ms" in result

    def test_missing_duration(self) -> None:
        """Test status with missing duration field."""
        msg = {
            "is_error": False,
            "total_cost_usd": 0.0100,
        }
        result = build_result_status_string(msg)
        assert "✅ Success" in result
        assert "$0.0100" in result
        assert "0ms" in result

    def test_zero_cost(self) -> None:
        """Test status with zero cost."""
        msg = {
            "is_error": False,
            "total_cost_usd": 0.0000,
            "duration_ms": 500,
        }
        result = build_result_status_string(msg)
        assert "$0.0000" in result

    def test_missing_is_error_defaults_to_false(self) -> None:
        """Test status with missing is_error field."""
        msg = {
            "total_cost_usd": 0.0100,
            "duration_ms": 1000,
        }
        result = build_result_status_string(msg)
        assert "✅ Success" in result

    def test_string_format(self) -> None:
        """Test that string has correct format with newlines."""
        msg = {
            "is_error": False,
            "total_cost_usd": 0.0100,
            "duration_ms": 1000,
        }
        result = build_result_status_string(msg)
        assert result.startswith("\n\n")
        assert result.endswith("\n")

    def test_high_cost_formatting(self) -> None:
        """Test formatting with high cost value."""
        msg = {
            "is_error": False,
            "total_cost_usd": 123.4567,
            "duration_ms": 10000,
        }
        result = build_result_status_string(msg)
        assert "$123.4567" in result

    def test_long_duration(self) -> None:
        """Test formatting with long duration."""
        msg = {
            "is_error": False,
            "total_cost_usd": 0.0100,
            "duration_ms": 999999,
        }
        result = build_result_status_string(msg)
        assert "999999ms" in result
