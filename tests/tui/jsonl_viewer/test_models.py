"""Tests for JSONL viewer models."""

from pathlib import Path

from erk.tui.jsonl_viewer.models import (
    JsonlEntry,
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


class TestFormatEntryDetail:
    """Tests for format_entry_detail function."""

    def test_raw_mode_preserves_escape_sequences(self) -> None:
        """Raw mode shows escape sequences as literal characters."""
        # In the parsed dict, the string contains literal backslash-n (2 chars)
        # This simulates what you'd get from JSON like: {"text": "line1\\nline2"}
        entry = JsonlEntry(
            line_number=1,
            entry_type="user",
            role="user",
            tool_name=None,
            raw_json="{}",
            parsed={"text": r"line1\nline2"},  # raw string: literal \n
        )
        result = format_entry_detail(entry, formatted=False)
        # Raw mode uses json.dumps which escapes backslash, showing \\n
        assert r"line1\nline2" in result or "line1\\\\nline2" in result

    def test_formatted_mode_interprets_newlines(self) -> None:
        """Formatted mode interprets \\n as actual newlines."""
        # In the parsed dict, the string contains literal backslash-n (2 chars)
        entry = JsonlEntry(
            line_number=1,
            entry_type="user",
            role="user",
            tool_name=None,
            raw_json="{}",
            parsed={"text": r"line1\nline2"},  # raw string: literal \n
        )
        result = format_entry_detail(entry, formatted=True)
        # Formatted mode interprets \n as actual newline
        assert "line1\nline2" in result

    def test_formatted_mode_interprets_tabs(self) -> None:
        """Formatted mode interprets \\t as actual tabs."""
        # In the parsed dict, the string contains literal backslash-t (2 chars)
        entry = JsonlEntry(
            line_number=1,
            entry_type="user",
            role="user",
            tool_name=None,
            raw_json="{}",
            parsed={"text": r"col1\tcol2"},  # raw string: literal \t
        )
        result = format_entry_detail(entry, formatted=True)
        # Formatted mode interprets \t as actual tab
        assert "col1\tcol2" in result

    def test_handles_nested_structures(self) -> None:
        """Handles nested dicts and lists correctly."""
        entry = JsonlEntry(
            line_number=1,
            entry_type="user",
            role="user",
            tool_name=None,
            raw_json="{}",
            parsed={"outer": {"inner": r"value\nwith newline"}},  # raw string
        )
        result = format_entry_detail(entry, formatted=True)
        # Should contain the interpreted newline
        assert "value\nwith newline" in result

    def test_handles_lists(self) -> None:
        """Handles lists correctly."""
        entry = JsonlEntry(
            line_number=1,
            entry_type="user",
            role="user",
            tool_name=None,
            raw_json="{}",
            parsed={"items": [r"first\nsecond", "third"]},  # raw string
        )
        result = format_entry_detail(entry, formatted=True)
        assert "first\nsecond" in result

    def test_handles_empty_dict(self) -> None:
        """Handles empty dict."""
        entry = JsonlEntry(
            line_number=1,
            entry_type="user",
            role="user",
            tool_name=None,
            raw_json="{}",
            parsed={},
        )
        result = format_entry_detail(entry, formatted=True)
        assert result == "{}"

    def test_handles_numbers_and_booleans(self) -> None:
        """Handles non-string primitives correctly."""
        entry = JsonlEntry(
            line_number=1,
            entry_type="user",
            role="user",
            tool_name=None,
            raw_json="{}",
            parsed={"count": 42, "enabled": True, "nothing": None},
        )
        result = format_entry_detail(entry, formatted=True)
        assert "42" in result
        assert "true" in result
        assert "null" in result


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
