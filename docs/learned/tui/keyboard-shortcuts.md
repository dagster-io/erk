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

**Item Actions:** enter/space (detail), p (open PR), n (open run), c (comments), h (checks), v (view plan body), l (launch menu), i (implement)

**System:** ctrl+p (command palette), r (refresh), ? (help), q/escape (quit)

## Naming Convention

Action methods follow the pattern `action_<verb>_<noun>`:

- `action_open_pr` — opens the PR in browser
- `action_open_run` — opens the GitHub Actions run URL
- `action_view_comments` — opens the comments modal

## Adding New Bindings

1. Check this table for conflicts
2. Prefer hidden bindings for power-user shortcuts
3. Follow the `action_<verb>_<noun>` naming pattern
4. Update this document after adding

## Related Documentation

- [TUI Modal Screen Pattern](modal-screen-pattern.md) — How modal screens handle key events
- [TUI Architecture](architecture.md) — Overall TUI design
