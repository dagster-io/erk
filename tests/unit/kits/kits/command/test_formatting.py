"""Layer 3 tests: Pure formatting function tests (no I/O, no mocking)."""

from erk_kits.data.kits.command.scripts.command.formatting import (
    format_complex_parameter,
    format_string_parameter,
    format_string_result,
    format_structured_result,
)


class TestFormatStringParameter:
    """Tests for format_string_parameter function."""

    def test_inline_string(self) -> None:
        """Test formatting simple inline string parameter."""
        result = format_string_parameter("command", "pytest tests/")
        assert result == ["   command: pytest tests/"]

    def test_multiline_string(self) -> None:
        """Test formatting multiline string parameter."""
        result = format_string_parameter("script", "line1\nline2\nline3")
        assert result == [
            "   script:",
            "      line1",
            "      line2",
            "      line3",
        ]

    def test_empty_string(self) -> None:
        """Test formatting empty string parameter."""
        result = format_string_parameter("empty", "")
        assert result == ["   empty: "]

    def test_string_with_only_newline(self) -> None:
        """Test formatting string that is just a newline."""
        result = format_string_parameter("newline", "\n")
        assert result == [
            "   newline:",
            "      ",
            "      ",
        ]

    def test_string_with_trailing_newline(self) -> None:
        """Test formatting string with trailing newline."""
        result = format_string_parameter("trailing", "content\n")
        assert result == [
            "   trailing:",
            "      content",
            "      ",
        ]

    def test_string_with_leading_newline(self) -> None:
        """Test formatting string with leading newline."""
        result = format_string_parameter("leading", "\ncontent")
        assert result == [
            "   leading:",
            "      ",
            "      content",
        ]

    def test_string_with_special_characters(self) -> None:
        """Test formatting string with special characters."""
        result = format_string_parameter("special", "tab\there\nand newline")
        assert result == [
            "   special:",
            "      tab\there",
            "      and newline",
        ]


class TestFormatComplexParameter:
    """Tests for format_complex_parameter function."""

    def test_simple_dict_parameter(self) -> None:
        """Test formatting simple dictionary parameter."""
        result = format_complex_parameter("config", {"key": "value"})
        assert result[0] == "   config:"
        assert '"key": "value"' in "\n".join(result)

    def test_simple_list_parameter(self) -> None:
        """Test formatting simple list parameter."""
        result = format_complex_parameter("items", ["a", "b", "c"])
        assert result[0] == "   items:"
        joined = "\n".join(result)
        assert '"a"' in joined
        assert '"b"' in joined
        assert '"c"' in joined

    def test_nested_dict_parameter(self) -> None:
        """Test formatting nested dictionary parameter."""
        result = format_complex_parameter(
            "nested",
            {"outer": {"inner": "value"}},
        )
        assert result[0] == "   nested:"
        joined = "\n".join(result)
        assert '"outer"' in joined
        assert '"inner"' in joined
        assert '"value"' in joined

    def test_list_of_dicts_parameter(self) -> None:
        """Test formatting list of dictionaries parameter."""
        result = format_complex_parameter(
            "todos",
            [
                {"content": "Task 1", "status": "pending"},
                {"content": "Task 2", "status": "completed"},
            ],
        )
        assert result[0] == "   todos:"
        joined = "\n".join(result)
        assert "Task 1" in joined
        assert "Task 2" in joined
        assert "pending" in joined
        assert "completed" in joined

    def test_empty_dict_parameter(self) -> None:
        """Test formatting empty dictionary parameter."""
        result = format_complex_parameter("empty", {})
        assert result == [
            "   empty:",
            "      {}",
        ]

    def test_empty_list_parameter(self) -> None:
        """Test formatting empty list parameter."""
        result = format_complex_parameter("empty_list", [])
        assert result == [
            "   empty_list:",
            "      []",
        ]

    def test_unicode_in_complex_parameter(self) -> None:
        """Test formatting complex parameter with unicode characters."""
        result = format_complex_parameter("unicode", {"emoji": "🚀", "text": "Hello 世界"})
        joined = "\n".join(result)
        assert "🚀" in joined
        assert "世界" in joined

    def test_numbers_in_complex_parameter(self) -> None:
        """Test formatting complex parameter with numbers."""
        result = format_complex_parameter("numbers", {"int": 42, "float": 3.14, "bool": True})
        joined = "\n".join(result)
        assert "42" in joined
        assert "3.14" in joined
        assert "true" in joined  # JSON uses lowercase for booleans


class TestFormatStringResult:
    """Tests for format_string_result function."""

    def test_single_line_result(self) -> None:
        """Test formatting single-line string result."""
        result = format_string_result("Success message")
        assert result == ["   Success message"]

    def test_multiline_result(self) -> None:
        """Test formatting multiline string result."""
        result = format_string_result("Line 1\nLine 2\nLine 3")
        assert result == [
            "   Line 1",
            "   Line 2",
            "   Line 3",
        ]

    def test_empty_string_result(self) -> None:
        """Test formatting empty string result."""
        result = format_string_result("")
        assert result == ["   "]

    def test_result_with_only_newlines(self) -> None:
        """Test formatting result with only newlines."""
        result = format_string_result("\n\n")
        assert result == [
            "   ",
            "   ",
            "   ",
        ]

    def test_result_with_trailing_newline(self) -> None:
        """Test formatting result with trailing newline."""
        result = format_string_result("content\n")
        assert result == [
            "   content",
            "   ",
        ]

    def test_result_with_mixed_whitespace(self) -> None:
        """Test formatting result with tabs and spaces."""
        result = format_string_result("line with\ttab\nline with  spaces")
        assert result == [
            "   line with\ttab",
            "   line with  spaces",
        ]


class TestFormatStructuredResult:
    """Tests for format_structured_result function."""

    def test_single_text_item(self) -> None:
        """Test formatting result with single text item."""
        result = format_structured_result([{"type": "text", "text": "Output line"}])
        assert result == ["   Output line"]

    def test_multiple_text_items(self) -> None:
        """Test formatting result with multiple text items."""
        result = format_structured_result(
            [
                {"type": "text", "text": "Line 1"},
                {"type": "text", "text": "Line 2"},
            ]
        )
        assert result == [
            "   Line 1",
            "   Line 2",
        ]

    def test_multiline_text_items(self) -> None:
        """Test formatting result with multiline text items."""
        result = format_structured_result(
            [
                {"type": "text", "text": "Line 1\nLine 2"},
                {"type": "text", "text": "Line 3\nLine 4"},
            ]
        )
        assert result == [
            "   Line 1",
            "   Line 2",
            "   Line 3",
            "   Line 4",
        ]

    def test_empty_result_list(self) -> None:
        """Test formatting empty result list."""
        result = format_structured_result([])
        assert result == []

    def test_ignores_non_dict_items(self) -> None:
        """Test that non-dict items in list are ignored."""
        result = format_structured_result(
            [
                {"type": "text", "text": "Valid"},
                "invalid string",
                42,
                None,
                {"type": "text", "text": "Also valid"},
            ]
        )
        assert result == [
            "   Valid",
            "   Also valid",
        ]

    def test_ignores_non_text_type(self) -> None:
        """Test that non-text type items are ignored."""
        result = format_structured_result(
            [
                {"type": "image", "url": "http://example.com/image.png"},
                {"type": "text", "text": "Text item"},
                {"type": "other", "data": "something"},
            ]
        )
        assert result == ["   Text item"]

    def test_handles_missing_text_field(self) -> None:
        """Test handling of text type item with missing text field."""
        result = format_structured_result(
            [
                {"type": "text"},  # Missing "text" field
                {"type": "text", "text": "Valid"},
            ]
        )
        # Should use empty string as default
        assert result == [
            "   ",
            "   Valid",
        ]

    def test_handles_empty_text_field(self) -> None:
        """Test handling of text type item with empty text field."""
        result = format_structured_result(
            [
                {"type": "text", "text": ""},
                {"type": "text", "text": "Non-empty"},
            ]
        )
        assert result == [
            "   ",
            "   Non-empty",
        ]

    def test_mixed_valid_and_invalid_items(self) -> None:
        """Test formatting with mix of valid and invalid items."""
        result = format_structured_result(
            [
                {"type": "text", "text": "First"},
                "string item",  # Not a dict, ignored
                {"type": "other"},  # Wrong type, ignored
                {"type": "text", "text": "Second"},
                {"no_type": "present"},  # No type field, ignored
                {"type": "text", "text": "Third"},
            ]
        )
        assert result == [
            "   First",
            "   Second",
            "   Third",
        ]
