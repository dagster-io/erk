"""Unit tests for PR body footer generation.

Tests the canonical build_pr_body_footer, build_remote_execution_note, and
header/footer extraction functions.
"""

from erk_shared.github.pr_footer import (
    build_pr_body_footer,
    build_remote_execution_note,
    extract_footer_from_body,
    extract_header_from_body,
    extract_main_content,
    rebuild_pr_body,
)


def test_build_pr_body_footer_without_issue_number() -> None:
    """Test footer generation without issue number."""
    result = build_pr_body_footer(pr_number=1895, issue_number=None, plans_repo=None)

    assert "---" in result
    assert 'source "$(erk pr checkout 1895 --script)" && erk pr sync --dangerous' in result
    assert "Closes #" not in result


def test_build_pr_body_footer_with_issue_number() -> None:
    """Test footer includes Closes #N when issue_number is provided."""
    result = build_pr_body_footer(pr_number=1895, issue_number=123, plans_repo=None)

    assert "---" in result
    assert "Closes #123" in result
    assert 'source "$(erk pr checkout 1895 --script)" && erk pr sync --dangerous' in result


def test_build_pr_body_footer_issue_number_before_checkout() -> None:
    """Test that Closes #N appears before the checkout command."""
    result = build_pr_body_footer(pr_number=456, issue_number=789, plans_repo=None)

    closes_pos = result.find("Closes #789")
    checkout_pos = result.find("erk pr checkout 456")

    assert closes_pos != -1
    assert checkout_pos != -1
    assert closes_pos < checkout_pos


def test_build_pr_body_footer_includes_sync_command() -> None:
    """Test that footer includes '&& erk pr sync --dangerous' in checkout command."""
    result = build_pr_body_footer(pr_number=100, issue_number=None, plans_repo=None)

    assert "&& erk pr sync --dangerous" in result
    assert 'source "$(erk pr checkout 100 --script)" && erk pr sync --dangerous' in result


def test_build_pr_body_footer_cross_repo_issue() -> None:
    """Test footer uses owner/repo#N format for cross-repo plans."""
    result = build_pr_body_footer(pr_number=100, issue_number=123, plans_repo="owner/plans-repo")

    assert "Closes owner/plans-repo#123" in result
    assert "Closes #123" not in result


# ============================================================================
# build_remote_execution_note Tests
# ============================================================================


def test_build_remote_execution_note_includes_run_id_and_url() -> None:
    """Test that remote execution note includes run ID and URL."""
    result = build_remote_execution_note(
        workflow_run_id="12345678",
        workflow_run_url="https://github.com/owner/repo/actions/runs/12345678",
    )

    assert "12345678" in result
    assert "https://github.com/owner/repo/actions/runs/12345678" in result
    assert "Remotely executed" in result


def test_build_remote_execution_note_is_markdown_link() -> None:
    """Test that the run link is a proper markdown link."""
    result = build_remote_execution_note(
        workflow_run_id="99999",
        workflow_run_url="https://github.com/test/repo/actions/runs/99999",
    )

    assert "[Run #99999](https://github.com/test/repo/actions/runs/99999)" in result


def test_build_remote_execution_note_starts_with_newline() -> None:
    """Test that note starts with newline for proper appending."""
    result = build_remote_execution_note(
        workflow_run_id="123",
        workflow_run_url="https://example.com/123",
    )

    assert result.startswith("\n")


# ============================================================================
# extract_header_from_body Tests
# ============================================================================


def test_extract_header_from_body_with_plan_link() -> None:
    """Test extraction of Plan header."""
    body = "**Plan:** #123\n\nThis is the main content."
    header = extract_header_from_body(body)
    assert header == "**Plan:** #123\n\n"


def test_extract_header_from_body_with_remote_execution() -> None:
    """Test extraction of Remotely executed header."""
    body = "**Remotely executed:** [Run #456](https://example.com)\n\nMain content."
    header = extract_header_from_body(body)
    assert header == "**Remotely executed:** [Run #456](https://example.com)\n\n"


def test_extract_header_from_body_with_multiple_headers() -> None:
    """Test extraction of multiple header lines."""
    body = (
        "**Plan:** #123\n"
        "**Remotely executed:** [Run #456](https://example.com)\n\n"
        "Main content here."
    )
    header = extract_header_from_body(body)
    assert "**Plan:** #123" in header
    assert "**Remotely executed:** [Run #456]" in header


def test_extract_header_from_body_no_header() -> None:
    """Test when there's no header in the body."""
    body = "This is just regular content.\n\nMore content here."
    header = extract_header_from_body(body)
    assert header == ""


def test_extract_header_from_body_empty_body() -> None:
    """Test extraction from empty body."""
    header = extract_header_from_body("")
    assert header == ""


def test_extract_header_from_body_cross_repo_plan() -> None:
    """Test extraction of cross-repo plan header."""
    body = "**Plan:** owner/repo#123\n\nMain content."
    header = extract_header_from_body(body)
    assert header == "**Plan:** owner/repo#123\n\n"


# ============================================================================
# extract_main_content Tests
# ============================================================================


def test_extract_main_content_with_header_and_footer() -> None:
    """Test extraction with both header and footer."""
    body = "**Plan:** #123\n\nMain content here.\n\n---\nCloses #123\nCheckout instructions..."
    content = extract_main_content(body)
    assert content == "Main content here."


def test_extract_main_content_no_header() -> None:
    """Test extraction with footer but no header."""
    body = "Main content here.\n\n---\n\nCloses #123"
    content = extract_main_content(body)
    assert content == "Main content here."


def test_extract_main_content_no_footer() -> None:
    """Test extraction with header but no footer."""
    body = "**Plan:** #123\n\nMain content here."
    content = extract_main_content(body)
    assert content == "Main content here."


def test_extract_main_content_plain_body() -> None:
    """Test extraction with no header or footer."""
    body = "Just plain content."
    content = extract_main_content(body)
    assert content == "Just plain content."


def test_extract_main_content_empty_body() -> None:
    """Test extraction from empty body."""
    content = extract_main_content("")
    assert content == ""


# ============================================================================
# rebuild_pr_body Tests
# ============================================================================


def test_rebuild_pr_body_all_parts() -> None:
    """Test rebuilding with header, content, and footer."""
    result = rebuild_pr_body(
        header="**Plan:** #123\n\n",
        content="Main content here.",
        footer="Closes #123\n\nCheckout instructions...",
    )
    assert "**Plan:** #123" in result
    assert "Main content here." in result
    assert "---" in result
    assert "Closes #123" in result


def test_rebuild_pr_body_no_header() -> None:
    """Test rebuilding without header."""
    result = rebuild_pr_body(
        header="",
        content="Main content here.",
        footer="Closes #123",
    )
    assert result.startswith("Main content here.")
    assert "---" in result
    assert "Closes #123" in result


def test_rebuild_pr_body_no_footer() -> None:
    """Test rebuilding without footer."""
    result = rebuild_pr_body(
        header="**Plan:** #123\n\n",
        content="Main content here.",
        footer="",
    )
    assert "**Plan:** #123" in result
    assert "Main content here." in result
    assert "---" not in result


def test_rebuild_pr_body_content_only() -> None:
    """Test rebuilding with content only."""
    result = rebuild_pr_body(
        header="",
        content="Just the content.",
        footer="",
    )
    assert result == "Just the content."


def test_rebuild_pr_body_preserves_structure_order() -> None:
    """Test that header comes before content which comes before footer."""
    result = rebuild_pr_body(
        header="**Plan:** #123\n\n",
        content="Main content here.",
        footer="Footer text",
    )
    header_pos = result.find("**Plan:**")
    content_pos = result.find("Main content")
    footer_pos = result.find("Footer text")
    assert header_pos < content_pos < footer_pos


# ============================================================================
# extract_footer_from_body Tests (existing function)
# ============================================================================


def test_extract_footer_from_body_with_footer() -> None:
    """Test extraction of footer section."""
    body = "Main content\n\n---\n\nCloses #123\n\nCheckout instructions"
    footer = extract_footer_from_body(body)
    assert footer is not None
    assert "Closes #123" in footer


def test_extract_footer_from_body_no_footer() -> None:
    """Test when there's no footer."""
    body = "Just content with no delimiter."
    footer = extract_footer_from_body(body)
    assert footer is None


# ============================================================================
# Round-trip Tests
# ============================================================================


def test_roundtrip_header_content_footer() -> None:
    """Test that extract + rebuild preserves the structure."""
    original = "**Plan:** #123\n\nMain description.\n\n---\nCloses #123\nCheckout instructions"
    header = extract_header_from_body(original)
    footer = extract_footer_from_body(original)
    content = extract_main_content(original)

    rebuilt = rebuild_pr_body(
        header=header,
        content=content,
        footer=footer if footer else "",
    )

    # Verify key parts are present
    assert "**Plan:** #123" in rebuilt
    assert "Main description." in rebuilt
    assert "---" in rebuilt
    assert "Closes #123" in rebuilt
