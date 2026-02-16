"""Shared frontmatter parsing for markdown files.

This module provides a unified frontmatter parsing function used by
both the review system and agent documentation validation.
"""

from dataclasses import dataclass

import frontmatter


@dataclass(frozen=True)
class FrontmatterParseResult:
    """Result of parsing YAML frontmatter from markdown content.

    Attributes:
        metadata: Parsed YAML dictionary, or None if parsing failed.
        body: Content after the frontmatter (always populated).
        error: Error message if parsing failed, None otherwise.
    """

    metadata: dict[str, object] | None
    body: str
    error: str | None

    @property
    def is_valid(self) -> bool:
        """Return True if frontmatter was successfully parsed."""
        return self.metadata is not None


def parse_markdown_frontmatter(content: str) -> FrontmatterParseResult:
    """Parse YAML frontmatter from markdown content.

    Uses python-frontmatter library for robust parsing. Distinguishes between:
    - No frontmatter (content doesn't start with ---)
    - Invalid YAML syntax
    - Non-dict YAML (list or scalar at top level)

    Args:
        content: The markdown file content.

    Returns:
        FrontmatterParseResult with parsed metadata, body text, and any error.
    """
    # Check if content has frontmatter delimiters before parsing
    has_frontmatter_delimiters = content.startswith("---")

    try:
        post = frontmatter.loads(content)
    except Exception as e:
        return FrontmatterParseResult(
            metadata=None,
            body=content,
            error=f"Invalid YAML: {e}",
        )

    # Check if metadata is a dict (frontmatter library stores non-dict YAML differently)
    if not isinstance(post.metadata, dict):
        return FrontmatterParseResult(
            metadata=None,
            body=post.content,
            error="Frontmatter is not a valid YAML mapping",
        )

    # Distinguish between "no frontmatter" vs "frontmatter was non-dict YAML"
    # When frontmatter library encounters non-dict YAML, it returns empty metadata
    if not post.metadata:
        if has_frontmatter_delimiters:
            return FrontmatterParseResult(
                metadata=None,
                body=post.content,
                error="Frontmatter is not a valid YAML mapping",
            )
        return FrontmatterParseResult(
            metadata=None,
            body=content,
            error="No frontmatter found",
        )

    return FrontmatterParseResult(
        metadata=dict(post.metadata),
        body=post.content,
        error=None,
    )
