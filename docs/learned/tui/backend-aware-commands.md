---
title: Backend-Aware TUI Commands
read_when:
  - "adding new TUI commands to the command palette"
  - "debugging why a command is not visible in the command palette"
  - "understanding which commands are hidden in draft-PR mode"
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

The `plan_backend` field is a `PlanBackendType` value (`"github"` or `"github-draft-pr"`).

## `CommandContext` with `plan_backend`

<!-- Source: src/erk/tui/commands/types.py:23-35, CommandContext -->

The `CommandContext` frozen dataclass at `src/erk/tui/commands/types.py:23-35` carries `row`, `view_mode`, and `plan_backend` fields. The `plan_backend` field is set from the app's active backend configuration and passed to every command's `is_available` and `get_display_name` functions.

## Commands Hidden in `draft_pr` Mode

Two commands are hidden when the backend is `github-draft-pr`:

| Command ID              | Shortcut | Reason hidden in draft-PR mode                              |
| ----------------------- | -------- | ----------------------------------------------------------- |
| `copy_prepare`          | `1`      | "Prepare" uses issue numbers; draft-PR uses branch checkout |
| `copy_prepare_activate` | `4`      | Same reason — prepare workflow doesn't apply to draft-PR    |

**Registry entry pattern** (`registry.py:314-329`):

<!-- Source: src/erk/tui/commands/registry.py:319, copy_prepare command -->

The `is_available` lambda combines `_is_plan_view(ctx) and _is_github_backend(ctx)`. See `registry.py:319` for the exact expression.

## Adding Backend-Filtered Commands

When adding a command that should only appear in one backend:

1. Use `_is_github_backend(ctx)` in `is_available` for issue-only commands
2. Use `not _is_github_backend(ctx)` for draft-PR-only commands
3. Combine with view mode checks: `_is_plan_view(ctx) and _is_github_backend(ctx)`

## Related Documentation

- [View-Aware Commands](view-aware-commands.md) — The first two filter dimensions
- [Adding Commands](adding-commands.md) — Full guide for adding commands to the palette
