---
title: Plan Reference Preservation in Roadmap Updates
read_when:
  - "calling update-roadmap-step with --pr but without --plan"
  - "changing update_step_in_frontmatter() semantics for plan=None"
  - "updating objective roadmap step plan or PR references"
  - "debugging lost plan references in objective roadmaps"
tripwires:
  - action: "calling update-roadmap-step with --pr but without --plan"
    warning: "CLI validation requires --plan when --pr is set. Omitting --plan would silently lose the plan reference. Use --plan '#NNN' to preserve or --plan '' to explicitly clear."
  - action: "changing update_step_in_frontmatter() semantics for plan=None"
    warning: "plan=None means 'preserve existing value', not 'clear'. This three-state pattern (None=preserve, ''=clear, '#NNN'=set) is used by both CLI and gateway. Changing it breaks preservation."
---

# Plan Reference Preservation in Roadmap Updates

When updating a roadmap step's PR reference, the plan reference must not be silently lost. This document explains the defense-in-depth pattern that prevents accidental plan loss.

## The Failure Mode

<!-- Source: src/erk/cli/commands/exec/scripts/update_roadmap_step.py:353-368 -->

The `update-roadmap-step` exec script accepts `--plan` and `--pr` flags. Before the fix, calling `--pr #123` without `--plan` would set the PR but leave `plan=None`, which the gateway interpreted as "clear the plan field." This silently erased the plan reference.

## Defense-in-Depth: CLI + Gateway

Two independent layers prevent this failure:

### Layer 1: CLI Validation (`plan_required_with_pr`)

The CLI rejects `--pr` without `--plan` before reaching the gateway:

```python
if pr_ref and plan_ref is None:
    # Error: --plan is required when --pr is set
    # Use --plan '' to explicitly clear, or --plan '#NNN' to preserve
```

This is the primary safeguard. It forces callers to state their intent explicitly.

### Layer 2: Gateway Preservation (`plan=None` means preserve)

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py:277-343 -->

The `update_step_in_frontmatter()` function uses a three-state pattern for both `plan` and `pr` parameters:

| Value    | Meaning           | Example          |
| -------- | ----------------- | ---------------- |
| `None`   | Preserve existing | (omitted)        |
| `""`     | Clear the field   | `--plan ''`      |
| `"#NNN"` | Set new value     | `--plan '#6464'` |

```python
# Resolve plan: None=preserve, ""=clear, "#6464"=set
if plan is None:
    resolved_plan = step.plan  # preserve existing
else:
    resolved_plan = plan or None  # "" becomes None (clear), "#NNN" stays
```

This ensures that even if a caller passes `plan=None`, the existing value is preserved rather than cleared.

## Dual-Storage Coordination

Objective roadmaps exist in two formats that use identical semantics:

1. **YAML frontmatter** — structured step data in a metadata block, updated by `update_step_in_frontmatter()`
2. **Markdown table** — human-readable table in the issue body, updated by `update_step_in_table()`

Both use the same three-state pattern. When one is updated, the other should be updated with the same values to maintain consistency.

## Status Computation

When plan or PR values change, step status is recomputed:

1. **Explicit status** — if `--status` is passed, it wins
2. **PR present** → status becomes `done`
3. **Plan present** (no PR) → status becomes `in_progress`
4. **Neither** → preserve existing status

This inference happens at write time in the gateway, not at parse time. The parser reads whatever status is stored; the updater infers what status should be based on the new references.

## Related Documentation

- [Objective Summary Format](../reference/objective-summary-format.md) — Status inference in roadmap parsing
- [Objective Lifecycle](objective-lifecycle.md) — How objectives and plans relate
