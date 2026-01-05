"""Shared fixtures and helpers for workspace create tests."""

from datetime import datetime

from erk_shared.naming import WORKTREE_DATE_SUFFIX_FORMAT


def get_current_date_suffix() -> str:
    """Get the current date suffix for plan-derived worktrees."""
    return datetime.now().strftime(WORKTREE_DATE_SUFFIX_FORMAT)
