"""Discriminated union types for Git branch operations.

BranchCreated | BranchAlreadyExists follows the NonIdealState pattern
established by PushResult | PushError in remote_ops/types.py.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BranchCreated:
    """Success result from creating a branch."""


@dataclass(frozen=True)
class BranchAlreadyExists:
    """Error: branch already exists. Implements NonIdealState."""

    branch_name: str
    message: str

    @property
    def error_type(self) -> str:
        return "branch-already-exists"
