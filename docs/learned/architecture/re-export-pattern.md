---
title: Re-Export Pattern
last_audited: "2026-02-08"
audit_result: clean
tripwires:
  - action: "adding re-exports to gateway implementation modules"
    warning: "Only re-export types that genuinely improve public API. Add # noqa: F401 - re-exported for <reason> comment."
  - action: "suppressing F401 (unused import) warnings"
    warning: "Use # noqa: F401 comment per-import with reason, not global ruff config. Indicates intentional re-export vs actual unused import."
read_when:
  - "Creating public API surface from internal gateway modules"
  - "Simplifying import paths for commonly used types"
  - "Working with ruff import linting"
---

# Re-Export Pattern

## Why Re-Exports Exist

Erk splits code across two packages (`erk` and `erk-shared`) but doesn't want consumers to care about this internal boundary. Re-exports hide the package split by making types available through shorter, more intuitive import paths.

**The trade-off:** Public API convenience vs. additional maintenance surface. Every re-export creates two import paths to the same symbol, which must be managed during refactoring.

## The Core Tension

Re-exports appear "unused" to linters because the importing module never references them—it only makes them available to other modules. This creates a choice:

1. **Disable F401 globally** → Hides genuine unused imports, defeats the linter's purpose
2. **Suppress F401 per-import** → Documents intent, distinguishes real re-exports from forgotten imports

Erk chooses option 2. Every re-export must carry a `# noqa: F401` comment explaining its purpose.

## When to Re-Export

| Situation                                        | Re-Export? | Rationale                                |
| ------------------------------------------------ | ---------- | ---------------------------------------- |
| Type is part of module's public interface        | ✅ Yes     | Shorter path benefits external consumers |
| Package boundary abstraction (erk vs erk-shared) | ✅ Yes     | Hides internal organization              |
| Type only used internally by current module      | ❌ No      | No external benefit, just complexity     |
| Avoiding circular imports                        | ❌ No      | Use `TYPE_CHECKING` guards instead       |
| Collecting utilities in one place                | ❌ No      | Creates unclear ownership                |

## Implementation Pattern

<!-- Source: src/erk/core/prompt_executor.py, CommandResult re-export -->

See the `CommandResult` re-export at `src/erk/core/prompt_executor.py:24-25`. The pattern:

```python
from erk_shared.core.prompt_executor import (
    CommandResult,  # noqa: F401 - re-exported for erk.cli.output
)
```

**Critical elements:**

1. `# noqa: F401` suppresses the "imported but unused" warning
2. `re-exported for <consumer>` documents the reason (not just "re-exported")
3. Per-import comment, not file-level or global config

The comment answers: "Why does this import exist if nothing here uses it?" Future maintainers need this context to avoid deleting it during cleanup.

## Linter Configuration Philosophy

**WRONG:** Disable F401 globally in `pyproject.toml`

```toml
[tool.ruff.lint]
ignore = ["F401"]  # DON'T DO THIS
```

This hides genuine unused imports. You lose the linter's value.

**CORRECT:** Keep F401 enabled globally, suppress locally

See `pyproject.toml:96-99` where F401 is included in the `select` list. Individual re-exports then use `# noqa: F401` comments.

## Migration Strategy

When consolidating gateways or refactoring package boundaries:

1. **Keep re-exports during migration** for backward compatibility
2. **Update consumers to canonical path** (automated with grep/sed or LibCST)
3. **Remove re-exports after migration** once all consumers updated
4. **Exception:** Keep if the shorter path genuinely improves the public API

The re-export's purpose changes from "migration bridge" to "public API design choice."

## Common Anti-Patterns

### Re-exporting "just in case"

**Problem:** Bloated public API with unclear ownership. Consumers don't know which import path is canonical.

**Fix:** Only re-export what current consumers actually need. Grep for usage before adding.

### Missing `# noqa` comment

**Problem:** CI fails with F401 errors. Developer doesn't understand why the import exists.

**Fix:** Every re-export needs `# noqa: F401 - re-exported for <specific consumer>`.

### Using re-exports instead of `__all__`

**Problem:** Python's `__all__` is the standard mechanism for defining what `from module import *` exposes.

**Fix:** Use `__all__ = ["Foo", "Bar"]` for wildcard import control. Use re-exports for shortening import paths.

### Re-exporting to hide circular imports

**Problem:** Masks architectural problem. Dependency graph becomes unclear because imports don't reflect actual dependencies.

**Fix:** Use `TYPE_CHECKING` guards and forward references (`"ClassName"` string literals) to break cycles at type-checking time.

## Historical Context

Erk currently has minimal re-exports (only `CommandResult` in the codebase). This document exists because gateway consolidation work frequently creates re-export opportunities, and the team has learned:

1. **Most re-exports are temporary** — They support migration, then get removed
2. **Per-import `# noqa` is non-negotiable** — File-level or global suppression has caused too many genuine unused imports to slip through
3. **Document the consumer** — "`re-exported for X`" makes the purpose searchable and auditable

## Related Documentation

- [Gateway ABC Implementation](gateway-abc-implementation.md) — Where re-exports commonly appear during gateway consolidation
- [Gateway Removal Pattern](gateway-removal-pattern.md) — Cleaning up re-exports after migration completes
