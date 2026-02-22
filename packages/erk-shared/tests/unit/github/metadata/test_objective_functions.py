"""Tests for objective metadata functions in core.py.

Tests the 4 new functions:
- create_objective_header_block
- render_objective_body_block
- format_objective_content_comment
- update_objective_header_comment_id
"""

import pytest

from erk_shared.gateway.github.metadata.core import (
    create_objective_header_block,
    format_objective_content_comment,
    render_metadata_block,
    render_objective_body_block,
    update_objective_header_comment_id,
)


class TestCreateObjectiveHeaderBlock:
    """Test create_objective_header_block creates valid metadata blocks."""

    def test_creates_block_with_required_fields(self) -> None:
        """Creates block with created_at, created_by, and null comment_id."""
        block = create_objective_header_block(
            created_at="2025-11-25T14:37:43+00:00",
            created_by="testuser",
            objective_comment_id=None,
            slug=None,
        )

        assert block.key == "objective-header"
        assert block.data["created_at"] == "2025-11-25T14:37:43+00:00"
        assert block.data["created_by"] == "testuser"
        assert block.data["objective_comment_id"] is None
        assert "slug" not in block.data

    def test_creates_block_with_comment_id(self) -> None:
        """Creates block with non-null objective_comment_id."""
        block = create_objective_header_block(
            created_at="2025-11-25T14:37:43+00:00",
            created_by="testuser",
            objective_comment_id=12345,
            slug=None,
        )

        assert block.data["objective_comment_id"] == 12345

    def test_creates_block_with_slug(self) -> None:
        """Creates block with slug field when provided."""
        block = create_objective_header_block(
            created_at="2025-11-25T14:37:43+00:00",
            created_by="testuser",
            objective_comment_id=None,
            slug="build-auth-system",
        )

        assert block.data["slug"] == "build-auth-system"

    def test_creates_block_with_slug_renders_to_metadata(self) -> None:
        """Block with slug renders slug into metadata block string."""
        block = create_objective_header_block(
            created_at="2025-11-25T14:37:43+00:00",
            created_by="testuser",
            objective_comment_id=None,
            slug="refactor-gateway",
        )

        rendered = render_metadata_block(block)
        assert "slug: refactor-gateway" in rendered

    def test_block_renders_to_valid_metadata(self) -> None:
        """Block can be rendered into a valid metadata block string."""
        block = create_objective_header_block(
            created_at="2025-11-25T14:37:43+00:00",
            created_by="testuser",
            objective_comment_id=None,
            slug=None,
        )

        rendered = render_metadata_block(block)
        assert "objective-header" in rendered
        assert "created_at:" in rendered
        assert "created_by: testuser" in rendered

    def test_rejects_empty_created_at(self) -> None:
        """Empty created_at is rejected by schema validation."""
        with pytest.raises(ValueError, match="created_at must not be empty"):
            create_objective_header_block(
                created_at="",
                created_by="testuser",
                objective_comment_id=None,
                slug=None,
            )

    def test_rejects_empty_created_by(self) -> None:
        """Empty created_by is rejected by schema validation."""
        with pytest.raises(ValueError, match="created_by must not be empty"):
            create_objective_header_block(
                created_at="2025-11-25T14:37:43+00:00",
                created_by="",
                objective_comment_id=None,
                slug=None,
            )


class TestRenderObjectiveBodyBlock:
    """Test render_objective_body_block wraps content in metadata block."""

    def test_wraps_content_in_objective_body_block(self) -> None:
        """Content is wrapped in objective-body metadata block markers."""
        result = render_objective_body_block("# My Objective\n\nSome content.")

        assert "<!-- erk:metadata-block:objective-body -->" in result
        assert "<!-- /erk:metadata-block:objective-body -->" in result
        assert "# My Objective" in result
        assert "Some content." in result

    def test_includes_collapsible_details(self) -> None:
        """Output includes collapsible <details open> wrapper."""
        result = render_objective_body_block("Content here")

        assert "<details open>" in result
        assert "<summary><strong>Objective</strong></summary>" in result
        assert "</details>" in result

    def test_includes_machine_generated_warning(self) -> None:
        """Output includes machine-generated warning comment."""
        result = render_objective_body_block("Content")

        assert "Machine-generated" in result


class TestFormatObjectiveContentComment:
    """Test format_objective_content_comment wraps content for first comment."""

    def test_wraps_content_in_objective_body_block(self) -> None:
        """Content is wrapped in objective-body metadata block."""
        result = format_objective_content_comment("# My Objective\n\nGoals here.")

        assert "objective-body" in result
        assert "# My Objective" in result
        assert "Goals here." in result

    def test_strips_whitespace(self) -> None:
        """Leading/trailing whitespace is stripped from content."""
        result = format_objective_content_comment("  \n# Objective\n\nContent\n  \n")

        assert "# Objective" in result
        assert "Content" in result

    def test_preserves_internal_formatting(self) -> None:
        """Internal markdown formatting is preserved."""
        content = "# Title\n\n## Section 1\n\n- Item 1\n- Item 2\n\n## Section 2\n\nParagraph."
        result = format_objective_content_comment(content)

        assert "## Section 1" in result
        assert "- Item 1" in result
        assert "## Section 2" in result


class TestUpdateObjectiveHeaderCommentId:
    """Test update_objective_header_comment_id updates the comment ID field."""

    def _make_objective_header_body(self, *, comment_id: int | None) -> str:
        """Create a test issue body with objective-header metadata block."""
        block = create_objective_header_block(
            created_at="2025-11-25T14:37:43+00:00",
            created_by="testuser",
            objective_comment_id=comment_id,
            slug=None,
        )
        return render_metadata_block(block)

    def test_updates_null_comment_id(self) -> None:
        """Updates objective_comment_id from null to a value."""
        body = self._make_objective_header_body(comment_id=None)
        assert "objective_comment_id: null" in body

        updated = update_objective_header_comment_id(body, 98765)

        assert "objective_comment_id: 98765" in updated
        assert "objective_comment_id: null" not in updated

    def test_updates_existing_comment_id(self) -> None:
        """Updates objective_comment_id from one value to another."""
        body = self._make_objective_header_body(comment_id=11111)

        updated = update_objective_header_comment_id(body, 22222)

        assert "objective_comment_id: 22222" in updated
        assert "objective_comment_id: 11111" not in updated

    def test_preserves_other_fields(self) -> None:
        """Other fields in the header are preserved after update."""
        body = self._make_objective_header_body(comment_id=None)

        updated = update_objective_header_comment_id(body, 12345)

        assert "created_at:" in updated
        assert "created_by: testuser" in updated

    def test_raises_on_missing_block(self) -> None:
        """Raises ValueError when objective-header block not found."""
        body = "This is just regular text."

        with pytest.raises(ValueError, match="objective-header block not found"):
            update_objective_header_comment_id(body, 12345)
