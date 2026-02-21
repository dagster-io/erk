---
title: erk_shared Package
last_audited: "2026-02-16 00:00 PT"
audit_result: edited
read_when:
  - "deciding where to put new utilities"
  - "moving code between packages"
tripwires:
  - action: "importing PlanBackendType or redeclaring it in a module other than erk_shared.context.types"
    warning: "PlanBackendType canonical import: import PlanBackendType only from erk_shared.context.types. Do not re-declare or shadow this type in other modules — erk_shared.context.types is the single source of truth. Shadowing creates hidden divergence that breaks isinstance checks and type narrowing."
    score: 7
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
├── config/        # Configuration management
├── context/       # Context helpers for dependency injection
├── core/          # Core abstractions (PromptExecutor ABC)
├── gateway/       # Gateway abstractions (git, github, shell, etc.)
├── hooks/         # Hook utilities
├── learn/         # Learn workflow utilities
├── output/        # Output formatting
├── plan_store/    # Plan storage
├── printing/      # Printing utilities
├── scratch/       # Scratch storage and markers
├── sessions/      # Session management
├── shell_utils/   # Shell integration utilities
└── stack/         # Stack management
```

## Import Rules

1. **erk can import from erk_shared** ✅
2. **erk_shared should not import from erk** ❌

## Moving Code to erk_shared

When code needs to be shared:

1. Move the code to appropriate `erk_shared` submodule
2. Update ALL imports to use `erk_shared` directly
3. Do NOT create re-export files (see [No Re-exports Policy](../conventions.md#no-re-exports-for-internal-code))
