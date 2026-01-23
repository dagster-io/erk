"""Tests for shared frontmatter parsing module."""

from erk.core.frontmatter import FrontmatterParseResult, parse_markdown_frontmatter


def test_valid_frontmatter() -> None:
    """Parse valid YAML frontmatter from markdown."""
    content = """\
---
name: Test Review
paths:
  - "**/*.py"
marker: "<!-- test -->"
---

Body content here.
"""
    result = parse_markdown_frontmatter(content)

    assert result.error is None
    assert result.metadata is not None
    assert result.metadata["name"] == "Test Review"
    assert result.metadata["paths"] == ["**/*.py"]
    assert result.metadata["marker"] == "<!-- test -->"
    assert result.body.strip() == "Body content here."
    assert result.is_valid is True


def test_no_frontmatter() -> None:
    """Return error when no frontmatter found."""
    content = "Just plain markdown without frontmatter."

    result = parse_markdown_frontmatter(content)

    assert result.metadata is None
    assert result.error == "No frontmatter found"
    assert result.body == content
    assert result.is_valid is False


def test_invalid_yaml() -> None:
    """Return error for invalid YAML."""
    content = """\
---
name: [unclosed bracket
---

Body.
"""
    result = parse_markdown_frontmatter(content)

    assert result.metadata is None
    assert result.error is not None
    assert "Invalid YAML" in result.error
    assert result.is_valid is False


def test_non_dict_frontmatter_list() -> None:
    """Return error when frontmatter is a list (not a dict)."""
    content = """\
---
- just
- a
- list
---

Body.
"""
    result = parse_markdown_frontmatter(content)

    assert result.metadata is None
    assert result.error is not None
    assert "not a valid YAML mapping" in result.error
    assert result.is_valid is False


def test_non_dict_frontmatter_scalar() -> None:
    """Return error when frontmatter is a scalar (not a dict)."""
    content = """\
---
just a string
---

Body.
"""
    result = parse_markdown_frontmatter(content)

    assert result.metadata is None
    assert result.error is not None
    assert "not a valid YAML mapping" in result.error
    assert result.is_valid is False


def test_empty_frontmatter_block() -> None:
    """Return error when frontmatter block exists but is empty."""
    content = """\
---
---

Body content.
"""
    result = parse_markdown_frontmatter(content)

    assert result.metadata is None
    assert result.error is not None
    assert "not a valid YAML mapping" in result.error
    assert result.is_valid is False


def test_frontmatter_with_complex_nested_structures() -> None:
    """Parse frontmatter with nested dicts and lists."""
    content = """\
---
title: Complex Doc
config:
  nested:
    key: value
    items:
      - one
      - two
      - three
  enabled: true
tags:
  - documentation
  - testing
---

Body text.
"""
    result = parse_markdown_frontmatter(content)

    assert result.error is None
    assert result.metadata is not None
    assert result.metadata["title"] == "Complex Doc"
    assert result.metadata["config"]["nested"]["key"] == "value"
    assert result.metadata["config"]["nested"]["items"] == ["one", "two", "three"]
    assert result.metadata["config"]["enabled"] is True
    assert result.metadata["tags"] == ["documentation", "testing"]
    assert result.body.strip() == "Body text."
    assert result.is_valid is True


def test_frontmatter_parse_result_dataclass() -> None:
    """Test FrontmatterParseResult dataclass properties."""
    # Valid result
    valid_result = FrontmatterParseResult(
        metadata={"key": "value"},
        body="body",
        error=None,
    )
    assert valid_result.is_valid is True

    # Invalid result
    invalid_result = FrontmatterParseResult(
        metadata=None,
        body="body",
        error="Some error",
    )
    assert invalid_result.is_valid is False


def test_frontmatter_with_multiline_strings() -> None:
    """Parse frontmatter with YAML multiline strings."""
    content = """\
---
title: Multiline Test
description: |
  This is a multiline
  description that spans
  multiple lines.
---

Body.
"""
    result = parse_markdown_frontmatter(content)

    assert result.error is None
    assert result.metadata is not None
    assert result.metadata["title"] == "Multiline Test"
    assert "This is a multiline" in result.metadata["description"]
    assert "multiple lines." in result.metadata["description"]
    assert result.is_valid is True


def test_frontmatter_with_special_characters() -> None:
    """Parse frontmatter with special characters in values."""
    content = """\
---
title: "Title with: colons"
marker: "<!-- special-chars: @#$% -->"
regex: "^foo.*bar$"
---

Body.
"""
    result = parse_markdown_frontmatter(content)

    assert result.error is None
    assert result.metadata is not None
    assert result.metadata["title"] == "Title with: colons"
    assert result.metadata["marker"] == "<!-- special-chars: @#$% -->"
    assert result.metadata["regex"] == "^foo.*bar$"
    assert result.is_valid is True
