---
title: Consolidation Refactoring Guide
read_when:
  - "identifying duplicated patterns"
  - "extracting shared code"
  - "consolidation workflows"
---

# Consolidation Refactoring Guide

How to identify and consolidate duplicated code patterns across the codebase.

## When to Consolidate

Signs that code should be consolidated:

- 3+ files implementing the same multi-step workflow
- Copy-paste patterns with minor variations
- Bug fixes that need to be applied to multiple locations
- Inconsistent behavior across similar operations

## Discovery Process

1. **Identify the pattern**: Look for repeated sequences of operations
2. **Catalog all instances**: Find every file implementing the pattern
3. **Note variations**: Document differences between implementations
4. **Design unified interface**: Create API that handles all variations

## Consolidation Steps

### Step 1: Create the Shared Module

Location guidelines:

- `erk_shared/` for code used by multiple packages
- Adjacent to related ABCs (e.g., `github/plan_issues.py` next to `github/issues/`)

### Step 2: Design the Interface

```python
@dataclass(frozen=True)
class OperationResult:
    """Use Result Pattern for error handling."""
    success: bool
    error: str | None
    # operation-specific fields

def consolidated_operation(
    dependency: SomeDependency,  # ABC for testability
    required_param: str,
    *,
    optional_param: str | None = None,  # Keyword-only for clarity
) -> OperationResult:
    """Perform the consolidated operation.

    Does NOT raise exceptions. All errors returned in result.
    """
```

### Step 3: Write Tests First

Before migrating callers, write comprehensive tests:

- All success paths
- All error paths
- Partial success scenarios
- Edge cases from each caller's context

### Step 4: Migrate Callers (Lowest Risk First)

Order by risk:

1. Newest/simplest callers
2. Well-tested callers
3. Complex callers with special logic
4. Outliers (e.g., subprocess-based implementations)

### Step 5: Verify No Regressions

Run full test suite after each migration.

## Example: Schema v2 Plan Issue Consolidation

**Before**: 5 files duplicating 6-step workflow (~150-200 lines each)
**After**: 1 shared function (~100 lines) + 5 callers (~10-15 lines each)

**Savings**: ~600 lines of duplicated code eliminated

## Anti-Patterns

- **Premature consolidation**: Don't consolidate code with only 2 instances
- **Over-parameterization**: If you need 10+ parameters, the abstraction is wrong
- **Breaking callers**: Migrate incrementally, not all at once
