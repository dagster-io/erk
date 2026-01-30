"""Discriminated union types for Git worktree operations.

WorktreeAdded | WorktreeAddError follows the NonIdealState pattern
established by PushResult | PushError in remote_ops/types.py.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WorktreeAdded:
    """Success result from adding a worktree."""


@dataclass(frozen=True)
class WorktreeAddError:
    """Error: worktree add failed. Implements NonIdealState."""

    message: str

    @property
    def error_type(self) -> str:
        return "worktree-add-failed"
