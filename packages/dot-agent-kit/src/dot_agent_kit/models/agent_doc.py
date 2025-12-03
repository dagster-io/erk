"""Models for agent documentation frontmatter.

This module defines the frontmatter schema for agent documentation files.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentDocFrontmatter:
    """Parsed frontmatter from an agent documentation file.

    Attributes:
        title: Human-readable document title.
        read_when: List of conditions/tasks when agent should read this doc.
    """

    title: str
    read_when: list[str]

    def is_valid(self) -> bool:
        """Check if this frontmatter has all required fields."""
        return bool(self.title) and len(self.read_when) > 0


@dataclass(frozen=True)
class AgentDocValidationResult:
    """Result of validating a single agent doc file.

    Attributes:
        file_path: Relative path to the file from docs/agent/.
        frontmatter: Parsed frontmatter, or None if parsing failed.
        errors: List of validation errors.
    """

    file_path: str
    frontmatter: AgentDocFrontmatter | None
    errors: list[str]

    @property
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return len(self.errors) == 0 and self.frontmatter is not None
