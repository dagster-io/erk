"""Discriminated union types for Git worktree operations.

WorktreeAdded | WorktreeAddError and WorktreeRemoved | WorktreeRemoveError follow
the NonIdealState pattern established by PushResult | PushError in remote_ops/types.py.
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



@dataclass(frozen=True)
class WorktreeRemoved:
    """Success result from removing a worktree."""


@dataclass(frozen=True)
class WorktreeRemoveError:
    """Error result from removing a worktree."""

    message: str

    @property
    def error_type(self) -> str:
        return "worktree-remove-failed"
