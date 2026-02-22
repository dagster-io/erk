---
title: Lifecycle and PR Status Display
read_when:
  - "adding a new lifecycle stage to the TUI"
  - "changing lifecycle abbreviations or colors"
  - "modifying PR status emoji indicators"
  - "understanding the stage column in erk dash"
tripwires:
  - action: "adding a new lifecycle stage without updating abbreviation map"
    warning: "The stage column is 9 chars wide. New stages longer than 9 chars need abbreviations in compute_lifecycle_display(). Also update format_lifecycle_with_status() stage detection."
---

# Lifecycle and PR Status Display

The TUI dashboard shows a `stage` column for draft_pr plans, computed in `lifecycle.py` and displayed only in draft_pr backend mode. PR status indicators (draft/published, conflicts, review decisions) are rendered inline within the stage display.

## Lifecycle Stage Display

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py, compute_lifecycle_display -->

`compute_lifecycle_display()` reads `lifecycle_stage` from plan header fields. If absent, it infers the stage from `is_draft` and `pr_state` in plan metadata:

| `is_draft` | `pr_state` | Inferred Stage  |
| ---------- | ---------- | --------------- |
| `True`     | `"OPEN"`   | `"planned"`     |
| `False`    | `"OPEN"`   | `"implemented"` |
| `False`    | `"MERGED"` | `"merged"`      |
| `False`    | `"CLOSED"` | `"closed"`      |

When the resolved stage is `"planned"` and a workflow run exists, it upgrades to `"implementing"`.

### Abbreviation and Color Map

The `stage` column is 9 characters wide. Stages longer than 9 chars are abbreviated:

| Stage          | Display    | Color   | Rich Markup                   |
| -------------- | ---------- | ------- | ----------------------------- |
| `prompted`     | `prompted` | magenta | `[magenta]prompted[/magenta]` |
| `planning`     | `planning` | magenta | `[magenta]planning[/magenta]` |
| `planned`      | `planned`  | dim     | `[dim]planned[/dim]`          |
| `implementing` | `impling`  | yellow  | `[yellow]impling[/yellow]`    |
| `implemented`  | `impld`    | cyan    | `[cyan]impld[/cyan]`          |
| `merged`       | `merged`   | green   | `[green]merged[/green]`       |
| `closed`       | `closed`   | dim red | `[dim red]closed[/dim red]`   |
| unknown/None   | `-`        | (none)  | `"-"`                         |

### Lifecycle with Status Indicators

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py, format_lifecycle_with_status -->

`format_lifecycle_with_status()` enriches the lifecycle display with emoji indicators inserted inside Rich markup tags:

- **Prefix** (active stages only: planned, implementing, review):
  - Draft PR: `🚧 ` prefix
  - Published PR: `👀 ` prefix
- **Suffix** (implementing, implemented, review stages only):
  - Conflicts: `💥`
  - Approved (review only): `✔`
  - Changes requested (review only): `❌`

Example: `[yellow]👀 impling 💥[/yellow]` for a published PR that is implementing and has conflicts.

## Code Location

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py -->

`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py` — both functions: `compute_lifecycle_display()` (lines 12-66), `format_lifecycle_with_status()` (lines 69-148).

## Related Documentation

- [Dashboard Column Inventory](dashboard-columns.md) — column layout and widths
- [PlanRowData Field Reference](plan-row-data.md) — `lifecycle_display` and `pr_status_display` fields
