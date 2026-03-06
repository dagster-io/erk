"""Assistant message deduplication tests for session log preprocessing."""

from erk.cli.commands.exec.scripts.preprocess_session import deduplicate_assistant_messages


def test_deduplicate_removes_duplicate_text_with_tool_use() -> None:
    """Test that duplicate assistant text is removed when tool_use present."""
    # Setup: Two assistant messages with same text, second has tool_use
    entries = [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "I'll help"}]}},
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "I'll help"},
                    {"type": "tool_use", "id": "toolu_123", "name": "Read"},
                ]
            },
        },
    ]
    result = deduplicate_assistant_messages(entries)

    # First message unchanged, second message should only have tool_use
    assert len(result[1]["message"]["content"]) == 1
    assert result[1]["message"]["content"][0]["type"] == "tool_use"


def test_deduplicate_preserves_text_without_tool_use() -> None:
    """Test that text is preserved when no tool_use present."""
    entries = [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "First"}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Second"}]}},
    ]
    result = deduplicate_assistant_messages(entries)

    # Both messages should keep their text
    assert result[0]["message"]["content"][0]["text"] == "First"
    assert result[1]["message"]["content"][0]["text"] == "Second"


def test_deduplicate_preserves_first_assistant_text() -> None:
    """Test that first assistant message is never deduplicated."""
    entries = [{"type": "assistant", "message": {"content": [{"type": "text", "text": "Hello"}]}}]
    result = deduplicate_assistant_messages(entries)
    assert result[0]["message"]["content"][0]["text"] == "Hello"


def test_deduplicate_handles_empty_content() -> None:
    """Test handling of assistant messages with empty content."""
    entries = [{"type": "assistant", "message": {"content": []}}]
    result = deduplicate_assistant_messages(entries)
    assert result == entries


def test_deduplicate_handles_no_assistant_messages() -> None:
    """Test handling of entries with no assistant messages."""
    entries = [{"type": "user", "message": {"content": "Hello"}}]
    result = deduplicate_assistant_messages(entries)
    assert result == entries
