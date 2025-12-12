"""Branch metadata dataclass for Graphite integration."""

import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class BranchMetadata:
    """Metadata for a single gt-tracked branch.

    This is used by the gt commands to provide machine-readable branch information.
    """

    name: str
    parent: str | None
    children: list[str]
    is_trunk: bool
    commit_sha: str | None

    @staticmethod
    def trunk(
        name: str,
        *,
        children: list[str] | None = None,
        commit_sha: str | None = None,
    ) -> "BranchMetadata":
        """Create a trunk branch (main/master/develop).

        Args:
            name: Branch name
            children: List of child branch names (defaults to empty list)
            commit_sha: Commit SHA (defaults to random 12-char hex)

        Returns:
            BranchMetadata with parent=None and is_trunk=True
        """
        return BranchMetadata(
            name=name,
            parent=None,
            children=children if children is not None else [],
            is_trunk=True,
            commit_sha=commit_sha if commit_sha is not None else secrets.token_hex(6),
        )

    @staticmethod
    def branch(
        name: str,
        parent: str,
        *,
        children: list[str] | None = None,
        commit_sha: str | None = None,
    ) -> "BranchMetadata":
        """Create a regular feature branch.

        Args:
            name: Branch name
            parent: Parent branch name
            children: List of child branch names (defaults to empty list)
            commit_sha: Commit SHA (defaults to random 12-char hex)

        Returns:
            BranchMetadata with is_trunk=False
        """
        return BranchMetadata(
            name=name,
            parent=parent,
            children=children if children is not None else [],
            is_trunk=False,
            commit_sha=commit_sha if commit_sha is not None else secrets.token_hex(6),
        )
