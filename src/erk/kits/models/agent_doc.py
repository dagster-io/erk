"""Models for agent documentation frontmatter.

This module defines the frontmatter schema for agent documentation files.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Tripwire:
    """A single action-triggered rule.

    Tripwires are "if you're about to do X, consult Y" rules that detect
    action patterns and route agents to documentation before mistakes happen.

    Attributes:
        action: The action pattern that triggers (gerund phrase, e.g., "writing to /tmp/").
        warning: Brief explanation of why and what to do instead.
    """

    action: str
    warning: str


@dataclass(frozen=True)
class AgentDocFrontmatter:
    """Parsed frontmatter from an agent documentation file.

    Attributes:
        title: Human-readable document title.
        read_when: List of conditions/tasks when agent should read this doc.
        tripwires: List of action-triggered rules defined in this doc.
    """

    title: str
    read_when: list[str]
    tripwires: list[Tripwire] = field(default_factory=list)

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
