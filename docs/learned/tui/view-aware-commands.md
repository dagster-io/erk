---
title: View-Aware Command Filtering
read_when:
  - "registering a new TUI command with view-mode filtering"
  - "understanding how commands are filtered by view mode (plans, learn, objectives)"
  - "adding objective-specific commands to the command palette"
  - "implementing streaming commands in the TUI"
tripwires:
  - action: "registering a new TUI command without a view-mode predicate"
    warning: "Every command must use _is_plan_view() or _is_objectives_view() to prevent it from appearing in the wrong view. Commands without view predicates appear in all views."
  - action: "adding streaming commands without using _push_streaming_detail helper"
    warning: "Streaming ACTION commands need _push_streaming_detail() to handle the push-then-stream sequence correctly. Direct streaming without it skips the detail screen push."
---

# View-Aware Command Filtering

The TUI command palette filters commands by the active view mode. Plan commands appear only in Plans/Learn views; objective commands appear only in the Objectives view. This filtering is implemented through view-mode predicates in the command registry.

## View Mode Predicates

<!-- Source: src/erk/tui/commands/registry.py:21-28 -->

Two predicates partition the command space by view mode:

<!-- See _is_plan_view and _is_objectives_view in src/erk/tui/commands/registry.py:21-28 -->

- `_is_plan_view(ctx)`: Returns `True` when not in Objectives view (i.e., Plans or Learn) — checks `ctx.view_mode != ViewMode.OBJECTIVES`
- `_is_objectives_view(ctx)`: Returns `True` when in Objectives view — checks `ctx.view_mode == ViewMode.OBJECTIVES`

The `CommandContext.view_mode` field carries the active `ViewMode` enum value. `MainListCommandProvider` reads this dynamically from `self._app._view_mode`, while `PlanCommandProvider` hardcodes `ViewMode.PLANS` since the detail modal is always in plan context.

## Why Predicates, Not Separate Registries

A single `get_all_commands()` list defines both plan and objective commands. View filtering happens inside each command's `is_available` predicate, composed with data-availability checks:

```python
# Plan command: needs plan view + PR number
is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_number is not None

# Objective command: needs objectives view only
is_available=lambda ctx: _is_objectives_view(ctx)
```

This keeps command definitions in one place. Adding a command to the wrong view is prevented by requiring the view predicate — without it, the command would appear everywhere.

## Shortcut Reuse Across Views

<!-- Source: src/erk/tui/commands/registry.py, shortcut assignments -->

Plan and objective commands safely reuse the same keyboard shortcuts because the view predicates guarantee mutual exclusivity:

| Shortcut | Plan View Command    | Objectives View Command |
| -------- | -------------------- | ----------------------- |
| `s`      | Submit to Queue      | Implement (One-Shot)    |
| `5`      | Fix Conflicts Remote | Check Objective         |
| `i`      | Open Issue           | Open Objective          |
| `1`      | Copy Prepare         | Copy Implement          |
| `3`      | Copy Submit          | Copy View               |

A shortcut collision would only occur if both a plan and objective command with the same shortcut had overlapping view predicates. The `_is_plan_view` / `_is_objectives_view` split prevents this.

## Objective Command Definitions

<!-- Source: src/erk/tui/commands/registry.py:218-357 -->

Six objective commands are registered, spanning all three categories:

| ID                | Category | Shortcut | Display Name Generator            |
| ----------------- | -------- | -------- | --------------------------------- |
| `one_shot_plan`   | ACTION   | `s`      | `erk objective plan N --one-shot` |
| `check_objective` | ACTION   | `5`      | `erk objective check N`           |
| `close_objective` | ACTION   | —        | `erk objective close N --force`   |
| `open_objective`  | OPEN     | `i`      | Issue URL or "Objective"          |
| `copy_plan`       | COPY     | `1`      | `erk objective plan N`            |
| `copy_view`       | COPY     | `3`      | `erk objective view N`            |

All six use `_is_objectives_view(ctx)` as their sole view predicate. Objective commands don't have compound availability conditions (unlike plan commands which check for PR, issue URL, etc.) because objective rows always have an issue number.

## Provider Context Building

<!-- Source: src/erk/tui/commands/provider.py:85-94, 174-181 -->

The two command providers resolve `CommandContext` differently:

- **`MainListCommandProvider._get_context()`**: Returns `CommandContext | None`. Reads `view_mode` dynamically from `self._app._view_mode`, which changes as the user switches tabs. This is what enables objective commands to appear when the Objectives tab is active.

- **`PlanCommandProvider._get_context()`**: Returns `CommandContext` (never None). Hardcodes `view_mode=ViewMode.PLANS` because the detail modal always shows a plan. This means objective commands never appear in the detail modal's command palette — by design, since the modal is scoped to a single plan.

## The `_push_streaming_detail` Pattern

ACTION commands that run long-running subprocess operations (land, fix-conflicts, address) need to push a detail screen first, then stream output into it. The `_push_streaming_detail()` helper on `ErkDashApp` handles this two-step sequence:

1. Push a `PlanDetailScreen` for the selected row
2. Start the streaming command in the detail screen

Without this helper, a streaming command started from the main list would have no visible output destination. The helper ensures the detail screen exists before streaming begins.

## Backend as Third Dimension

View mode and data availability are the first two filter dimensions. **Plan backend** is the third. Some commands only make sense for one backend:

- `copy_prepare` and `copy_prepare_activate` are hidden when `plan_backend == "github-draft-pr"` because the "prepare" workflow uses issue numbers that don't apply to draft-PR plans.

The `plan_backend` field is available on `CommandContext` (alongside `view_mode` and `row`). The `_is_github_backend(ctx)` predicate checks `ctx.plan_backend == "github"`.

See [Backend-Aware Commands](backend-aware-commands.md) for the complete reference.

## Related Documentation

- [TUI Command Architecture](action-inventory.md) — Data-driven availability predicates and category mapping
- [Dual Provider Pattern](dual-handler-pattern.md) — How two providers share one registry
- [TUI Streaming Output](streaming-output.md) — Cross-thread UI updates for ACTION commands
