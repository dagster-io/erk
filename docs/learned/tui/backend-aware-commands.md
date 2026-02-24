---
title: Backend-Aware TUI Commands
read_when:
  - "adding new TUI commands to the command palette"
  - "debugging why a command is not visible in the command palette"
  - "understanding which commands are hidden in planned-PR mode"
tripwires:
  - action: "adding a new TUI command that should only show in certain plan backends"
    warning: "Commands have THREE filter dimensions: view mode, data availability, AND plan backend. If the command is backend-specific, add _is_github_backend() or a similar predicate to is_available. See backend-aware-commands.md."
    score: 8
---

# Backend-Aware TUI Commands

The TUI command palette filters commands along three independent dimensions:

1. **View mode** — Which view is active (plans, learn, objectives). Checked via `_is_plan_view()`, `_is_objectives_view()`, etc.
2. **Data availability** — Whether required data exists (e.g., a PR URL, an issue number). Checked in `is_available` lambda.
3. **Plan backend** — Which plan backend is active (`github` vs `github-draft-pr`). Checked via `_is_github_backend()`.

Missing any dimension means a command can appear when it shouldn't, or be invisible when it should be visible.

## `_is_github_backend()` Predicate

<!-- Source: src/erk/tui/commands/registry.py:31-33, _is_github_backend -->

The function checks `ctx.plan_backend == "github"` and returns `True` for issue-based plans. See `src/erk/tui/commands/registry.py:31-33` for the implementation.

**Dead code note:** After PR #7971, `plan_backend` is always `"planned_pr"`, so `_is_github_backend()` can never return `True`. This function is scheduled for removal in objective #7911 node 1.3.

## `CommandContext` with `plan_backend`

<!-- Source: src/erk/tui/commands/types.py:23-35, CommandContext -->

The `CommandContext` frozen dataclass at `src/erk/tui/commands/types.py:23-35` carries `row`, `view_mode`, and `plan_backend` fields. The `plan_backend` field is typed as `Literal["planned_pr"]` after PR #7971. The former `PlanBackendType` type alias (which included `"github"`) was deleted. The only valid value is `"planned_pr"`.

**Transitional state:** The `plan_backend` parameter still exists on several TUI entry points (`app.py`, `plan_table.py`, `types.py`) but is redundant — it always carries `"planned_pr"`. These parameters are scheduled for removal in objective #7911 node 1.3. Do not add new callers or expand usage of `plan_backend` in TUI code.

## Commands Hidden in `planned_pr` Mode

Two commands are hidden when the backend is `github-draft-pr`:

| Command ID              | Shortcut | Reason hidden in planned-PR mode                              |
| ----------------------- | -------- | ------------------------------------------------------------- |
| `copy_prepare`          | `1`      | "Prepare" uses issue numbers; planned-PR uses branch checkout |
| `copy_prepare_activate` | `4`      | Same reason — prepare workflow doesn't apply to planned-PR    |

**Registry entry pattern** (`registry.py:314-329`):

<!-- Source: src/erk/tui/commands/registry.py:319, copy_prepare command -->

The `is_available` lambda combines `_is_plan_view(ctx) and _is_github_backend(ctx)`. See `registry.py:319` for the exact expression.

## Adding Backend-Filtered Commands

When adding a command that should only appear in one backend:

1. Use `_is_github_backend(ctx)` in `is_available` for issue-only commands
2. Use `not _is_github_backend(ctx)` for planned-PR-only commands
3. Combine with view mode checks: `_is_plan_view(ctx) and _is_github_backend(ctx)`

## Related Documentation

- [View-Aware Commands](view-aware-commands.md) — The first two filter dimensions
- [Adding Commands](adding-commands.md) — Full guide for adding commands to the palette
