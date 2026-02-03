---
title: Re-Export Pattern
last_audited: "2026-02-03 03:56 PT"
audit_result: edited
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

## Overview

The re-export pattern allows gateway implementation modules to expose ABC types and related classes from `erk-shared`, creating a cleaner import path for consumers while maintaining a single canonical definition.

## Pattern Definition

A **re-export** is an import that exists solely to make a symbol available through the current module, not for use within the module itself.

```python
# src/erk/core/prompt_executor.py
from erk_shared.core.prompt_executor import (
    CommandResult,  # noqa: F401 - re-exported for erk.cli.output
    PromptExecutor,
    PromptResult,
)
```

Consumers can then import from the shorter path:

```python
# Before (verbose, exposes internal structure)
from erk_shared.core.prompt_executor import CommandResult

# After (clean, hides package boundaries)
from erk.core.prompt_executor import CommandResult
```

## When to Use Re-Exports

**Use re-exports when:**

1. **Public API surface** - The type is part of the module's public interface
2. **Convenience for consumers** - Shorter import path improves ergonomics
3. **Package boundary abstraction** - Hide split between `erk` and `erk-shared`

**Do NOT use re-exports for:**

1. **Types only used internally** - If only the current module needs it, don't re-export
2. **Avoiding circular imports** - Use `TYPE_CHECKING` guards instead
3. **Collecting "utility" imports** - Don't create `utils.py` that re-exports everything

## The `# noqa: F401` Comment

### Why It's Needed

Ruff's F401 rule flags unused imports:

```python
from erk_shared.core.prompt_executor import CommandResult  # F401: imported but unused
```

The import appears unused because the current module doesn't reference `CommandResult` - it only re-exports it for others.

### Required Format

```python
CommandResult,  # noqa: F401 - re-exported for <consumer-description>
```

**Format rules:**

- Comment MUST include `# noqa: F401` to suppress the warning
- Comment SHOULD include reason: `re-exported for <consumer>`
- Reason helps future developers understand the re-export's purpose

### Real-World Example

```python
# src/erk/core/prompt_executor.py:22-23
from erk_shared.core.prompt_executor import (
    CommandResult,  # noqa: F401 - re-exported for erk.cli.output
    # ... other imports used in this module ...
)
```

This tells readers:

1. `CommandResult` is intentionally imported but not used here
2. It's re-exported for `erk.cli.output` module's convenience
3. Don't delete this import during cleanup - it's serving a purpose

## Ruff Configuration

The `# noqa: F401` comment is per-import. Do NOT disable F401 globally in `pyproject.toml` - that would hide genuine unused imports.

**Correct approach:**

```toml
# pyproject.toml - keep F401 enabled
[tool.ruff.lint]
select = ["F"]  # Include F401 checks
```

Then suppress on a per-import basis with `# noqa: F401` comments.

## Migration Pattern

When consolidating gateways (e.g., PromptExecutor merging):

1. **Keep re-exports** during migration for backward compatibility
2. **Update all consumers** to use canonical import path
3. **Remove re-exports** once all consumers migrated
4. **Verify with ruff** - no F401 warnings should remain

**Exception:** If the re-export genuinely improves the public API (shorter path, cleaner interface), keep it permanently with proper `# noqa: F401` comment.

## Common Pitfalls

**Re-exporting everything "just in case"**

- **Problem:** Creates bloated public API with unclear ownership
- **Fix:** Only re-export what consumers actually need

**Missing `# noqa: F401` comment**

- **Problem:** Ruff flags as error, blocks CI
- **Fix:** Add `# noqa: F401 - re-exported for <reason>` to every re-export

**Using re-exports as `__all__` alternative**

- **Problem:** Python's `__all__` is the correct mechanism for defining public API
- **Fix:** Use `__all__ = ["Foo", "Bar"]` instead of re-exporting for wildcard imports

**Re-exporting to avoid fixing circular imports**

- **Problem:** Masks architectural problem, makes dependency graph unclear
- **Fix:** Use `TYPE_CHECKING` guards and forward references

## Related Documentation

- [Gateway ABC Implementation](gateway-abc-implementation.md) - Where re-exports commonly appear
- [Gateway Removal Pattern](gateway-removal-pattern.md) - Cleaning up re-exports during consolidation
