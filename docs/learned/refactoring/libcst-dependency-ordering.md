---
title: libcst-refactor Dependency Ordering
read_when:
  - "planning large-scale refactors"
  - "using libcst-refactor for bulk renames"
  - "avoiding intermediate broken states"
---

# libcst-refactor Dependency Ordering

When executing large refactors, order changes by dependency.

## Correct Ordering

1. **Types first:** Dataclass definitions, type aliases, enums
2. **ABCs second:** Abstract base class method signatures
3. **Implementations third:** Fake and real implementations
4. **Consumers fourth:** Code that uses the types/ABCs
5. **Tests last:** Test files that exercise consumers

## Why This Order Matters

- Types must exist before ABCs can reference them
- ABCs must be updated before implementations
- Consumers depend on stable ABC interfaces
- Tests verify final behavior after all changes

## Example Instruction for libcst-refactor

```
Rename in this order:
1. PlanRowData fields in types.py
2. PlanDataProvider ABC method parameters
3. FakePlanDataProvider method parameters
4. RealPlanDataProvider method parameters
5. TUI code referencing the fields
6. Test files
```

This prevents intermediate states where type checker sees mismatches.

## Related Documentation

- [LibCST Systematic Import Refactoring](libcst-systematic-imports.md) — LibCST patterns and gotchas
- [Frozen Dataclass Field Renames](frozen-dataclass-renames.md) — field-level rename patterns
