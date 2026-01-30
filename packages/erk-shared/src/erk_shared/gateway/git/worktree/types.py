"""Discriminated union types for Git worktree operations.

WorktreeAdded | WorktreeAddError follows the NonIdealState pattern
established by MergeResult | MergeError.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WorktreeAdded:
    """Success result from adding a worktree."""


@dataclass(frozen=True)
class WorktreeAddError:
    """Error result from adding a worktree. Implements NonIdealState."""

    message: str

    @property
    def error_type(self) -> str:
        return "worktree-add-failed"
