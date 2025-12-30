---
title: erk_shared Package
read_when:
  - "deciding where to put new utilities"
  - "moving code between packages"
---

# erk_shared Package

The `erk_shared` package (`packages/erk-shared/`) contains reusable code that can be shared between the main `erk` package and future packages.

## When to Use erk_shared

| Situation                           | Location               |
| ----------------------------------- | ---------------------- |
| Code only used by erk CLI           | `src/erk/`             |
| Reusable utilities and abstractions | `packages/erk-shared/` |

## Package Structure

```
packages/erk-shared/src/erk_shared/
├── context/       # Context helpers for dependency injection
├── gateway/       # Gateway abstractions (git, shell)
├── github/        # GitHub integration
├── graphite/      # Graphite integration
├── scratch/       # Scratch storage and markers
├── extraction/    # Extraction utilities
└── output/        # Output formatting
```

## Import Rules

1. **erk can import from erk_shared** ✅
2. **erk_shared should not import from erk** ❌

## Moving Code to erk_shared

When code needs to be shared:

1. Move the code to appropriate `erk_shared` submodule
2. Update ALL imports to use `erk_shared` directly
3. Do NOT create re-export files (see [No Re-exports Policy](../conventions.md#no-re-exports-for-internal-code))
