---
title: Type-Safe Refactoring with Frozen Dataclasses
read_when:
  - "planning large-scale refactors"
  - "understanding type safety benefits"
  - "working with frozen dataclasses"
---

# Type-Safe Refactoring

Frozen dataclasses + strict type checking enable confident mechanical renames.

## The Safety Net

With frozen dataclasses:

- All field access is through explicit attribute access
- Type checker verifies every access site
- No dynamic attribute setting to bypass checks

## Workflow

1. Change the field name in the dataclass
2. Run type checker
3. Fix every error it reports
4. Run tests to catch string literal issues

## What It Catches

- Direct field access (`row.plan_id`)
- Constructor kwargs (`PlanRowData(plan_id=123)`)
- Comparison operations (`row.plan_id == other.plan_id`)

## What It Misses

- JSON key strings (`"issue_number"` in test assertions)
- Display strings (`f"Issue #{row.issue_number}"`)
- Docstrings and comments

Use grep for these after type checking passes.

## Related Documentation

- [Frozen Dataclass Field Renames](frozen-dataclass-renames.md) — specific rename patterns
- [Multi-Pass Rename Verification](multi-pass-rename-verification.md) — verification checklist
