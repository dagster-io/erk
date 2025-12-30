"""Models for agent documentation frontmatter.

This module defines the frontmatter schema for agent documentation files.
"""

from dataclasses import dataclass


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
    tripwires: list[Tripwire]

    def is_valid(self) -> bool:
        """Check if this frontmatter has all required fields."""
        return bool(self.title) and len(self.read_when) > 0


@dataclass(frozen=True)
class AgentDocValidationResult:
    """Result of validating a single agent doc file.

    Attributes:
        file_path: Relative path to the file from docs/learned/.
        frontmatter: Parsed frontmatter, or None if parsing failed.
        errors: List of validation errors.
    """

    file_path: str
    frontmatter: AgentDocFrontmatter | None
    errors: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return len(self.errors) == 0 and self.frontmatter is not None


@dataclass(frozen=True)
class DocInfo:
    """Information about a documentation file.

    Attributes:
        rel_path: Relative path from docs/learned/.
        frontmatter: Parsed frontmatter.
    """

    rel_path: str
    frontmatter: AgentDocFrontmatter


@dataclass(frozen=True)
class CategoryInfo:
    """Information about a documentation category (subdirectory).

    Attributes:
        name: Category directory name.
        docs: List of documents in this category.
    """

    name: str
    docs: tuple[DocInfo, ...]


@dataclass(frozen=True)
class SyncResult:
    """Result of syncing agent documentation indexes.

    Attributes:
        created: List of index files that were created.
        updated: List of index files that were updated.
        unchanged: List of index files that didn't need changes.
        skipped_invalid: Number of docs skipped due to invalid frontmatter.
        tripwires_count: Number of tripwires collected and generated.
    """

    created: tuple[str, ...]
    updated: tuple[str, ...]
    unchanged: tuple[str, ...]
    skipped_invalid: int
    tripwires_count: int


@dataclass(frozen=True)
class CollectedTripwire:
    """A tripwire collected from an agent documentation file.

    Attributes:
        action: The action pattern that triggers.
        warning: Brief explanation of why and what to do instead.
        doc_path: Relative path from docs/learned/.
        doc_title: Human-readable document title.
    """

    action: str
    warning: str
    doc_path: str
    doc_title: str
