---
title: Worktree Metadata Storage
read_when:
  - "storing per-worktree data"
  - "working with worktrees.toml"
  - "associating metadata with worktrees"
  - "implementing subdirectory navigation"
  - "preserving relative path on worktree switch"
---

# Worktree Metadata Storage

## Overview

Per-worktree metadata is stored in `~/.erk/repos/{repo}/worktrees.toml`. This file associates worktree names with metadata.

## File Location

```
~/.erk/repos/
└── {repo-name}/
    ├── config.toml      ← Repo-level configuration
    └── worktrees.toml   ← Per-worktree metadata
```

## API

**Utilities**: `src/erk/core/worktree_utils.py` — contains worktree lookup and navigation helpers (`find_current_worktree`, `compute_relative_path_in_worktree`, etc.).

## Subdirectory Navigation Patterns

Navigation commands can preserve the user's relative position within a worktree.

### Relative Path Pattern (checkout, up, down)

<!-- Source: src/erk/core/worktree_utils.py, find_worktree_containing_path and compute_relative_path_in_worktree -->

Navigation commands preserve the user's relative position through three steps:

1. **Compute relative path** from current worktree root to cwd using `find_worktree_containing_path()` and `Path.relative_to()`
2. **Apply that path** to the target worktree root
3. **Fall back to worktree root** if the relative path doesn't exist in the target

This pattern allows users to stay in `src/components/` when switching worktrees, rather than always landing at the worktree root.

### Implementation Notes

- Use `render_activation_script()` in `activation.py` for script generation
- The computed path should be validated before navigation
- Log the fallback case so users understand why they landed at root

## Related Topics

- [Template Variables](../cli/template-variables.md) - Variables available in configs
