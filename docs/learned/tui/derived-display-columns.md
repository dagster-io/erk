---
title: Derived Display Columns
read_when:
  - "adding a TUI column that uses an existing PlanRowData field"
  - "deciding whether a new column needs gateway/query changes"
curated_in: erk-tui
---

# Derived Display Columns

When a new TUI column reuses an already-present `PlanRowData` field (no new data needed), you can skip the gateway and data-layer steps from the standard [5-step column addition pattern](column-addition-pattern.md).

## When This Applies

The standard 5-step pattern assumes the column requires new data from the backend. If the data already exists in `PlanRowData` (perhaps fetched for a different purpose), skip steps 1, 2, 4, and 5. Only step 3 (add column + value in table) is needed.

## Reduced Checklist

| Step | File                        | Change                        |
| ---- | --------------------------- | ----------------------------- |
| 3    | `tui/widgets/plan_table.py` | Add column definition + value |

Plus: update all index-based test assertions (see column index cascade tripwire in [column-addition-pattern.md](column-addition-pattern.md)).

## Example: Branch Column

The branch column displays `pr_head_branch` and `worktree_branch` — both already present in `PlanRowData` for other purposes (PR discovery, worktree display). No gateway query, data class field, or serialization changes were needed. Only the column definition and render logic were added to `plan_table.py`.

## Decision: Standard vs Derived

| Question                                   | Answer | Pattern                           |
| ------------------------------------------ | ------ | --------------------------------- |
| Does `PlanRowData` already have this data? | No     | Standard 5-step                   |
| Does `PlanRowData` already have this data? | Yes    | Derived (this)                    |
| Does the column need a new display format? | Yes    | Add `*_display` field (steps 1-2) |

## Related Documentation

- [Column Addition Pattern](column-addition-pattern.md) — Full 5-step pattern
- [Data Contract](data-contract.md) — Display-vs-raw field duality
