---
title: Checkout Helpers Module
last_audited: "2026-02-16 03:30 PT"
audit_result: edited
read_when:
  - "writing checkout commands"
  - "creating worktrees in checkout commands"
  - "implementing branch checkout logic"
tripwires:
  - action: "putting checkout-specific helpers in navigation_helpers.py"
    warning: "`src/erk/cli/commands/navigation_helpers.py` imports from `wt.create_cmd`, which creates a cycle if navigation_helpers tries to import from `wt` subpackage. Keep checkout-specific helpers in separate `checkout_helpers.py` module instead."
---

# Checkout Helpers Module

## Overview

<!-- Source: src/erk/cli/commands/checkout_helpers.py -->

The `src/erk/cli/commands/checkout_helpers.py` module contains shared helper functions used by checkout commands. See `ensure_branch_has_worktree()` and `navigate_and_display_checkout()` in that file for the full API.

These helpers are used by four checkout commands: `wt/checkout_cmd.py`, `branch/checkout_cmd.py`, `plan/checkout_cmd.py`, and `pr/checkout_cmd.py`.

## Why This Module Exists Separately

The helpers live in `checkout_helpers.py` instead of `navigation_helpers.py` **to break a circular import cycle**:

- `navigation_helpers` imports from `wt.create_cmd`
- `wt.create_cmd` is in a module where `wt/__init__.py` imports `wt.checkout_cmd`
- If `navigation_helpers` contains checkout-specific helpers, it creates a cycle: `navigation_helpers` -> `wt.create_cmd` -> `wt` -> `wt.checkout_cmd`

Solution: Keep checkout-specific helpers in a separate `checkout_helpers.py` module that doesn't import from `wt` subpackage.

## Key Design Decisions

### Worktree Creation: Slot vs Direct

`ensure_branch_has_worktree()` supports two creation modes:

- **With slot** (`no_slot=False`): Uses `allocate_slot_for_branch()` for managed slot pool — the default for most checkout commands
- **Without slot** (`no_slot=True`): Creates worktree directly at a computed path — used when slots aren't desired

### Navigation: Script vs Interactive

`navigate_and_display_checkout()` handles two output modes:

- **Script mode**: Generates an activation script and exits via `sys.exit(0)` — used by shell integration
- **Interactive mode**: Returns so the caller can output a custom message with `{styled_path}` placeholder formatting

### Sync Status Display

After checkout, `display_sync_status()` shows remote tracking info using Unicode arrows (e.g., `1↑` ahead, `2↓` behind). Suppressed in script mode for machine-readability. Bot-authored commits (e.g., autofix) get a distinct message.

## Refactoring Pattern

This module is an example of successful minimal abstraction for eliminating duplication:

1. **Identified common pattern**: Multiple commands had identical worktree creation + navigation logic
2. **Extracted minimal helpers**: Functions that handle the repeated blocks without over-engineering
3. **Preserved command-specific logic**: Each command still handles its own branch fetching, PR resolution, etc.
