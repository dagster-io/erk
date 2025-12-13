"""Tests for frontmatter parsing."""

from erk.kits.io.frontmatter import (
    ArtifactFrontmatter,
    add_kit_to_frontmatter,
    parse_artifact_frontmatter,
    parse_user_metadata,
)


class TestParseArtifactFrontmatter:
    """Tests for parse_artifact_frontmatter function."""

    def test_returns_none_for_no_frontmatter(self) -> None:
        """Returns None when content has no frontmatter."""
        content = "# Just a heading\n\nSome content."
        result = parse_artifact_frontmatter(content)
        assert result is None

    def test_parses_kit_field_from_erk_namespace(self) -> None:
        """Parses kit field from erk namespace in frontmatter."""
        content = """---
name: my-command
erk:
  kit: erk
---

# Command content
"""
        result = parse_artifact_frontmatter(content)
        assert result is not None
        assert result.kit == "erk"
        assert result.name == "my-command"

    def test_handles_null_kit(self) -> None:
        """Handles erk.kit: null for local-only artifacts."""
        content = """---
name: local-command
erk:
  kit: null
---

# Local command
"""
        result = parse_artifact_frontmatter(content)
        assert result is not None
        assert result.kit is None
        assert result.name == "local-command"

    def test_extracts_description(self) -> None:
        """Extracts description field."""
        content = """---
name: test
description: This is a test command
---

# Content
"""
        result = parse_artifact_frontmatter(content)
        assert result is not None
        assert result.description == "This is a test command"

    def test_preserves_raw_data(self) -> None:
        """Preserves full raw dictionary for other fields."""
        content = """---
name: test
custom_field: custom_value
erk:
  kit: erk
---

# Content
"""
        result = parse_artifact_frontmatter(content)
        assert result is not None
        assert result.raw["custom_field"] == "custom_value"
        assert result.raw["name"] == "test"
        assert result.raw["erk"]["kit"] == "erk"

    def test_handles_empty_frontmatter(self) -> None:
        """Returns None for empty frontmatter."""
        content = """---
---

# Content
"""
        result = parse_artifact_frontmatter(content)
        assert result is None

    def test_removes_legacy_metadata(self) -> None:
        """Removes __dot_agent internal metadata."""
        content = """---
name: test
__dot_agent: internal_stuff
---

# Content
"""
        result = parse_artifact_frontmatter(content)
        assert result is not None
        assert "__dot_agent" not in result.raw


class TestAddKitToFrontmatter:
    """Tests for add_kit_to_frontmatter function."""

    def test_adds_kit_to_existing_frontmatter(self) -> None:
        """Adds kit field under erk namespace to existing frontmatter."""
        content = """---
name: my-command
description: A command
---

# Command content
"""
        result = add_kit_to_frontmatter(content, "erk")
        assert "erk:" in result
        assert "kit: erk" in result
        assert "name: my-command" in result

    def test_creates_frontmatter_if_missing(self) -> None:
        """Creates new frontmatter when none exists."""
        content = "# Just a heading\n\nSome content."
        result = add_kit_to_frontmatter(content, "gt")
        assert result.startswith("---\nerk:\n  kit: gt\n---\n")
        assert "# Just a heading" in result

    def test_updates_existing_kit_field(self) -> None:
        """Updates existing kit field value in erk namespace."""
        content = """---
name: my-command
erk:
  kit: old-kit
---

# Content
"""
        result = add_kit_to_frontmatter(content, "new-kit")
        assert "kit: new-kit" in result
        assert "kit: old-kit" not in result

    def test_preserves_content_after_frontmatter(self) -> None:
        """Preserves all content after frontmatter block."""
        content = """---
name: test
---

# Main heading

Some paragraph text.

## Another heading
"""
        result = add_kit_to_frontmatter(content, "erk")
        assert "# Main heading" in result
        assert "Some paragraph text." in result
        assert "## Another heading" in result

    def test_orders_erk_after_name_and_description(self) -> None:
        """Places erk namespace after name and description."""
        content = """---
description: A description
name: my-command
other: value
---

# Content
"""
        result = add_kit_to_frontmatter(content, "erk")
        # name should appear first, then description, then erk
        frontmatter_section = result.split("---")[1]
        lines = [line for line in frontmatter_section.strip().split("\n") if line.strip()]
        assert lines[0].startswith("name:")
        assert lines[1].startswith("description:")
        assert lines[2].startswith("erk:")


class TestParseUserMetadata:
    """Tests for parse_user_metadata function (backward compatibility)."""

    def test_returns_none_for_no_frontmatter(self) -> None:
        """Returns None when no frontmatter."""
        content = "# Just content"
        result = parse_user_metadata(content)
        assert result is None

    def test_returns_dict_with_all_fields(self) -> None:
        """Returns dictionary with all frontmatter fields."""
        content = """---
name: test
custom: value
erk:
  kit: erk
---

# Content
"""
        result = parse_user_metadata(content)
        assert result is not None
        assert result["name"] == "test"
        assert result["erk"]["kit"] == "erk"
        assert result["custom"] == "value"


class TestArtifactFrontmatterDataclass:
    """Tests for ArtifactFrontmatter dataclass."""

    def test_is_frozen(self) -> None:
        """Verifies dataclass is frozen (immutable)."""
        import pytest

        fm = ArtifactFrontmatter(name="test", description=None, kit="erk", raw={})
        # Attempting to modify should raise an error
        with pytest.raises(AttributeError):
            fm.name = "other"  # type: ignore[misc]
