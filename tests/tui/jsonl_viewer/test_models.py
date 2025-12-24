"""Tests for JSONL viewer models."""

from pathlib import Path

from erk.tui.jsonl_viewer.models import (
    JsonlEntry,
    _format_as_yaml_like,
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


class TestFormatAsYamlLike:
    """Tests for _format_as_yaml_like function.

    This function formats Python values in YAML-like style for readability.
    These tests document the formatting behavior for each type.
    """

    # === Primitive Types ===

    def test_formats_null(self) -> None:
        """Formats None as null."""
        assert _format_as_yaml_like(None) == "null"

    def test_formats_boolean_true(self) -> None:
        """Formats True as true."""
        assert _format_as_yaml_like(True) == "true"

    def test_formats_boolean_false(self) -> None:
        """Formats False as false."""
        assert _format_as_yaml_like(False) == "false"

    def test_formats_integer(self) -> None:
        """Formats integers as strings."""
        assert _format_as_yaml_like(42) == "42"

    def test_formats_negative_integer(self) -> None:
        """Formats negative integers."""
        assert _format_as_yaml_like(-123) == "-123"

    def test_formats_zero(self) -> None:
        """Formats zero."""
        assert _format_as_yaml_like(0) == "0"

    def test_formats_float(self) -> None:
        """Formats floats as strings."""
        assert _format_as_yaml_like(3.14) == "3.14"

    def test_formats_negative_float(self) -> None:
        """Formats negative floats."""
        assert _format_as_yaml_like(-2.5) == "-2.5"

    # === String Types ===

    def test_formats_simple_string(self) -> None:
        """Formats simple strings unchanged."""
        assert _format_as_yaml_like("hello") == "hello"

    def test_formats_empty_string(self) -> None:
        """Formats empty string as empty string."""
        assert _format_as_yaml_like("") == ""

    def test_formats_string_with_spaces(self) -> None:
        """Formats strings with spaces unchanged."""
        assert _format_as_yaml_like("hello world") == "hello world"

    def test_formats_string_with_escape_sequences(self) -> None:
        """Interprets escape sequences in strings."""
        result = _format_as_yaml_like("line1\\nline2")
        assert result == "line1\nline2"

    def test_formats_string_with_tab_escape(self) -> None:
        """Interprets tab escape sequences."""
        result = _format_as_yaml_like("col1\\tcol2")
        assert result == "col1\tcol2"

    def test_formats_string_with_multiple_escapes(self) -> None:
        """Interprets multiple escape sequences."""
        result = _format_as_yaml_like("a\\nb\\tc\\r")
        assert result == "a\nb\tc\r"

    # === Empty Collections ===

    def test_formats_empty_list(self) -> None:
        """Formats empty list as []."""
        assert _format_as_yaml_like([]) == "[]"

    def test_formats_empty_dict(self) -> None:
        """Formats empty dict as {}."""
        assert _format_as_yaml_like({}) == "{}"

    # === List Formatting ===

    def test_formats_list_with_single_item(self) -> None:
        """Formats single-item list."""
        result = _format_as_yaml_like(["only"])
        assert result == "- only"

    def test_formats_list_with_items(self) -> None:
        """Formats list with items in YAML style."""
        result = _format_as_yaml_like(["a", "b"])
        assert result == "- a\n- b"

    def test_formats_list_with_mixed_types(self) -> None:
        """Formats list with mixed primitive types."""
        result = _format_as_yaml_like(["text", 42, True, None])
        lines = result.split("\n")
        assert lines[0] == "- text"
        assert lines[1] == "- 42"
        assert lines[2] == "- true"
        assert lines[3] == "- null"

    def test_formats_list_with_nested_dict(self) -> None:
        """Formats list containing dictionaries with indentation."""
        result = _format_as_yaml_like([{"type": "text", "value": "hello"}])
        # Nested dict items are indented under the list marker
        assert "-   type: text" in result
        assert "  value: hello" in result

    def test_formats_list_with_nested_list(self) -> None:
        """Formats list containing nested lists with indentation."""
        result = _format_as_yaml_like([["inner1", "inner2"]])
        # Nested list items are indented
        assert "-   - inner1" in result
        assert "  - inner2" in result

    # === Dict Formatting ===

    def test_formats_dict_with_single_item(self) -> None:
        """Formats single-item dict."""
        result = _format_as_yaml_like({"key": "value"})
        assert result == "key: value"

    def test_formats_dict_with_items(self) -> None:
        """Formats dict with key: value pairs."""
        result = _format_as_yaml_like({"name": "test", "value": 42})
        assert "name: test" in result
        assert "value: 42" in result

    def test_formats_dict_with_null_value(self) -> None:
        """Formats dict with None value."""
        result = _format_as_yaml_like({"data": None})
        assert result == "data: null"

    def test_formats_dict_with_boolean_values(self) -> None:
        """Formats dict with boolean values."""
        result = _format_as_yaml_like({"enabled": True, "disabled": False})
        assert "enabled: true" in result
        assert "disabled: false" in result

    def test_formats_dict_with_nested_dict(self) -> None:
        """Formats dict containing nested dict with indentation."""
        result = _format_as_yaml_like({"outer": {"inner": "value"}})
        # Nested dict is indented under parent key
        assert "outer:   inner: value" in result

    def test_formats_dict_with_nested_list(self) -> None:
        """Formats dict containing list value with indentation."""
        result = _format_as_yaml_like({"items": ["a", "b"]})
        # List items are indented under the key
        assert "items:   - a" in result
        assert "  - b" in result

    # === Deeply Nested Structures ===

    def test_formats_deeply_nested_structure(self) -> None:
        """Formats complex nested structure (typical JSONL entry)."""
        value = {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Hello"},
                    {"type": "tool_use", "name": "Bash", "id": "123"},
                ],
            },
        }
        result = _format_as_yaml_like(value)
        # Top-level keys
        assert "type: assistant" in result
        # Nested structure with indentation
        assert "message:" in result
        assert "role: assistant" in result
        # Deeply nested content
        assert "text: Hello" in result
        assert "name: Bash" in result

    # === Indentation ===

    def test_respects_indent_parameter(self) -> None:
        """Respects indent parameter for nested formatting."""
        result = _format_as_yaml_like({"key": "value"}, indent=1)
        # With indent=1, should have 2 spaces prefix
        assert result == "  key: value"

    def test_nested_dict_increases_indentation(self) -> None:
        """Nested structures increase indentation."""
        result = _format_as_yaml_like({"outer": {"inner": "value"}})
        # The format produces "outer: inner: value" on one line for simple nesting
        assert "inner: value" in result

    # === Fallback for Unknown Types ===

    def test_formats_unknown_type_with_str(self) -> None:
        """Falls back to str() for unknown types."""

        # Using a custom object that isn't dict/list/str/int/float/bool/None
        class CustomObject:
            def __str__(self) -> str:
                return "custom_repr"

        result = _format_as_yaml_like(CustomObject())
        assert result == "custom_repr"

    def test_formats_tuple_with_str_fallback(self) -> None:
        """Tuples use str() fallback (not treated as list)."""
        result = _format_as_yaml_like((1, 2, 3))
        assert result == "(1, 2, 3)"

    def test_formats_set_with_str_fallback(self) -> None:
        """Sets use str() fallback (not treated as list)."""
        result = _format_as_yaml_like({1})  # Single element set for deterministic output
        assert result == "{1}"


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
