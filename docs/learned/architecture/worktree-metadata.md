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

**File**: `src/erk/core/worktree_metadata.py`

```python
# Remove worktree metadata (called when worktree deleted)
remove_worktree_metadata(repo_dir, worktree_name)
```

## Subdirectory Navigation Patterns

Navigation commands can preserve the user's relative position within a worktree.

### Relative Path Pattern (checkout, up, down)

Navigation commands preserve the user's relative position by:

1. **Computing relative path from current worktree root to cwd**

   ```python
   # Get current position relative to worktree root
   current_worktree_root = find_worktree_for_path(ctx.cwd)
   relative_position = ctx.cwd.relative_to(current_worktree_root)
   ```

2. **Applying that path to target worktree**

   ```python
   # Navigate to same relative position in target
   target_path = target_worktree_root / relative_position
   ```

3. **Falling back to worktree root if path doesn't exist**

   ```python
   # Fall back if the relative path doesn't exist in target
   if target_path.exists():
       final_destination = target_path
   else:
       final_destination = target_worktree_root
   ```

This pattern allows users to stay in `src/components/` when switching worktrees, rather than always landing at the worktree root.

### Implementation Notes

- Use `render_activation_script()` in `activation.py` for script generation
- The computed path should be validated before navigation
- Log the fallback case so users understand why they landed at root

## Related Topics

- [Template Variables](../cli/template-variables.md) - Variables available in configs
- [Shell Integration Patterns](shell-integration-patterns.md) - Script generation for shell commands
