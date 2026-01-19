"""Tests for shared frontmatter parsing."""

from erk.core.frontmatter import parse_markdown_frontmatter


def test_parse_valid_frontmatter() -> None:
    """Parse content with valid YAML frontmatter."""
    content = """\
---
title: Test Document
read_when:
  - "testing frontmatter"
---

Body content here.
"""
    result = parse_markdown_frontmatter(content)

    assert result.is_valid
    assert result.error is None
    assert result.metadata is not None
    assert result.metadata["title"] == "Test Document"
    assert result.metadata["read_when"] == ["testing frontmatter"]
    assert result.body == "Body content here."


def test_parse_no_frontmatter() -> None:
    """Return error when content has no frontmatter."""
    content = "Just plain markdown content."

    result = parse_markdown_frontmatter(content)

    assert not result.is_valid
    assert result.error == "No frontmatter found"
    assert result.metadata is None
    assert result.body == content


def test_parse_invalid_yaml() -> None:
    """Return error when frontmatter contains invalid YAML."""
    content = """\
---
title: [unclosed bracket
---

Body.
"""
    result = parse_markdown_frontmatter(content)

    assert not result.is_valid
    assert result.error is not None
    assert "Invalid YAML" in result.error
    assert result.metadata is None


def test_parse_non_dict_frontmatter() -> None:
    """Return error when frontmatter is not a dict (e.g., a list)."""
    content = """\
---
- item1
- item2
---

Body.
"""
    result = parse_markdown_frontmatter(content)

    assert not result.is_valid
    assert result.error == "Frontmatter is not a valid YAML mapping"
    assert result.metadata is None


def test_parse_empty_frontmatter_with_delimiters() -> None:
    """Return error when frontmatter delimiters exist but content is empty."""
    content = """\
---
---

Body content.
"""
    result = parse_markdown_frontmatter(content)

    assert not result.is_valid
    assert result.error == "Frontmatter is not a valid YAML mapping"
    assert result.metadata is None


def test_body_preserved_on_valid_parse() -> None:
    """Body content is correctly extracted after valid frontmatter."""
    content = """\
---
key: value
---

First paragraph.

Second paragraph.
"""
    result = parse_markdown_frontmatter(content)

    assert result.is_valid
    assert "First paragraph" in result.body
    assert "Second paragraph" in result.body


def test_body_preserved_on_invalid_parse() -> None:
    """Body content is returned even when parsing fails."""
    content = "Plain markdown without frontmatter."

    result = parse_markdown_frontmatter(content)

    assert not result.is_valid
    assert result.body == content


def test_metadata_is_dict_copy() -> None:
    """Metadata is a plain dict (not frontmatter library object)."""
    content = """\
---
name: Test
count: 42
---

Body.
"""
    result = parse_markdown_frontmatter(content)

    assert result.is_valid
    assert result.metadata is not None
    assert isinstance(result.metadata, dict)
    assert result.metadata["name"] == "Test"
    assert result.metadata["count"] == 42
