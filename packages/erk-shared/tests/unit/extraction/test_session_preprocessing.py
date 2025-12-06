"""Tests for session preprocessing module."""

import json
from pathlib import Path

from erk_shared.extraction.session_preprocessing import (
    escape_xml,
    generate_compressed_xml,
    is_empty_session,
    is_warmup_session,
    preprocess_session,
    process_log_file,
    prune_tool_result_content,
    truncate_parameter_value,
)


class TestEscapeXml:
    """Tests for escape_xml function."""

    def test_escapes_ampersand(self) -> None:
        """Ampersands are escaped."""
        assert escape_xml("foo & bar") == "foo &amp; bar"

    def test_escapes_less_than(self) -> None:
        """Less-than signs are escaped."""
        assert escape_xml("a < b") == "a &lt; b"

    def test_escapes_greater_than(self) -> None:
        """Greater-than signs are escaped."""
        assert escape_xml("a > b") == "a &gt; b"

    def test_escapes_all_special_chars(self) -> None:
        """All special characters are escaped."""
        assert escape_xml("a & b < c > d") == "a &amp; b &lt; c &gt; d"


class TestIsEmptySession:
    """Tests for is_empty_session function."""

    def test_fewer_than_3_entries_is_empty(self) -> None:
        """Sessions with fewer than 3 entries are considered empty."""
        entries = [{"type": "user"}, {"type": "assistant"}]
        assert is_empty_session(entries) is True

    def test_no_user_message_is_empty(self) -> None:
        """Sessions without user messages are considered empty."""
        entries = [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hello"}]}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "World"}]}},
            {"type": "tool_result", "message": {}},
        ]
        assert is_empty_session(entries) is True

    def test_no_assistant_response_is_empty(self) -> None:
        """Sessions without assistant responses are considered empty."""
        entries = [
            {"type": "user", "message": {"content": "Hello"}},
            {"type": "user", "message": {"content": "World"}},
            {"type": "tool_result", "message": {}},
        ]
        assert is_empty_session(entries) is True

    def test_meaningful_session_is_not_empty(self) -> None:
        """Sessions with user message and assistant response are not empty."""
        entries = [
            {"type": "user", "message": {"content": "Hello"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi there!"}]}},
            {"type": "user", "message": {"content": "Thanks"}},
        ]
        assert is_empty_session(entries) is False


class TestIsWarmupSession:
    """Tests for is_warmup_session function."""

    def test_empty_entries_not_warmup(self) -> None:
        """Empty entry list is not a warmup."""
        assert is_warmup_session([]) is False

    def test_warmup_keyword_detected(self) -> None:
        """Sessions with 'warmup' in first user message are warmups."""
        entries = [
            {"type": "user", "message": {"content": "warmup: review the codebase"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Ready"}]}},
        ]
        assert is_warmup_session(entries) is True

    def test_normal_session_not_warmup(self) -> None:
        """Normal sessions without 'warmup' are not warmups."""
        entries = [
            {"type": "user", "message": {"content": "Fix the bug in auth module"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Sure"}]}},
        ]
        assert is_warmup_session(entries) is False


class TestTruncateParameterValue:
    """Tests for truncate_parameter_value function."""

    def test_short_value_unchanged(self) -> None:
        """Values under max_length are unchanged."""
        result = truncate_parameter_value("short value", max_length=200)
        assert result == "short value"

    def test_long_path_truncated_with_ellipsis(self) -> None:
        """Long file paths are truncated preserving start and end."""
        long_path = "/Users/foo/code/project/src/very/deep/nested/module/file.py"
        result = truncate_parameter_value(long_path, max_length=40)
        assert "/.../" in result
        assert result.startswith("/Users")
        assert result.endswith("file.py")

    def test_long_text_truncated_with_marker(self) -> None:
        """Long text is truncated with character count marker."""
        long_text = "a" * 300
        result = truncate_parameter_value(long_text, max_length=200)
        assert "truncated" in result
        assert len(result) < len(long_text)


class TestPruneToolResultContent:
    """Tests for prune_tool_result_content function."""

    def test_short_content_unchanged(self) -> None:
        """Content under 30 lines is unchanged."""
        content = "\n".join(f"line {i}" for i in range(20))
        result = prune_tool_result_content(content)
        assert result == content

    def test_long_content_pruned(self) -> None:
        """Content over 30 lines is pruned."""
        lines = [f"line {i}" for i in range(50)]
        content = "\n".join(lines)
        result = prune_tool_result_content(content)
        assert "omitted" in result
        assert len(result.split("\n")) < 50

    def test_preserves_error_lines(self) -> None:
        """Error lines after line 30 are preserved."""
        lines = [f"line {i}" for i in range(50)]
        lines[40] = "ERROR: something failed"
        content = "\n".join(lines)
        result = prune_tool_result_content(content)
        assert "ERROR: something failed" in result


class TestGenerateCompressedXml:
    """Tests for generate_compressed_xml function."""

    def test_generates_session_wrapper(self) -> None:
        """Output is wrapped in <session> tags."""
        entries = [
            {"type": "user", "message": {"content": "Hello"}},
        ]
        result = generate_compressed_xml(entries)
        assert result.startswith("<session>")
        assert result.endswith("</session>")

    def test_includes_user_content(self) -> None:
        """User messages are included."""
        entries = [
            {"type": "user", "message": {"content": "Hello world"}},
        ]
        result = generate_compressed_xml(entries)
        assert "<user>Hello world</user>" in result

    def test_includes_assistant_text(self) -> None:
        """Assistant text is included."""
        entries = [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi there"}]}},
        ]
        result = generate_compressed_xml(entries)
        assert "<assistant>Hi there</assistant>" in result

    def test_includes_tool_use(self) -> None:
        """Tool use is included with parameters."""
        entries = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "id": "tool123",
                            "input": {"file_path": "/test.py"},
                        }
                    ]
                },
            },
        ]
        result = generate_compressed_xml(entries)
        assert 'name="Read"' in result
        assert 'id="tool123"' in result
        assert '<param name="file_path">/test.py</param>' in result

    def test_includes_source_label(self) -> None:
        """Source label is included as metadata."""
        entries = [{"type": "user", "message": {"content": "Hello"}}]
        result = generate_compressed_xml(entries, source_label="agent-abc")
        assert '<meta source="agent-abc" />' in result


class TestProcessLogFile:
    """Tests for process_log_file function."""

    def test_reads_jsonl_entries(self, tmp_path: Path) -> None:
        """Reads and parses JSONL log file."""
        log_file = tmp_path / "session.jsonl"
        entries = [
            {"type": "user", "message": {"content": "Hello"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi"}]}},
        ]
        log_file.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

        result, total, skipped = process_log_file(log_file)

        assert len(result) == 2
        assert total == 2
        assert skipped == 0

    def test_filters_by_session_id(self, tmp_path: Path) -> None:
        """Entries can be filtered by session ID."""
        log_file = tmp_path / "session.jsonl"
        entries = [
            {"type": "user", "message": {"content": "Hello"}, "sessionId": "abc123"},
            {"type": "user", "message": {"content": "World"}, "sessionId": "def456"},
        ]
        log_file.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

        result, total, skipped = process_log_file(log_file, session_id="abc123")

        assert len(result) == 1
        assert result[0]["message"]["content"] == "Hello"
        assert skipped == 1

    def test_filters_file_history_snapshots(self, tmp_path: Path) -> None:
        """file-history-snapshot entries are filtered out."""
        log_file = tmp_path / "session.jsonl"
        entries = [
            {"type": "user", "message": {"content": "Hello"}},
            {"type": "file-history-snapshot", "message": {}},
        ]
        log_file.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

        result, total, skipped = process_log_file(log_file)

        assert len(result) == 1
        assert result[0]["type"] == "user"


class TestPreprocessSession:
    """Tests for preprocess_session function."""

    def test_preprocesses_simple_session(self, tmp_path: Path) -> None:
        """Simple session is preprocessed to XML."""
        log_file = tmp_path / "session.jsonl"
        entries = [
            {"type": "user", "message": {"content": "Hello"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi there!"}]}},
            {"type": "user", "message": {"content": "Thanks"}},
        ]
        log_file.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

        result = preprocess_session(log_file)

        assert "<session>" in result
        assert "<user>Hello</user>" in result
        assert "<assistant>Hi there!</assistant>" in result

    def test_returns_empty_for_empty_session(self, tmp_path: Path) -> None:
        """Empty sessions return empty string."""
        log_file = tmp_path / "session.jsonl"
        entries = [{"type": "user", "message": {"content": ""}}]
        log_file.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

        result = preprocess_session(log_file)

        assert result == ""

    def test_returns_empty_for_warmup_session(self, tmp_path: Path) -> None:
        """Warmup sessions return empty string."""
        log_file = tmp_path / "session.jsonl"
        entries = [
            {"type": "user", "message": {"content": "warmup: get ready"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Ready!"}]}},
            {"type": "user", "message": {"content": "done"}},
        ]
        log_file.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

        result = preprocess_session(log_file)

        assert result == ""
