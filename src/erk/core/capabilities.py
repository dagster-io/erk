"""Capability system for erk init.

Capabilities are optional features that can be installed via `erk init --capability <name>`.
Each capability knows how to detect if it's installed and how to install itself.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class CapabilityResult:
    """Result of a capability installation operation."""

    success: bool
    message: str


@dataclass(frozen=True)
class CapabilityArtifact:
    """Describes an artifact installed by a capability."""

    path: str  # Relative to repo_root, e.g., "docs/learned/"
    artifact_type: Literal["file", "directory"]


class Capability(ABC):
    """Abstract base class for erk capabilities.

    A capability is an optional feature that can be installed during `erk init`.
    Each capability must implement:
    - name: CLI-facing identifier
    - description: Short description for help text
    - is_installed(): Check if already installed
    - install(): Install the capability
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """CLI-facing identifier for this capability (e.g., 'learned-docs')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description for help text."""
        ...

    @property
    @abstractmethod
    def installation_check_description(self) -> str:
        """Human-readable description of what is_installed() checks.

        Example: "docs/learned/ directory exists"
        """
        ...

    @property
    @abstractmethod
    def artifacts(self) -> list[CapabilityArtifact]:
        """List of artifacts this capability installs.

        Returns:
            List of CapabilityArtifact describing files/directories created
        """
        ...

    @abstractmethod
    def is_installed(self, repo_root: Path) -> bool:
        """Check if this capability is already installed.

        Args:
            repo_root: Path to the repository root

        Returns:
            True if the capability is already installed
        """
        ...

    @abstractmethod
    def install(self, repo_root: Path) -> CapabilityResult:
        """Install this capability.

        Args:
            repo_root: Path to the repository root

        Returns:
            CapabilityResult with success status and message
        """
        ...


# =============================================================================
# Built-in Capabilities
# =============================================================================

LEARNED_DOCS_README = """\
---
title: "Learned Documentation Guide"
read_when:
  - "setting up learned docs"
  - "understanding learned docs structure"
  - "adding new documentation"
---

# Learned Documentation

This directory contains agent-discoverable documentation for AI assistants.

## Purpose

Learned docs provide structured guidance that AI agents can discover based on \
`read_when` conditions in frontmatter.

## Structure

Each markdown file requires YAML frontmatter:

- `title`: Document title (required)
- `read_when`: Conditions for when to read (required)
- `tripwires` (optional): Action-triggered rules

## Commands

- `erk docs sync` - Regenerate index files from frontmatter
- `erk docs validate` - Validate frontmatter

## Getting Started

1. Create markdown files with proper frontmatter
2. Organize related docs in subdirectories (categories)
3. Run `erk docs sync` to generate index files
"""

LEARNED_DOCS_INDEX = """\
<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Run 'erk docs sync' to regenerate this file from document frontmatter. -->

# Agent Documentation

<!-- This index is automatically populated by 'erk docs sync'. -->
<!-- It will list all categories and documents with their read_when conditions. -->

## Categories

<!-- Subdirectories will be listed here once created. -->

## Uncategorized

<!-- Top-level documents will be listed here. -->
<!-- Example: **[my-doc.md](my-doc.md)** — when to read condition 1, condition 2 -->
"""

LEARNED_DOCS_TRIPWIRES = """\
<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Run 'erk docs sync' to regenerate this file from document frontmatter. -->

# Tripwires

Action-triggered rules that fire when you're about to perform specific actions.

<!-- Tripwires are collected from the 'tripwires' frontmatter field in documents. -->
<!-- Each tripwire should follow this format in your document's frontmatter: -->
<!--
---
title: "My Document"
read_when:
  - "working on feature X"
tripwires:
  - trigger: "Before doing action Y"
    action: "Read this document first. Explains why Y needs special handling."
---
-->

<!-- Currently empty. Add tripwires to your documents and run 'erk docs sync'. -->
"""


class LearnedDocsCapability(Capability):
    """Capability for the learned-docs agent documentation system."""

    @property
    def name(self) -> str:
        return "learned-docs"

    @property
    def description(self) -> str:
        return "Agent documentation system"

    @property
    def installation_check_description(self) -> str:
        return "docs/learned/ directory exists"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        return [
            CapabilityArtifact(path="docs/learned/", artifact_type="directory"),
            CapabilityArtifact(path="docs/learned/README.md", artifact_type="file"),
            CapabilityArtifact(path="docs/learned/index.md", artifact_type="file"),
            CapabilityArtifact(path="docs/learned/tripwires.md", artifact_type="file"),
        ]

    def is_installed(self, repo_root: Path) -> bool:
        """Check if docs/learned/ directory exists."""
        return (repo_root / "docs" / "learned").exists()

    def install(self, repo_root: Path) -> CapabilityResult:
        """Create docs/learned/ directory with initial files."""
        docs_dir = repo_root / "docs" / "learned"
        if docs_dir.exists():
            return CapabilityResult(success=True, message="docs/learned/ already exists")

        docs_dir.mkdir(parents=True)
        (docs_dir / "README.md").write_text(LEARNED_DOCS_README, encoding="utf-8")
        (docs_dir / "index.md").write_text(LEARNED_DOCS_INDEX, encoding="utf-8")
        (docs_dir / "tripwires.md").write_text(LEARNED_DOCS_TRIPWIRES, encoding="utf-8")
        return CapabilityResult(
            success=True, message="Created docs/learned/ with README, index.md, tripwires.md"
        )


# =============================================================================
# Capability Registry (Lazy Initialization)
# =============================================================================


@cache
def _get_capability_registry() -> dict[str, Capability]:
    """Get capability registry (initialized on first call).

    Uses @cache for lazy initialization - built-in capabilities are only
    instantiated when first accessed, avoiding import-time side effects.
    """
    return {
        "learned-docs": LearnedDocsCapability(),
    }


def register_capability(cap: Capability) -> None:
    """Register a capability in the global registry.

    This function can be called to add custom capabilities after module import.

    Args:
        cap: The capability to register
    """
    _get_capability_registry()[cap.name] = cap


def get_capability(name: str) -> Capability | None:
    """Get a capability by name.

    Args:
        name: The capability name

    Returns:
        The capability if found, None otherwise
    """
    return _get_capability_registry().get(name)


def list_capabilities() -> list[Capability]:
    """Get all registered capabilities.

    Returns:
        List of all registered capabilities
    """
    return list(_get_capability_registry().values())
