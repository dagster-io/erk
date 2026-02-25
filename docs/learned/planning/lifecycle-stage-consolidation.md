---
title: Lifecycle Stage Consolidation
read_when:
  - "adding or modifying lifecycle_stage write points"
  - "understanding the impl stage consolidation from implementing/implemented"
  - "working with plan lifecycle stage transitions"
tripwires:
  - action: "writing lifecycle_stage value other than 'impl' in a write point"
    warning: "All lifecycle write points must use 'impl', never the legacy values 'implementing' or 'implemented'. Schema validation accepts legacy values for backwards compatibility only."
    score: 7
---

# Lifecycle Stage Consolidation

The `lifecycle_stage` field was simplified from a two-stage model (`implementing` / `implemented`) to a single `impl` stage. This document covers the rationale, write discipline, and schema compatibility.

## Problem

The original two-stage model (`implementing` and `implemented`) added no actionable value:

- Both stages mean "implementation is happening or has happened"
- No workflow decision depends on distinguishing them
- The display layer renders all three values identically as `[yellow]impl[/yellow]`

## Solution

A single `impl` stage with backwards-compatible parsing.

### Write Discipline

All write points use `"impl"` exclusively. There are four write locations:

| Write Point                                | File                                                     | Context                                                        |
| ------------------------------------------ | -------------------------------------------------------- | -------------------------------------------------------------- |
| `impl_signal.py` "started" handler         | `src/erk/cli/commands/exec/scripts/impl_signal.py`       | Sets `lifecycle_stage: "impl"` when implementation starts      |
| `impl_signal.py` "submitted" handler       | `src/erk/cli/commands/exec/scripts/impl_signal.py`       | Sets `lifecycle_stage: "impl"` after PR submission             |
| `mark_impl_started.py` GitHub Actions path | `src/erk/cli/commands/exec/scripts/mark_impl_started.py` | Sets `lifecycle_stage: "impl"` with `last_remote_impl_at`      |
| `mark_impl_started.py` local path          | `src/erk/cli/commands/exec/scripts/mark_impl_started.py` | Sets `lifecycle_stage: "impl"` with `last_local_impl_*` fields |

### Schema Validation

The schema accepts all three values for backwards compatibility with existing plans:

- `impl` (current, canonical)
- `implementing` (legacy, accepted but never written)
- `implemented` (legacy, accepted but never written)

Schema location: `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py`

### Display Layer

`compute_lifecycle_display()` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py` renders all three values identically:

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py, compute_lifecycle_display() around line 58 -->

This means existing plans with legacy values display correctly without migration.

## Verification

To confirm no write points use legacy values:

```bash
grep -rn '"implementing"\|"implemented"' src/erk/
```

This should return matches only in:

- Schema validation constants (read-only, not write points)
- Display layer comparisons (read-only)

No matches should appear in metadata dict literals or `update_metadata()` calls.

## Related Topics

- [Plan Lifecycle](lifecycle.md) - Full lifecycle documentation including stage table
- [Lifecycle Stage Tracking](lifecycle.md#lifecycle-stage-tracking) - Stage values, write points, display computation
