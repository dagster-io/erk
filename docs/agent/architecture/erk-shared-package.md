---
title: erk_shared Package
read_when:
  - "sharing code between erk and erk-kits"
  - "deciding where to put new utilities"
  - "moving code between packages"
tripwires:
  - action: "importing from erk package in erk-kits"
    warning: "erk-kits cannot import from erk. Use erk_shared for shared code."
---

# erk_shared Package

The `erk_shared` package (`packages/erk-shared/`) contains code shared between:

- `erk` - Main CLI package
- `erk-kits` - Kit CLI commands for Claude Code

## When to Use erk_shared

| Situation                 | Location               |
| ------------------------- | ---------------------- |
| Code only used by erk CLI | `src/erk/`             |
| Code only used by kit CLI | `packages/erk-kits/`   |
| Code used by both         | `packages/erk-shared/` |

## Package Structure

```
packages/erk-shared/src/erk_shared/
├── git/           # Git abstraction (abc, real, fake, dry_run)
├── github/        # GitHub integration
├── graphite/      # Graphite integration
├── scratch/       # Scratch storage and markers
├── extraction/    # Extraction utilities
└── output/        # Output formatting
```

## Import Rules

1. **erk can import from erk_shared** ✅
2. **erk-kits can import from erk_shared** ✅
3. **erk-kits cannot import from erk** ❌

## Moving Code to erk_shared

When code needs to be shared:

1. Move the code to appropriate `erk_shared` submodule
2. Update ALL imports to use `erk_shared` directly
3. Do NOT create re-export files (see [No Re-exports Policy](../conventions.md#no-re-exports-for-internal-code))
