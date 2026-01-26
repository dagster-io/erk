"""Branch metadata dataclass for Graphite integration."""

from __future__ import annotations

import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class BranchMetadata:
    """Metadata for a single gt-tracked branch.

    This is used by the gt commands to provide machine-readable branch information.

    Attributes:
        name: Branch name
        parent: Parent branch name, or None for trunk
        children: List of child branch names
        is_trunk: True if this is the trunk branch (main/master)
        commit_sha: Actual git commit SHA from git branch head
        tracked_revision: Graphite's cached branchRevision from .graphite_cache_persist
            (may differ from commit_sha after rebase/restack)
    """

    name: str
    parent: str | None
    children: list[str]
    is_trunk: bool
    commit_sha: str | None
    tracked_revision: str | None = None

    @staticmethod
    def trunk(
        name: str,
        *,
        children: list[str] | None = None,
        commit_sha: str | None = None,
        tracked_revision: str | None = None,
    ) -> BranchMetadata:
        """Create a trunk branch (main/master/develop).

        Args:
            name: Branch name
            children: List of child branch names (defaults to empty list)
            commit_sha: Commit SHA (defaults to random 12-char hex)
            tracked_revision: Graphite's cached branchRevision (defaults to commit_sha)

        Returns:
            BranchMetadata with parent=None and is_trunk=True
        """
        sha = commit_sha if commit_sha is not None else secrets.token_hex(6)
        return BranchMetadata(
            name=name,
            parent=None,
            children=children if children is not None else [],
            is_trunk=True,
            commit_sha=sha,
            tracked_revision=tracked_revision if tracked_revision is not None else sha,
        )

    @staticmethod
    def branch(
        name: str,
        parent: str,
        *,
        children: list[str] | None = None,
        commit_sha: str | None = None,
        tracked_revision: str | None = None,
    ) -> BranchMetadata:
        """Create a regular feature branch.

        Args:
            name: Branch name
            parent: Parent branch name
            children: List of child branch names (defaults to empty list)
            commit_sha: Commit SHA (defaults to random 12-char hex)
            tracked_revision: Graphite's cached branchRevision (defaults to commit_sha)

        Returns:
            BranchMetadata with is_trunk=False
        """
        sha = commit_sha if commit_sha is not None else secrets.token_hex(6)
        return BranchMetadata(
            name=name,
            parent=parent,
            children=children if children is not None else [],
            is_trunk=False,
            commit_sha=sha,
            tracked_revision=tracked_revision if tracked_revision is not None else sha,
        )
