"""Shared validation functions for stack operations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ParentNotTrunkError:
    """Validation error when branch parent is not trunk."""

    current_branch: str
    parent_branch: str | None
    trunk_branch: str

    @property
    def message(self) -> str:
        return (
            f"Branch must be exactly one level up from {self.trunk_branch}\n"
            f"Current branch: {self.current_branch}\n"
            f"Parent branch: {self.parent_branch or 'unknown'} "
            f"(expected: {self.trunk_branch})\n\n"
            f"Please navigate to a branch that branches directly from "
            f"{self.trunk_branch}."
        )


def validate_parent_is_trunk(
    *,
    current_branch: str,
    parent_branch: str | None,
    trunk_branch: str,
) -> ParentNotTrunkError | None:
    """Validate that a branch's parent is trunk.

    Returns None if valid, ParentNotTrunkError if invalid.
    """
    if parent_branch != trunk_branch:
        return ParentNotTrunkError(
            current_branch=current_branch,
            parent_branch=parent_branch,
            trunk_branch=trunk_branch,
        )
    return None
