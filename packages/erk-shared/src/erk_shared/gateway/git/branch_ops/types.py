"""Discriminated union types for Git branch operations.

BranchCreated | BranchCreateError follows the NonIdealState pattern
established by MergeResult | MergeError.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BranchCreated:
    """Success result from creating a branch."""


@dataclass(frozen=True)
class BranchCreateError:
    """Error result from creating a branch. Implements NonIdealState."""

    message: str

    @property
    def error_type(self) -> str:
        return "branch-create-failed"
