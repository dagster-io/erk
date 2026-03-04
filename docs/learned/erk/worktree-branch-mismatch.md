---
title: Worktree Branch Mismatch Handling
read_when:
  - "debugging erk up/down navigation failures"
  - "understanding how erk handles manual git checkout in worktrees"
  - "working with find_worktree_for_branch_or_path()"
tripwires:
  - action: "using find_worktree_for_branch() alone for stack navigation"
    warning: "Always use find_worktree_for_branch_or_path() for stack navigation, not find_worktree_for_branch() alone. The path-based fallback handles cases where users ran manual git checkout in a worktree."
---

# Worktree Branch Mismatch Handling

## The Problem

When a user manually runs `git checkout other-branch` inside a worktree slot, the worktree's actual branch diverges from what erk expects. Subsequent `erk up` or `erk down` navigation fails because `find_worktree_for_branch()` looks for an exact branch match in the git worktree registry and finds nothing.

## The Solution

<!-- Source: src/erk/cli/commands/navigation_helpers.py, find_worktree_for_branch_or_path -->

`find_worktree_for_branch_or_path()` in `src/erk/cli/commands/navigation_helpers.py` implements a two-stage lookup:

1. **Exact branch match**: Try `find_worktree_for_branch()` first. If a worktree has the expected branch checked out, return it with `needs_checkout=False`.

2. **Path-based fallback**: If no exact match, compute the expected worktree path from the branch name (via `sanitize_worktree_name()` + `worktree_path_for()`), and check if any worktree exists at that path regardless of what branch it has checked out. If found, return it with `needs_checkout=True`.

## The WorktreeLookupResult Type

<!-- Source: src/erk/cli/commands/navigation_helpers.py, WorktreeLookupResult -->

`WorktreeLookupResult` in `src/erk/cli/commands/navigation_helpers.py` is a frozen dataclass with `path: Path | None` and `needs_checkout: bool` fields.

| `path`   | `needs_checkout` | Meaning                                               |
| -------- | ---------------- | ----------------------------------------------------- |
| `None`   | `False`          | No worktree found at all                              |
| `<path>` | `False`          | Worktree found with correct branch checked out        |
| `<path>` | `True`           | Worktree exists at expected path but has wrong branch |

When `needs_checkout=True`, the activation script includes a `git checkout <expected-branch>` command to restore the correct branch before activating the worktree.

## Usage in Navigation

Both `resolve_up_navigation()` and `resolve_down_navigation()` call `find_worktree_for_branch_or_path()` to locate worktrees for target branches. The orchestrator layer then handles the checkout if `needs_checkout=True`.

## Historical Context

- PR #8651 fixed this issue for the root worktree
- PR #8693 generalized the fix to non-root worktrees using the two-stage lookup pattern

## Implementation Reference

| Function / Type                                              | File                                         |
| ------------------------------------------------------------ | -------------------------------------------- |
| `WorktreeLookupResult`, `find_worktree_for_branch_or_path()` | `src/erk/cli/commands/navigation_helpers.py` |
| `resolve_up_navigation()`, `resolve_down_navigation()`       | `src/erk/cli/commands/navigation_helpers.py` |
