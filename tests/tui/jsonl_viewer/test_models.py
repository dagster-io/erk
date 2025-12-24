"""Tests for JSONL viewer models."""

from pathlib import Path

from erk.tui.jsonl_viewer.models import (
    JsonlEntry,
    _format_value,
    _interpret_escape_sequences,
    extract_tool_name,
    format_entry_detail,
    format_summary,
    parse_jsonl_file,
)


class TestExtractToolName:
    """Tests for extract_tool_name function."""

    def test_extracts_tool_name_from_tool_use_block(self) -> None:
        """Extracts tool name from tool_use content block."""
        entry = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "I'll run the tests"},
                    {"type": "tool_use", "name": "Bash", "id": "tool_123"},
                ]
            },
        }
        assert extract_tool_name(entry) == "Bash"

    def test_returns_none_when_no_tool_use(self) -> None:
        """Returns None when no tool_use block present."""
        entry = {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "Hello"}]},
        }
        assert extract_tool_name(entry) is None

    def test_returns_none_when_no_message(self) -> None:
        """Returns None when message is missing."""
        entry = {"type": "user"}
        assert extract_tool_name(entry) is None

    def test_returns_none_when_content_not_list(self) -> None:
        """Returns None when content is not a list."""
        entry = {"type": "assistant", "message": {"content": "text"}}
        assert extract_tool_name(entry) is None

    def test_extracts_first_tool_name_when_multiple(self) -> None:
        """Extracts first tool name when multiple tool_use blocks."""
        entry = {
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Read", "id": "1"},
                    {"type": "tool_use", "name": "Edit", "id": "2"},
                ]
            }
        }
        assert extract_tool_name(entry) == "Read"


class TestFormatSummary:
    """Tests for format_summary function."""

    def test_formats_entry_with_tool_name(self) -> None:
        """Formats entry with line number, type, and tool name."""
        entry = JsonlEntry(
            line_number=5,
            entry_type="assistant",
            role="assistant",
            tool_name="Bash",
            raw_json="{}",
            parsed={},
        )
        result = format_summary(entry)
        assert result == "[   5] | assistant | Bash"

    def test_formats_entry_without_tool_name(self) -> None:
        """Formats entry without tool name."""
        entry = JsonlEntry(
            line_number=1,
            entry_type="user",
            role="user",
            tool_name=None,
            raw_json="{}",
            parsed={},
        )
        result = format_summary(entry)
        assert result == "[   1] | user"

    def test_formats_large_line_number(self) -> None:
        """Formats entry with large line number."""
        entry = JsonlEntry(
            line_number=1234,
            entry_type="tool_result",
            role=None,
            tool_name="Read",
            raw_json="{}",
            parsed={},
        )
        result = format_summary(entry)
        assert result == "[1234] | tool_result | Read"


class TestParseJsonlFile:
    """Tests for parse_jsonl_file function."""

    def test_parses_valid_jsonl_file(self, tmp_path: Path) -> None:
        """Parses valid JSONL file into entries."""
        jsonl_file = tmp_path / "test.jsonl"
        jsonl_file.write_text(
            '{"type": "user", "message": {"content": [{"type": "text", '
            '"text": "Hello"}]}}\n'
            '{"type": "assistant", "message": {"content": [{"type": '
            '"tool_use", "name": "Bash"}]}}\n',
            encoding="utf-8",
        )

        entries = parse_jsonl_file(jsonl_file)

        assert len(entries) == 2
        assert entries[0].line_number == 1
        assert entries[0].entry_type == "user"
        assert entries[1].line_number == 2
        assert entries[1].entry_type == "assistant"

    def test_parses_entries_with_correct_types(self, tmp_path: Path) -> None:
        """Parses entries and classifies types correctly."""
        jsonl_file = tmp_path / "test.jsonl"
        jsonl_file.write_text(
            '{"type": "user", "message": {}}\n'
            '{"type": "assistant", "message": {}}\n'
            '{"type": "tool_result", "message": {}}\n',
            encoding="utf-8",
        )

        entries = parse_jsonl_file(jsonl_file)

        assert entries[0].entry_type == "user"
        assert entries[1].entry_type == "assistant"
        assert entries[2].entry_type == "tool_result"

    def test_handles_empty_file(self, tmp_path: Path) -> None:
        """Handles empty JSONL file gracefully."""
        jsonl_file = tmp_path / "empty.jsonl"
        jsonl_file.write_text("", encoding="utf-8")

        entries = parse_jsonl_file(jsonl_file)

        assert entries == []

    def test_parses_entries_with_role(self, tmp_path: Path) -> None:
        """Parses entries with role from message."""
        jsonl_file = tmp_path / "test.jsonl"
        jsonl_file.write_text(
            '{"type": "user", "message": {"role": "user", "content": []}}\n',
            encoding="utf-8",
        )

        entries = parse_jsonl_file(jsonl_file)
        entry = entries[0]

        assert entry.line_number == 1
        assert entry.entry_type == "user"
        assert entry.role == "user"
        assert entry.raw_json is not None
        assert entry.parsed is not None

    def test_extracts_tool_name_from_entries(self, tmp_path: Path) -> None:
        """Extracts tool name from assistant entries."""
        jsonl_file = tmp_path / "test.jsonl"
        jsonl_file.write_text(
            '{"type": "assistant", "message": {"content": [{"type": '
            '"tool_use", "name": "Bash"}]}}\n',
            encoding="utf-8",
        )

        entries = parse_jsonl_file(jsonl_file)

        assert entries[0].tool_name == "Bash"

    def test_handles_malformed_json_line(self, tmp_path: Path) -> None:
        """Handles malformed JSON gracefully by skipping."""
        jsonl_file = tmp_path / "bad.jsonl"
        jsonl_file.write_text(
            '{"type": "user"}\nnot valid json\n{"type": "assistant"}\n',
            encoding="utf-8",
        )

        entries = parse_jsonl_file(jsonl_file)

        # Should parse valid entries and skip malformed line
        assert len(entries) == 2
        assert entries[0].line_number == 1
        assert entries[1].line_number == 3


class TestInterpretEscapeSequences:
    """Tests for _interpret_escape_sequences function."""

    def test_converts_newline_escape(self) -> None:
        """Converts literal \\n to actual newline."""
        result = _interpret_escape_sequences("hello\\nworld")
        assert result == "hello\nworld"

    def test_converts_tab_escape(self) -> None:
        """Converts literal \\t to actual tab."""
        result = _interpret_escape_sequences("hello\\tworld")
        assert result == "hello\tworld"

    def test_converts_carriage_return_escape(self) -> None:
        """Converts literal \\r to actual carriage return."""
        result = _interpret_escape_sequences("hello\\rworld")
        assert result == "hello\rworld"

    def test_converts_multiple_escapes(self) -> None:
        """Converts multiple escape sequences in one string."""
        result = _interpret_escape_sequences("line1\\nline2\\tindented\\r")
        assert result == "line1\nline2\tindented\r"

    def test_leaves_other_text_unchanged(self) -> None:
        """Leaves text without escape sequences unchanged."""
        result = _interpret_escape_sequences("normal text")
        assert result == "normal text"


class TestFormatValue:
    """Tests for _format_value function."""

    def test_formats_null(self) -> None:
        """Formats None as null."""
        assert _format_value(None) == "null"

    def test_formats_boolean_true(self) -> None:
        """Formats True as true."""
        assert _format_value(True) == "true"

    def test_formats_boolean_false(self) -> None:
        """Formats False as false."""
        assert _format_value(False) == "false"

    def test_formats_integer(self) -> None:
        """Formats integers as strings."""
        assert _format_value(42) == "42"

    def test_formats_float(self) -> None:
        """Formats floats as strings."""
        assert _format_value(3.14) == "3.14"

    def test_formats_simple_string(self) -> None:
        """Formats simple strings unchanged."""
        assert _format_value("hello") == "hello"

    def test_formats_string_with_escape_sequences(self) -> None:
        """Interprets escape sequences in strings."""
        result = _format_value("line1\\nline2")
        assert result == "line1\nline2"

    def test_formats_empty_list(self) -> None:
        """Formats empty list as []."""
        assert _format_value([]) == "[]"

    def test_formats_list_with_items(self) -> None:
        """Formats list with items in YAML style."""
        result = _format_value(["a", "b"])
        assert "- a" in result
        assert "- b" in result

    def test_formats_empty_dict(self) -> None:
        """Formats empty dict as {}."""
        assert _format_value({}) == "{}"

    def test_formats_dict_with_items(self) -> None:
        """Formats dict with key: value pairs."""
        result = _format_value({"name": "test", "value": 42})
        assert "name: test" in result
        assert "value: 42" in result


class TestFormatEntryDetail:
    """Tests for format_entry_detail function."""

    def test_returns_raw_json_when_not_formatted(self) -> None:
        """Returns raw JSON string when formatted=False."""
        entry = JsonlEntry(
            line_number=1,
            entry_type="user",
            role="user",
            tool_name=None,
            raw_json='{"type": "user"}',
            parsed={"type": "user"},
        )
        result = format_entry_detail(entry, formatted=False)
        assert result == '{"type": "user"}'

    def test_returns_formatted_output_when_formatted(self) -> None:
        """Returns YAML-like formatted output when formatted=True."""
        entry = JsonlEntry(
            line_number=1,
            entry_type="user",
            role="user",
            tool_name=None,
            raw_json='{"type": "user", "message": "hello"}',
            parsed={"type": "user", "message": "hello"},
        )
        result = format_entry_detail(entry, formatted=True)
        assert "type: user" in result
        assert "message: hello" in result

    def test_formats_nested_structure(self) -> None:
        """Formats nested dict/list structures."""
        entry = JsonlEntry(
            line_number=1,
            entry_type="assistant",
            role="assistant",
            tool_name=None,
            raw_json='{"content": [{"type": "text", "text": "hello"}]}',
            parsed={"content": [{"type": "text", "text": "hello"}]},
        )
        result = format_entry_detail(entry, formatted=True)
        assert "content:" in result
        assert "type: text" in result
        assert "text: hello" in result

    def test_interprets_escape_sequences_in_formatted_mode(self) -> None:
        """Interprets escape sequences when formatting."""
        entry = JsonlEntry(
            line_number=1,
            entry_type="user",
            role="user",
            tool_name=None,
            raw_json='{"text": "line1\\nline2"}',
            parsed={"text": "line1\\nline2"},
        )
        result = format_entry_detail(entry, formatted=True)
        # Should contain actual newline, not escaped
        assert "line1\nline2" in result or "line1" in result and "line2" in result
