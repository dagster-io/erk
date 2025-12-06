"""Tests for session preprocessing module - Stage 1 deterministic reduction."""

import json
from pathlib import Path

from erk_shared.extraction.session_preprocessing import (
    compact_whitespace,
    deduplicate_assistant_messages,
    escape_xml,
    generate_compressed_xml,
    preprocess_session,
    process_log_file,
    reduce_session_mechanically,
    remove_empty_text_blocks,
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


class TestCompactWhitespace:
    """Tests for compact_whitespace function."""

    def test_leaves_single_newlines_alone(self) -> None:
        """Single newlines are preserved."""
        assert compact_whitespace("a\nb") == "a\nb"

    def test_leaves_double_newlines_alone(self) -> None:
        """Double newlines are preserved."""
        assert compact_whitespace("a\n\nb") == "a\n\nb"

    def test_compacts_triple_newlines(self) -> None:
        """Triple newlines are compacted to double."""
        assert compact_whitespace("a\n\n\nb") == "a\n\nb"

    def test_compacts_many_newlines(self) -> None:
        """Many newlines are compacted to double."""
        assert compact_whitespace("a\n\n\n\n\nb") == "a\n\nb"


class TestRemoveEmptyTextBlocks:
    """Tests for remove_empty_text_blocks function."""

    def test_removes_empty_text_blocks(self) -> None:
        """Empty text blocks are removed."""
        blocks = [
            {"type": "text", "text": ""},
            {"type": "text", "text": "content"},
        ]
        result = remove_empty_text_blocks(blocks)
        assert len(result) == 1
        assert result[0]["text"] == "content"

    def test_removes_whitespace_only_blocks(self) -> None:
        """Whitespace-only text blocks are removed."""
        blocks = [
            {"type": "text", "text": "   "},
            {"type": "text", "text": "\n\t"},
            {"type": "text", "text": "content"},
        ]
        result = remove_empty_text_blocks(blocks)
        assert len(result) == 1
        assert result[0]["text"] == "content"

    def test_preserves_non_text_blocks(self) -> None:
        """Non-text blocks are preserved regardless of content."""
        blocks = [
            {"type": "tool_use", "name": "Read"},
            {"type": "text", "text": ""},
        ]
        result = remove_empty_text_blocks(blocks)
        assert len(result) == 1
        assert result[0]["type"] == "tool_use"


class TestDeduplicateAssistantMessages:
    """Tests for deduplicate_assistant_messages function."""

    def test_removes_duplicate_text_when_tool_use_present(self) -> None:
        """Duplicate assistant text is removed when tool_use follows."""
        entries = [
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Let me help"}]},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "Let me help"},
                        {"type": "tool_use", "name": "Read"},
                    ]
                },
            },
        ]
        result = deduplicate_assistant_messages(entries)
        # Second entry should only have tool_use
        assert len(result[1]["message"]["content"]) == 1
        assert result[1]["message"]["content"][0]["type"] == "tool_use"


class TestReduceSessionMechanically:
    """Tests for reduce_session_mechanically function - Stage 1 core logic."""

    def test_drops_file_history_snapshot(self) -> None:
        """file-history-snapshot entries are dropped entirely."""
        entries = [
            {"type": "user", "message": {"content": "Hello"}},
            {"type": "file-history-snapshot", "message": {}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi"}]}},
        ]
        result = reduce_session_mechanically(entries)
        assert len(result) == 2
        assert all(e["type"] != "file-history-snapshot" for e in result)

    def test_strips_usage_metadata(self) -> None:
        """usage metadata is stripped from assistant messages."""
        entries = [
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": "Hi"}],
                    "usage": {"input_tokens": 100, "output_tokens": 50},
                },
            },
        ]
        result = reduce_session_mechanically(entries)
        assert "usage" not in result[0]["message"]

    def test_removes_empty_text_blocks(self) -> None:
        """Empty text blocks are removed from content."""
        entries = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": ""},
                        {"type": "text", "text": "content"},
                    ]
                },
            },
        ]
        result = reduce_session_mechanically(entries)
        assert len(result[0]["message"]["content"]) == 1
        assert result[0]["message"]["content"][0]["text"] == "content"

    def test_preserves_git_branch(self) -> None:
        """gitBranch is preserved for metadata extraction."""
        entries = [
            {
                "type": "user",
                "message": {"content": "Hello"},
                "gitBranch": "feature/test",
            },
        ]
        result = reduce_session_mechanically(entries)
        assert result[0]["gitBranch"] == "feature/test"


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

    def test_compacts_whitespace_in_content(self) -> None:
        """Multiple newlines in content are compacted."""
        entries = [
            {"type": "user", "message": {"content": "Hello\n\n\n\nWorld"}},
        ]
        result = generate_compressed_xml(entries)
        assert "Hello\n\nWorld" in result
        assert "Hello\n\n\n\nWorld" not in result


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

    def test_always_returns_xml_no_empty_check(self, tmp_path: Path) -> None:
        """Stage 1 always returns XML - semantic emptiness check delegated to Haiku."""
        log_file = tmp_path / "session.jsonl"
        entries = [{"type": "user", "message": {"content": ""}}]
        log_file.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

        result = preprocess_session(log_file)

        # Stage 1 returns XML structure even for minimal sessions
        # Haiku (Stage 2) decides if content is meaningful
        assert "<session>" in result

    def test_no_warmup_filtering(self, tmp_path: Path) -> None:
        """Stage 1 does not filter warmup sessions - delegated to Haiku."""
        log_file = tmp_path / "session.jsonl"
        entries = [
            {"type": "user", "message": {"content": "warmup: get ready"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Ready!"}]}},
            {"type": "user", "message": {"content": "done"}},
        ]
        log_file.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

        result = preprocess_session(log_file)

        # Stage 1 includes warmup content - Haiku decides if it's noise
        assert "warmup" in result
        assert "<session>" in result
