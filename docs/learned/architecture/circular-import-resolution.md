---
title: Circular Import Resolution Pattern
read_when:
  - "encountering circular imports between erk and erk_shared"
  - "moving an ABC to erk_shared to break import cycles"
  - "using TYPE_CHECKING guards for type-only imports"
tripwires:
  - action: "importing from erk in erk_shared code"
    warning: "erk_shared must not import from erk. Move ABCs to erk_shared, keep implementations in erk. See circular-import-resolution.md."
---

# Circular Import Resolution Pattern

When an ABC in `erk` is consumed by `ErkContext` (also in `erk`), but the implementation needs types from `ErkContext`, a circular import occurs. The solution: move the ABC to `erk_shared`, keep the implementation in `erk`.

## Concrete Example: HealthCheckRunner

### Problem

`HealthCheckRunner` ABC was in `erk`, consumed by `ErkContext`. But `RealHealthCheckRunner.run_all()` needed `ErkContext` as a parameter — circular import.

### Solution

<!-- Source: packages/erk-shared/src/erk_shared/core/health_check_runner.py -->
<!-- Source: src/erk/core/health_checks/runner.py -->

1. **ABC** moved to `packages/erk-shared/src/erk_shared/core/health_check_runner.py`
2. **Implementation** stays at `src/erk/core/health_checks/runner.py` (`RealHealthCheckRunner`)
3. **TYPE_CHECKING guard** in the ABC file: uses `from __future__ import annotations` and a `TYPE_CHECKING` block to import `ErkContext` for type annotations only, avoiding the runtime circular import

The `RealHealthCheckRunner` is a thin wrapper that delegates to `run_all_checks()` module-level function, keeping the ABC minimal.

## General Pattern

1. Move ABC to `erk_shared` (the lower-level package)
2. Keep implementation in `erk` (the higher-level package)
3. Use `TYPE_CHECKING` guard for type-only imports from the higher package
4. Implementation can import from both `erk` and `erk_shared` freely

## Precedent

This follows the same pattern as `GraphiteDisabled` sentinel: the sentinel type lives in `erk_shared` so context construction can reference it without importing the full Graphite implementation.

## Related Documentation

- [Gateway ABC Implementation](gateway-abc-implementation.md) — 5-place ABC pattern
- [Erk Architecture Patterns](erk-architecture.md) — Package dependency direction
