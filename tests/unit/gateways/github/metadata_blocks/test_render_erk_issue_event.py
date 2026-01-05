"""Tests for render_erk_issue_event function."""

from erk_shared.github.metadata_blocks import (
    create_implementation_status_block,
    render_erk_issue_event,
)


def test_render_erk_issue_event_with_all_parameters() -> None:
    """Test render_erk_issue_event with title, metadata, and description."""
    block = create_implementation_status_block(
        status="in_progress",
        completed_steps=3,
        total_steps=5,
        timestamp="2025-11-22T12:00:00Z",
        summary="Phase 1 complete",
    )

    comment = render_erk_issue_event(
        title="✓ Step 3/5 completed",
        metadata=block,
        description="Next: implement feature X",
    )

    # Verify structure
    assert comment.startswith("✓ Step 3/5 completed\n\n")
    assert "<!-- erk:metadata-block:erk-implementation-status -->" in comment
    assert "\n---\n\nNext: implement feature X" in comment

    # Verify format: title -> blank -> metadata -> blank -> separator -> blank -> description
    lines = comment.split("\n")
    assert lines[0] == "✓ Step 3/5 completed"
    assert lines[1] == ""  # Blank line after title
    # Metadata block appears next
    separator_idx = lines.index("---")
    assert lines[separator_idx - 1] == ""  # Blank line before separator
    assert lines[separator_idx + 1] == ""  # Blank line after separator
    assert lines[separator_idx + 2] == "Next: implement feature X"


def test_render_erk_issue_event_with_empty_description() -> None:
    """Test render_erk_issue_event with empty description (optional parameter)."""
    block = create_implementation_status_block(
        status="complete",
        completed_steps=5,
        total_steps=5,
        timestamp="2025-11-22T12:00:00Z",
    )

    comment = render_erk_issue_event(
        title="✅ Implementation complete",
        metadata=block,
        description="",
    )

    # Verify structure: title -> blank -> metadata -> blank -> separator -> blank (no description)
    assert comment.startswith("✅ Implementation complete\n\n")
    assert "<!-- erk:metadata-block:erk-implementation-status -->" in comment
    assert comment.endswith("---\n")

    # Ensure no description text after separator
    lines = comment.split("\n")
    separator_idx = lines.index("---")
    # Last line should be blank (after separator)
    assert len(lines) == separator_idx + 2
    assert lines[-1] == ""


def test_render_erk_issue_event_markdown_structure() -> None:
    """Test render_erk_issue_event produces valid markdown structure."""
    block = create_implementation_status_block(
        status="in_progress",
        completed_steps=2,
        total_steps=4,
        timestamp="2025-11-22T12:00:00Z",
    )

    comment = render_erk_issue_event(
        title="Progress Update",
        metadata=block,
        description="Working on implementation",
    )

    # Verify blank lines are preserved for markdown rendering
    lines = comment.split("\n")

    # Title at start
    assert lines[0] == "Progress Update"
    assert lines[1] == ""  # Blank after title

    # Metadata block appears (starts with comment)
    metadata_start = next(i for i, line in enumerate(lines) if "<!-- WARNING:" in line)
    assert lines[metadata_start - 1] == ""  # Blank before metadata

    # Separator exists with blank lines around it
    separator_idx = lines.index("---")
    assert lines[separator_idx - 1] == ""  # Blank before separator
    assert lines[separator_idx + 1] == ""  # Blank after separator

    # Description after separator
    assert lines[separator_idx + 2] == "Working on implementation"
