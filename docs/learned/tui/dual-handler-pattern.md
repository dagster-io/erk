---
title: Dual Provider Pattern for Context-Agnostic Commands
read_when:
  - "implementing a TUI command that works from both list and detail views"
  - "understanding how MainListCommandProvider and PlanCommandProvider share commands"
  - "adding command palette support to a new screen"
tripwires:
  - action: "duplicating command definitions for list and detail contexts"
    warning: "Commands are defined once in the registry. Use a second Provider subclass with its own _get_context() to serve the same commands from a new context."
  - action: "duplicating execute_palette_command logic between ErkDashApp and PlanDetailScreen"
    warning: "This duplication is a known trade-off. Both ErkDashApp.execute_palette_command() and PlanDetailScreen.execute_command() implement the same command_id switch because they dispatch to different APIs (provider methods vs executor methods). See the asymmetries section below."
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
---

# Dual Provider Pattern for Context-Agnostic Commands

The TUI command palette serves the same set of commands from two different UI contexts (main list and plan detail modal) without duplicating command definitions. This is achieved through Textual's `Provider` mechanism: two provider classes share one command registry but resolve `CommandContext` from different sources.

## Why Two Providers, Not Two Registries

The core design question was: when a user opens the command palette from the detail modal, should it show a different set of commands than from the main list? The answer is no — the same operations (open PR, copy checkout, close plan) apply regardless of context. What differs is only _which plan_ the command operates on and _how the command dispatches_.

<!-- Source: src/erk/tui/commands/provider.py, MainListCommandProvider -->
<!-- Source: src/erk/tui/commands/provider.py, PlanCommandProvider -->

`MainListCommandProvider` resolves context from the table's selected row (`_app._get_selected_row()`), while `PlanCommandProvider` resolves context from the detail screen's `_row` field. Both call the same `get_available_commands()` with the resolved `CommandContext`, so command definitions, availability predicates, and display names are defined exactly once.

## The Critical Asymmetries

Despite sharing command definitions, the two contexts differ in important ways that prevent full unification:

### Context Resolution Fallibility

<!-- Source: src/erk/tui/commands/provider.py, MainListCommandProvider._get_context -->
<!-- Source: src/erk/tui/commands/provider.py, PlanCommandProvider._get_context -->

`MainListCommandProvider._get_context()` returns `CommandContext | None` — no row may be selected. `PlanCommandProvider._get_context()` returns `CommandContext` (never None) — the detail screen always has a `_row`. This means `MainListCommandProvider.discover()` must guard against `None` context, while `PlanCommandProvider.discover()` can proceed unconditionally.

### Dispatch Target Divergence

<!-- Source: src/erk/tui/app.py, ErkDashApp.execute_palette_command -->
<!-- Source: src/erk/tui/screens/plan_detail_screen.py, PlanDetailScreen.execute_command -->

Both providers feed the same `command_id` string into dispatch methods, but the dispatch targets are different:

- **Main list**: `MainListCommandProvider` dispatches to `ErkDashApp.execute_palette_command()`, which uses `self._provider` (the `PlanDataProvider`) directly for browser/clipboard/API operations.
- **Detail modal**: `PlanCommandProvider` dispatches to `PlanDetailScreen.execute_command()`, which uses an injected `CommandExecutor` for the same operations.

This dispatch duplication is the main cost of the pattern. Both methods contain parallel `command_id` switch statements handling the same IDs. The duplication exists because `ErkDashApp` operates at the app level (accessing `self._provider` and managing screen pushes), while `PlanDetailScreen` operates within a modal (using an executor and able to `self.dismiss()`). Attempts to unify them would require either threading app-level concerns into the modal or modal-level concerns into the app, both of which would violate the screen boundary.

### ViewMode Hardcoding in PlanCommandProvider

<!-- Source: src/erk/tui/commands/provider.py:181 -->

`PlanCommandProvider._get_context()` hardcodes `view_mode=ViewMode.PLANS`:

```python
return CommandContext(row=self._detail_screen._row, view_mode=ViewMode.PLANS)
```

This is intentional, not a bug. The detail modal always shows a single plan, so objective commands should never appear there. In contrast, `MainListCommandProvider` reads `view_mode` dynamically from `self._app._view_mode`, which changes as the user switches tabs — this is what enables objective commands to appear when the Objectives tab is active. The asymmetry exists because the detail modal is scoped to plan context while the main list serves multiple views.

## When This Pattern Breaks Down

The dual provider pattern works for operations on "the selected plan." It does not apply to:

- **View-specific commands**: Sort, filter, and navigation bindings are screen-level `BINDINGS`, not palette commands
- **Commands that need app-level orchestration**: Some ACTION commands dispatched from the main list create a `PlanDetailScreen` and push it _then_ invoke a streaming command — this two-step push-then-execute sequence only makes sense at the app level
- **Commands with different semantics per context**: `close_plan` from the detail modal dismisses the modal first, then delegates to the app. From the main list, it runs directly. The command_id is the same but the orchestration differs.

## Related Documentation

- [TUI Command Architecture](action-inventory.md) — Command categories, availability predicates, and the shared registry
- [Textual CommandPalette Guide](command-palette.md) — System command hiding and display formatting
- [Adding Commands to TUI](adding-commands.md) — Step-by-step guide including the dual provider touchpoints
- [TUI Data Contract](data-contract.md) — The `PlanRowData` and `CommandContext` types that providers resolve
