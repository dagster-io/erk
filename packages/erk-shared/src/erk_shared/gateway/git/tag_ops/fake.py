"""Fake implementation of Git tag operations for testing."""

from __future__ import annotations

from pathlib import Path

from erk_shared.gateway.git.tag_ops.abc import GitTagOps


class FakeGitTagOps(GitTagOps):
    """In-memory fake implementation of Git tag operations.

    This fake accepts pre-configured state in its constructor and tracks
    mutations for test assertions.

    Constructor Injection:
    ---------------------
    - existing_tags: Set of tag names that exist in the repository

    Mutation Tracking:
    -----------------
    This fake tracks mutations for test assertions via read-only properties:
    - created_tags: List of (tag_name, message) tuples from create_tag()
    - pushed_tags: List of (remote, tag_name) tuples from push_tag()
    """

    def __init__(
        self,
        *,
        existing_tags: set[str] | None = None,
    ) -> None:
        """Create FakeGitTagOps with pre-configured state.

        Args:
            existing_tags: Set of tag names that exist in the repository
        """
        self._existing_tags: set[str] = existing_tags if existing_tags is not None else set()

        # Mutation tracking
        self._created_tags: list[tuple[str, str]] = []  # (tag_name, message)
        self._pushed_tags: list[tuple[str, str]] = []  # (remote, tag_name)

    # ============================================================================
    # Query Operations
    # ============================================================================

    def tag_exists(self, repo_root: Path, tag_name: str) -> bool:
        """Check if a git tag exists in the fake state."""
        return tag_name in self._existing_tags

    # ============================================================================
    # Mutation Operations
    # ============================================================================

    def create_tag(self, repo_root: Path, tag_name: str, message: str) -> None:
        """Create an annotated git tag (mutates internal state)."""
        self._existing_tags.add(tag_name)
        self._created_tags.append((tag_name, message))

    def push_tag(self, repo_root: Path, remote: str, tag_name: str) -> None:
        """Push a tag to a remote (tracks mutation)."""
        self._pushed_tags.append((remote, tag_name))

    # ============================================================================
    # Mutation Tracking Properties
    # ============================================================================

    @property
    def created_tags(self) -> list[tuple[str, str]]:
        """Get list of tags created during test.

        Returns list of (tag_name, message) tuples.
        This property is for test assertions only.
        """
        return self._created_tags.copy()

    @property
    def pushed_tags(self) -> list[tuple[str, str]]:
        """Get list of tags pushed during test.

        Returns list of (remote, tag_name) tuples.
        This property is for test assertions only.
        """
        return self._pushed_tags.copy()

    # ============================================================================
    # Link Mutation Tracking (for integration with FakeGit)
    # ============================================================================

    def link_mutation_tracking(
        self,
        *,
        existing_tags: set[str],
        created_tags: list[tuple[str, str]],
        pushed_tags: list[tuple[str, str]],
    ) -> None:
        """Link this fake's mutation tracking to FakeGit's tracking lists.

        This allows FakeGit to expose tag operations mutations through its
        own properties while delegating to this subgateway.

        Args:
            existing_tags: FakeGit's _existing_tags set
            created_tags: FakeGit's _created_tags list
            pushed_tags: FakeGit's _pushed_tags list
        """
        self._existing_tags = existing_tags
        self._created_tags = created_tags
        self._pushed_tags = pushed_tags
