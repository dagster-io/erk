---
title: TUI Keyboard Shortcuts Inventory
read_when:
  - "adding a new keyboard shortcut to the TUI"
  - "checking for shortcut conflicts before binding a new key"
  - "understanding what keys are available in the TUI"
tripwires:
  - action: "adding a new key binding without checking existing bindings"
    warning: "Check this document and ErkDashApp.BINDINGS in app.py for conflicts. Some keys are hidden but still active."
    score: 4
curated_in: erk-tui
---

# TUI Keyboard Shortcuts Inventory

Complete binding inventory from `ErkDashApp.BINDINGS` in `src/erk/tui/app.py`.

## All Bindings

<!-- Source: src/erk/tui/app.py, ErkDashApp.BINDINGS -->

The complete binding inventory is defined in `ErkDashApp.BINDINGS`. The bindings include both visible shortcuts (shown in help) and hidden power-user shortcuts.

## Key Groups

**Navigation:** j/k (vim-style), escape (quit)

**View Switching:** 1/2/3 (direct), left/right (cycle)

**Filters:** o (objective), t (stack), / (text filter), s (sort)

**Item Actions:** enter/space (detail), p (open PR / open objective, view-aware), n (open run), c (comments), h (checks), v (view plan body), l (launch menu), i (implement)

**System:** ctrl+p (command palette), r (refresh), ? (help), q/escape (quit)

## Launch Keys

Launch keys are defined in `CommandDefinition.launch_key` fields in `src/erk/tui/commands/registry.py`, not a separate LAUNCH_KEYS dict. See [TUI Command Registration](tui-command-registration.md) for the full table of current assignments.

Key highlights:

- Plan view: c (close), d (dispatch), l (land), r (rebase), a (address), w (rewrite), m (cmux)
- Objective view: c (close), s (one-shot), k (check)
- Rebase changed from `f` to `r` in PR #8560 for mnemonic consistency

## Naming Convention

Action methods follow the pattern `action_<verb>_<noun>`:

- `action_open_pr` -- opens the PR in browser
- `action_open_run` -- opens the GitHub Actions run URL
- `action_view_comments` -- opens the comments modal

## Priority Binding Pattern for Widget Override

<!-- Source: src/erk/tui/screens/objective_nodes_screen.py -->

When a screen contains a `DataTable` widget, arrow keys are consumed by the widget before the screen's bindings fire. To override this, use `priority=True` on the binding:

The `ObjectiveNodesScreen` uses `priority=True` on its `down` and `up` bindings to ensure arrow keys invoke the screen's custom `action_cursor_down`/`action_cursor_up` methods instead of the DataTable's default handlers. The custom actions add separator-skipping behavior (jumping past decorative separator rows) that j/k (vim-style) bindings also implement.

After this change, j/k and arrow keys work identically for navigation.

## Adding New Bindings

1. Check this table for conflicts
2. Prefer hidden bindings for power-user shortcuts
3. Follow the `action_<verb>_<noun>` naming pattern
4. Update this document after adding

## Related Documentation

- [TUI Modal Screen Pattern](modal-screen-pattern.md) -- How modal screens handle key events
- [TUI Architecture](architecture.md) -- Overall TUI design
- [TUI Command Registration](tui-command-registration.md) -- Launch key assignments and command palette
