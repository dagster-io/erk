"""Tests for session content metadata block functions."""

from erk_shared.github.metadata import (
    CHUNK_SAFETY_BUFFER,
    GITHUB_COMMENT_SIZE_LIMIT,
    chunk_session_content,
    render_session_content_block,
    render_session_content_blocks,
)

# === chunk_session_content Tests ===


def test_chunk_session_content_small_content_single_chunk() -> None:
    """Test that small content returns a single chunk."""
    content = "<session>\n  <message>Hello</message>\n</session>"
    chunks = chunk_session_content(content)

    assert len(chunks) == 1
    assert chunks[0] == content


def test_chunk_session_content_exact_limit_single_chunk() -> None:
    """Test that content at exactly max size returns a single chunk."""
    max_size = 100
    content = "x" * max_size
    chunks = chunk_session_content(content, max_chunk_size=max_size)

    assert len(chunks) == 1
    assert chunks[0] == content


def test_chunk_session_content_splits_at_line_boundaries() -> None:
    """Test that chunking splits on line boundaries, not mid-line."""
    # Create content that exceeds limit but has clear line breaks
    line = "x" * 50
    content = "\n".join([line] * 5)  # 5 lines of 50 chars each = ~255 chars

    # Use a max size that forces splitting between lines
    chunks = chunk_session_content(content, max_chunk_size=110)

    # Each chunk should contain complete lines
    assert len(chunks) > 1
    for chunk in chunks:
        # No line should be cut mid-way (all lines should be 50 chars or less)
        for line in chunk.split("\n"):
            assert len(line) <= 50


def test_chunk_session_content_preserves_all_content() -> None:
    """Test that chunking preserves all original content."""
    lines = [f"Line {i}: " + "x" * 40 for i in range(10)]
    content = "\n".join(lines)

    chunks = chunk_session_content(content, max_chunk_size=200)

    # Reconstruct content from chunks
    reconstructed = "\n".join(chunks)

    assert reconstructed == content


def test_chunk_session_content_empty_content() -> None:
    """Test chunking empty content."""
    chunks = chunk_session_content("")

    assert len(chunks) == 1
    assert chunks[0] == ""


def test_chunk_session_content_default_limit() -> None:
    """Test that default limit is GITHUB_COMMENT_SIZE_LIMIT - CHUNK_SAFETY_BUFFER."""
    # Create content just under the default limit
    content = "x" * (GITHUB_COMMENT_SIZE_LIMIT - CHUNK_SAFETY_BUFFER - 10)
    chunks = chunk_session_content(content)

    assert len(chunks) == 1

    # Create content just over the default limit
    content_over = "x" * (GITHUB_COMMENT_SIZE_LIMIT - CHUNK_SAFETY_BUFFER + 10)
    chunks_over = chunk_session_content(content_over)

    # May be 1 or more chunks depending on line splitting
    assert len(chunks_over) >= 1


def test_chunk_session_content_large_xml() -> None:
    """Test chunking realistic large XML session content."""
    # Simulate a large session with many messages
    messages = []
    for i in range(100):
        msg = f'  <message id="{i}">\n    <content>Test message {i}</content>\n  </message>'
        messages.append(msg)

    content = "<session>\n" + "\n".join(messages) + "\n</session>"

    # Force chunking with a small limit
    chunks = chunk_session_content(content, max_chunk_size=500)

    assert len(chunks) > 1
    # All content should be preserved
    reconstructed = "\n".join(chunks)
    assert reconstructed == content


# === render_session_content_block Tests ===


def test_render_session_content_block_basic() -> None:
    """Test basic rendering without optional parameters."""
    content = "<session>\n  <message>Hello</message>\n</session>"
    rendered = render_session_content_block(content)

    # Verify metadata block structure
    assert "<!-- WARNING: Machine-generated" in rendered
    assert "<!-- erk:metadata-block:session-content -->" in rendered
    assert "<!-- /erk:metadata-block:session-content -->" in rendered

    # Verify details structure
    assert "<details>" in rendered
    assert "<summary><strong>Session Data</strong></summary>" in rendered
    assert "</details>" in rendered

    # Verify XML code fence
    assert "```xml" in rendered
    assert content in rendered
    assert "```" in rendered


def test_render_session_content_block_with_chunk_numbers() -> None:
    """Test rendering with chunk numbering."""
    content = "<session>...</session>"
    rendered = render_session_content_block(
        content,
        chunk_number=2,
        total_chunks=5,
    )

    assert "<summary><strong>Session Data (2/5)</strong></summary>" in rendered


def test_render_session_content_block_with_session_label() -> None:
    """Test rendering with session label."""
    content = "<session>...</session>"
    rendered = render_session_content_block(
        content,
        session_label="fix-auth-bug",
    )

    assert "<summary><strong>Session Data: fix-auth-bug</strong></summary>" in rendered


def test_render_session_content_block_with_all_parameters() -> None:
    """Test rendering with all parameters."""
    content = "<session>...</session>"
    rendered = render_session_content_block(
        content,
        chunk_number=1,
        total_chunks=3,
        session_label="fix-auth-bug",
        extraction_hints=["Error handling patterns", "Test fixture setup"],
    )

    # Verify summary includes chunk and label
    assert "<summary><strong>Session Data (1/3): fix-auth-bug</strong></summary>" in rendered

    # Verify extraction hints section
    assert "**Extraction Hints:**" in rendered
    assert "- Error handling patterns" in rendered
    assert "- Test fixture setup" in rendered


def test_render_session_content_block_extraction_hints_only() -> None:
    """Test rendering with only extraction hints."""
    content = "<session>...</session>"
    rendered = render_session_content_block(
        content,
        extraction_hints=["CLI patterns", "Config management"],
    )

    assert "**Extraction Hints:**" in rendered
    assert "- CLI patterns" in rendered
    assert "- Config management" in rendered
    # No chunk numbering
    assert "Session Data (1/" not in rendered


def test_render_session_content_block_empty_hints_list() -> None:
    """Test that empty hints list doesn't render hints section."""
    content = "<session>...</session>"
    rendered = render_session_content_block(
        content,
        extraction_hints=[],
    )

    assert "**Extraction Hints:**" not in rendered


def test_render_session_content_block_preserves_xml_content() -> None:
    """Test that XML content is preserved exactly."""
    content = """<session>
  <user>schrockn</user>
  <messages>
    <message type="human">How do I fix this?</message>
    <message type="assistant">Let me help you.</message>
  </messages>
</session>"""
    rendered = render_session_content_block(content)

    assert content in rendered


# === render_session_content_blocks Tests ===


def test_render_session_content_blocks_small_content_single_block() -> None:
    """Test that small content returns a single rendered block."""
    content = "<session>\n  <message>Hello</message>\n</session>"
    blocks = render_session_content_blocks(
        content,
        session_label="test-branch",
    )

    assert len(blocks) == 1
    # No chunk numbering for single block
    assert "Session Data: test-branch" in blocks[0]
    assert "(1/" not in blocks[0]


def test_render_session_content_blocks_large_content_multiple_blocks() -> None:
    """Test that large content returns multiple numbered blocks."""
    # Create content that will require chunking
    lines = [f"<message>{i}</message>" for i in range(100)]
    content = "<session>\n" + "\n".join(lines) + "\n</session>"

    blocks = render_session_content_blocks(
        content,
        session_label="feature-branch",
        max_chunk_size=500,
    )

    assert len(blocks) > 1

    # First block should have numbering
    assert "(1/" in blocks[0]
    assert "feature-branch" in blocks[0]

    # Last block should have correct numbering
    assert f"({len(blocks)}/{len(blocks)})" in blocks[-1]


def test_render_session_content_blocks_hints_only_in_first_chunk() -> None:
    """Test that extraction hints appear only in the first chunk."""
    lines = [f"<message>{i}</message>" for i in range(100)]
    content = "<session>\n" + "\n".join(lines) + "\n</session>"

    blocks = render_session_content_blocks(
        content,
        extraction_hints=["Pattern A", "Pattern B"],
        max_chunk_size=500,
    )

    assert len(blocks) > 1

    # First block should have hints
    assert "**Extraction Hints:**" in blocks[0]
    assert "- Pattern A" in blocks[0]

    # Subsequent blocks should not have hints
    for block in blocks[1:]:
        assert "**Extraction Hints:**" not in block


def test_render_session_content_blocks_all_parameters() -> None:
    """Test render_session_content_blocks with all parameters."""
    content = "<session>\n  <message>Test</message>\n</session>"
    blocks = render_session_content_blocks(
        content,
        session_label="my-feature",
        extraction_hints=["Hint 1"],
    )

    assert len(blocks) == 1
    assert "Session Data: my-feature" in blocks[0]
    assert "**Extraction Hints:**" in blocks[0]
    assert "- Hint 1" in blocks[0]


def test_render_session_content_blocks_preserves_content() -> None:
    """Test that all content is preserved across chunked blocks."""
    # Create test content
    lines = [f"<line{i}>content{i}</line{i}>" for i in range(50)]
    content = "<session>\n" + "\n".join(lines) + "\n</session>"

    blocks = render_session_content_blocks(
        content,
        max_chunk_size=500,
    )

    # Verify all lines appear in some block
    for line in lines:
        found = any(line in block for block in blocks)
        assert found, f"Line not found in any block: {line}"


def test_render_session_content_blocks_valid_metadata_structure() -> None:
    """Test that all rendered blocks have valid metadata block structure."""
    lines = [f"<message>{i}</message>" for i in range(50)]
    content = "<session>\n" + "\n".join(lines) + "\n</session>"

    blocks = render_session_content_blocks(
        content,
        max_chunk_size=500,
    )

    for block in blocks:
        # Each block should have proper metadata structure
        assert "<!-- WARNING: Machine-generated" in block
        assert "<!-- erk:metadata-block:session-content -->" in block
        assert "<!-- /erk:metadata-block:session-content -->" in block
        assert "<details>" in block
        assert "</details>" in block
        assert "```xml" in block
