# erk-shared

Shared utilities and interfaces for erk and erk-kits packages.

This package provides:

- **GitHub Issues Interface**: ABC with Real/Fake implementations
- **Naming Utilities**: Filename and worktree name transformations
- **Metadata Blocks**: GitHub comment formatting utilities
- **Impl Folder Utilities**: Issue reference management and progress parsing

## Purpose

This package exists to break the circular dependency between `erk` and `erk-kits`:

- `erk` imports kit utilities from `erk-kits`
- `erk-kits` imports interfaces and utilities from `erk`

By extracting shared code to `erk-shared`, we create an acyclic dependency graph:

```
erk-shared (no dependencies)
    ↑
    |
erk-kits (depends on: erk-shared)
    ↑
    |
erk (depends on: erk-kits, erk-shared)
```

## Note

This is an internal workspace package, not published to PyPI.
