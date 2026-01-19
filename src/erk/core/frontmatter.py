"""Shared frontmatter parsing for markdown files.

This module provides a unified interface for parsing YAML frontmatter from
markdown content. Domain-specific validation is handled by callers.
"""

from dataclasses import dataclass

import frontmatter


@dataclass(frozen=True)
class FrontmatterParseResult:
    """Result of parsing frontmatter from markdown content.

    Attributes:
        metadata: Parsed frontmatter dict, or None if parsing failed.
        body: Content after the frontmatter (always present).
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

    Handles these cases:
    - Valid frontmatter: returns metadata dict and body
    - No frontmatter: returns error
    - Invalid YAML: returns error
    - Non-dict frontmatter: returns error
    - Empty frontmatter with delimiters: returns error

    Args:
        content: The markdown file content.

    Returns:
        FrontmatterParseResult with metadata, body, and error fields.
    """
    has_frontmatter_delimiters = content.startswith("---")

    try:
        post = frontmatter.loads(content)
    except Exception as e:
        return FrontmatterParseResult(
            metadata=None,
            body=content,
            error=f"Invalid YAML: {e}",
        )

    if not isinstance(post.metadata, dict):
        return FrontmatterParseResult(
            metadata=None,
            body=post.content,
            error="Frontmatter is not a valid YAML mapping",
        )

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
