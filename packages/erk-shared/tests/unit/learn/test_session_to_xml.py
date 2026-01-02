"""Unit tests for session_to_xml module.

Tests cover:
- Deterministic filtering (no LLM needed)
- Deterministic batching (no LLM needed)
- XML conversion with FakePromptExecutor
"""

from erk_shared.learn.session_to_xml import (
    batch_lines,
    convert_batch_to_xml,
    filter_junk_lines,
    session_to_xml,
)
from erk_shared.prompt_executor.fake import FakePromptExecutor


class TestFilterJunkLines:
    """Tests for filter_junk_lines function."""

    def test_empty_input(self) -> None:
        """Empty input returns empty list."""
        result = filter_junk_lines([])
        assert result == []

    def test_filters_empty_lines(self) -> None:
        """Empty and whitespace-only lines are removed."""
        lines = ["line1", "", "line2", "   ", "line3"]
        result = filter_junk_lines(lines)
        assert result == ["line1", "line2", "line3"]

    def test_filters_queue_operations(self) -> None:
        """Queue operation entries are removed."""
        lines = [
            '{"type":"queue-operation","operation":"enqueue"}',
            '{"type":"user","message":"hello"}',
            '{"type":"queue-operation","operation":"dequeue"}',
        ]
        result = filter_junk_lines(lines)
        assert len(result) == 1
        assert '"type":"user"' in result[0]

    def test_preserves_user_assistant_entries(self) -> None:
        """User and assistant entries are preserved."""
        lines = [
            '{"type":"user","message":"hello"}',
            '{"type":"assistant","message":"world"}',
        ]
        result = filter_junk_lines(lines)
        assert result == lines


class TestBatchLines:
    """Tests for batch_lines function."""

    def test_empty_input(self) -> None:
        """Empty input returns empty list."""
        result = batch_lines([], char_limit=100)
        assert result == []

    def test_single_line_under_limit(self) -> None:
        """Single line under limit goes in one batch."""
        lines = ["short"]
        result = batch_lines(lines, char_limit=100)
        assert result == [["short"]]

    def test_multiple_lines_under_limit(self) -> None:
        """Multiple lines fitting in limit go in one batch."""
        lines = ["abc", "def", "ghi"]
        result = batch_lines(lines, char_limit=100)
        assert result == [["abc", "def", "ghi"]]

    def test_lines_split_at_limit(self) -> None:
        """Lines are split when exceeding limit."""
        lines = ["12345", "67890", "abcde"]
        # Each line is 5 chars, limit is 10, so batches: [12345, 67890], [abcde]
        result = batch_lines(lines, char_limit=10)
        assert len(result) == 2
        assert result[0] == ["12345", "67890"]
        assert result[1] == ["abcde"]

    def test_single_line_exceeds_limit(self) -> None:
        """Single line exceeding limit is in its own batch."""
        lines = ["this_is_a_very_long_line"]
        result = batch_lines(lines, char_limit=5)
        assert result == [["this_is_a_very_long_line"]]

    def test_respects_exact_limit(self) -> None:
        """Batching respects exact character limit."""
        lines = ["123", "456"]  # 3 + 3 = 6 chars
        result = batch_lines(lines, char_limit=6)
        assert result == [["123", "456"]]


class TestConvertBatchToXml:
    """Tests for convert_batch_to_xml function."""

    def test_returns_llm_output(self) -> None:
        """Returns the LLM output stripped."""
        fake_executor = FakePromptExecutor(output="<user>hello</user>\n")
        result = convert_batch_to_xml("test content", fake_executor)
        assert result == "<user>hello</user>"

    def test_raises_on_llm_failure(self) -> None:
        """Raises RuntimeError when LLM fails."""
        fake_executor = FakePromptExecutor(should_fail=True, error="API error")
        try:
            convert_batch_to_xml("test content", fake_executor)
            raise AssertionError("Expected RuntimeError")
        except RuntimeError as e:
            assert "LLM batch conversion failed" in str(e)
            assert "API error" in str(e)

    def test_records_prompt_call(self) -> None:
        """Records the prompt call for verification."""
        fake_executor = FakePromptExecutor(output="<user>test</user>")
        convert_batch_to_xml("batch content", fake_executor)

        assert len(fake_executor.prompt_calls) == 1
        call = fake_executor.prompt_calls[0]
        assert "batch content" in call.prompt
        assert call.model == "haiku"


class TestSessionToXml:
    """Tests for session_to_xml function."""

    def test_empty_session(self) -> None:
        """Empty session returns empty XML wrapper."""
        fake_executor = FakePromptExecutor()
        result = session_to_xml("", fake_executor, batch_char_limit=1000)
        assert result == "<session></session>"

    def test_all_junk_session(self) -> None:
        """Session with only junk returns empty XML wrapper."""
        content = '{"type":"queue-operation"}\n{"type":"queue-operation"}'
        fake_executor = FakePromptExecutor()
        result = session_to_xml(content, fake_executor, batch_char_limit=1000)
        assert result == "<session></session>"

    def test_simple_session(self) -> None:
        """Simple session is converted to XML."""
        content = '{"type":"user","message":"hello"}'
        fake_executor = FakePromptExecutor(output="<user>hello</user>")

        result = session_to_xml(content, fake_executor, batch_char_limit=1000)

        assert "<session>" in result
        assert "</session>" in result
        assert "<user>hello</user>" in result

    def test_multiple_batches(self) -> None:
        """Session exceeding batch limit uses multiple LLM calls."""
        # Create content that will be split into 2 batches
        line1 = '{"type":"user","message":"first"}'
        line2 = '{"type":"assistant","message":"second"}'
        content = f"{line1}\n{line2}"

        # Use a small batch limit to force splitting
        # Each line is ~35 chars, limit of 40 should split them
        fake_executor = FakePromptExecutor(output="<converted/>")

        result = session_to_xml(content, fake_executor, batch_char_limit=40)

        # Should have made 2 LLM calls
        assert len(fake_executor.prompt_calls) == 2
        assert "<session>" in result
        assert "</session>" in result

    def test_wraps_in_session_tags(self) -> None:
        """Output is wrapped in <session> tags."""
        content = '{"type":"user"}'
        fake_executor = FakePromptExecutor(output="<user>test</user>")

        result = session_to_xml(content, fake_executor, batch_char_limit=1000)

        assert result.startswith("<session>")
        assert result.endswith("</session>")
