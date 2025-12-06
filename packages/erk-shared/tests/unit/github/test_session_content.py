"""Tests for session content metadata block functions."""

from erk_shared.github.metadata import (
    CHUNK_SAFETY_BUFFER,
    GITHUB_COMMENT_SIZE_LIMIT,
    chunk_session_content,
    render_session_content_block,
    render_session_content_blocks,
)

# =============================================================================
# Tests for chunk_session_content
# =============================================================================


def test_chunk_session_content_small_content_returns_single_chunk() -> None:
    """Small content that fits in one chunk returns a single-element list."""
    content = "<session>small content</session>"
    chunks = chunk_session_content(content)
    assert len(chunks) == 1
    assert chunks[0] == content


def test_chunk_session_content_respects_max_size() -> None:
    """Content is split into chunks respecting the max size limit."""
    # Create content that will need multiple chunks
    line = "x" * 100 + "\n"
    content = line * 100  # 10100 bytes total

    chunks = chunk_session_content(content, max_chunk_size=1000)

    # Each chunk should be under the limit
    for chunk in chunks:
        assert len(chunk.encode("utf-8")) <= 1000


def test_chunk_session_content_preserves_all_content() -> None:
    """All original content is preserved across chunks."""
    lines = [f"line {i}" for i in range(100)]
    content = "\n".join(lines)

    chunks = chunk_session_content(content, max_chunk_size=200)

    # Reconstruct by joining with newlines (chunks don't include trailing newlines)
    reconstructed = "\n".join(chunks)
    # The reconstructed content should match the original
    assert content == reconstructed


def test_chunk_session_content_handles_empty_content() -> None:
    """Empty content returns a single empty chunk."""
    chunks = chunk_session_content("")
    assert len(chunks) == 1
    assert chunks[0] == ""


def test_chunk_session_content_handles_unicode() -> None:
    """Unicode content is handled correctly without splitting mid-character."""
    # Each emoji is 4 bytes in UTF-8
    emoji_line = "😀" * 10 + "\n"  # 41 bytes per line
    content = emoji_line * 10

    chunks = chunk_session_content(content, max_chunk_size=100)

    # All chunks should be valid UTF-8
    for chunk in chunks:
        # This should not raise
        chunk.encode("utf-8")

    # Content should be preserved
    reconstructed = "\n".join(chunks)
    assert "😀" in reconstructed


def test_chunk_session_content_default_size_is_github_limit() -> None:
    """Default max_chunk_size uses the GitHub comment limit minus safety buffer."""
    expected_default = GITHUB_COMMENT_SIZE_LIMIT - CHUNK_SAFETY_BUFFER

    # Small content should fit in one chunk with default
    small_content = "x" * 1000
    chunks = chunk_session_content(small_content)
    assert len(chunks) == 1

    # Content just over the limit should split
    large_content = "x" * (expected_default + 100)
    chunks = chunk_session_content(large_content)
    assert len(chunks) > 1


# =============================================================================
# Tests for render_session_content_block
# =============================================================================


def test_render_session_content_block_basic() -> None:
    """Basic rendering includes metadata block markers and content."""
    content = "<session>test</session>"
    result = render_session_content_block(content)

    assert "<!-- erk:metadata-block:session-content -->" in result
    assert "<!-- /erk:metadata-block:session-content -->" in result
    assert "<details>" in result
    assert "</details>" in result
    assert "```xml" in result
    assert content in result
    assert "<summary><strong>Session Data</strong></summary>" in result


def test_render_session_content_block_with_chunk_numbers() -> None:
    """Chunk numbers are included in the summary when provided."""
    result = render_session_content_block(
        "content",
        chunk_number=2,
        total_chunks=5,
    )

    assert "Session Data (2/5)" in result


def test_render_session_content_block_with_session_label() -> None:
    """Session label is appended to the summary."""
    result = render_session_content_block(
        "content",
        session_label="fix-auth-bug",
    )

    assert "Session Data: fix-auth-bug" in result


def test_render_session_content_block_with_chunk_and_label() -> None:
    """Both chunk numbers and label can be combined."""
    result = render_session_content_block(
        "content",
        chunk_number=1,
        total_chunks=3,
        session_label="refactor-cli",
    )

    assert "Session Data (1/3): refactor-cli" in result


def test_render_session_content_block_with_extraction_hints() -> None:
    """Extraction hints are rendered as a bulleted list."""
    hints = ["Error handling patterns", "Test fixture setup"]
    result = render_session_content_block(
        "content",
        extraction_hints=hints,
    )

    assert "**Extraction Hints:**" in result
    assert "- Error handling patterns" in result
    assert "- Test fixture setup" in result


def test_render_session_content_block_without_hints_no_section() -> None:
    """When no hints provided, the hints section is not rendered."""
    result = render_session_content_block("content")

    assert "**Extraction Hints:**" not in result


def test_render_session_content_block_includes_warning_comment() -> None:
    """The machine-generated warning comment is included."""
    result = render_session_content_block("content")

    assert "<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->" in result


# =============================================================================
# Tests for render_session_content_blocks
# =============================================================================


def test_render_session_content_blocks_single_chunk() -> None:
    """Small content produces a single block without chunk numbers."""
    content = "<session>small</session>"
    blocks = render_session_content_blocks(content)

    assert len(blocks) == 1
    # No chunk numbers for single chunk
    assert "(1/1)" not in blocks[0]
    assert "Session Data</strong>" in blocks[0]


def test_render_session_content_blocks_multiple_chunks() -> None:
    """Large content produces multiple blocks with chunk numbers."""
    # Create content that will need chunking
    content = "x" * 5000
    blocks = render_session_content_blocks(content, max_chunk_size=1000)

    assert len(blocks) > 1
    # Each block should have chunk numbers
    assert "(1/" in blocks[0]
    assert f"({len(blocks)}/{len(blocks)})" in blocks[-1]


def test_render_session_content_blocks_hints_only_in_first() -> None:
    """Extraction hints are only included in the first chunk."""
    content = "x" * 5000
    hints = ["Hint 1", "Hint 2"]
    blocks = render_session_content_blocks(
        content,
        extraction_hints=hints,
        max_chunk_size=1000,
    )

    assert len(blocks) > 1
    # First block has hints
    assert "**Extraction Hints:**" in blocks[0]
    assert "- Hint 1" in blocks[0]
    # Subsequent blocks don't have hints
    for block in blocks[1:]:
        assert "**Extraction Hints:**" not in block


def test_render_session_content_blocks_with_label() -> None:
    """Session label is included in all chunks."""
    content = "x" * 5000
    blocks = render_session_content_blocks(
        content,
        session_label="my-feature",
        max_chunk_size=1000,
    )

    for block in blocks:
        assert "my-feature" in block


def test_render_session_content_blocks_content_preserved() -> None:
    """All content is preserved across rendered blocks."""
    lines = [f"<line id='{i}'>content {i}</line>" for i in range(50)]
    content = "\n".join(lines)

    blocks = render_session_content_blocks(content, max_chunk_size=500)

    # Join all blocks and check each original line is present somewhere
    all_blocks = "\n".join(blocks)
    for line in lines:
        assert line in all_blocks
