---
title: Python pathlib Symlink Behavior
read_when:
  - Writing file validation code
  - Debugging unexpected path resolution behavior
  - Working with symlinked configuration files
last_audited: "2026-02-03"
audit_result: edited
---

# Python pathlib Symlink Behavior

## Key Behaviors

- `Path.exists()` follows symlinks — returns `True` if the **target** exists
- `Path.resolve()` follows symlinks — returns the canonical path
- Path arithmetic (`parent / "../foo"`) does NOT follow symlinks during construction, but `.exists()` and `.resolve()` will follow them later

## Anti-Pattern

When validating relative paths in symlinked files, `Path.exists()` may return `True` even when the path wouldn't work from the symlink's literal location.

## Erk Pattern: Consistent `.resolve()` for Comparison

Erk consistently resolves paths before comparing them to handle symlinks correctly. See `src/erk/core/worktree_utils.py`:

```python
resolved_current = current_dir.resolve()
resolved_root = worktree_root.resolve()
```

Always call `.resolve()` on both sides of a path comparison. Check `.exists()` before `.resolve()` to avoid resolving nonexistent paths.
