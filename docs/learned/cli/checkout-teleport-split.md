---
title: Checkout/Teleport Command Split
read_when:
  - "working with erk pr checkout or erk pr teleport commands"
  - "understanding the difference between checkout and teleport"
  - "modifying cmux-open-pr command"
tripwires:
  - action: "adding --sync to checkout"
    warning: "checkout is local-only; use teleport for sync. Checkout preserves local state; teleport force-resets to remote."
---

# Checkout/Teleport Command Split

The `checkout` and `teleport` commands were split to separate local-only and remote-sync concerns.

## Problem

`checkout` was overloaded with both local worktree management and remote synchronization (Graphite sync). This made the command unpredictable: sometimes it preserved local state, sometimes it overwrote it.

## Solution

Two distinct commands with clear guarantees:

### `erk pr checkout` (lightweight, local-only)

```
erk pr checkout <REFERENCE> [--no-slot] [-f/--force] [--script]
```

- Preserves local state (reuses existing worktrees, keeps unpushed commits)
- Handles both PR references (`123`, URL) and plan references (`P123`)
- For plans: finds branches/PRs referencing the plan issue
- Alias: `erk pr co`

### `erk pr teleport` (heavyweight, remote-first)

```
erk pr teleport <PR_NUMBER> [--new-slot] [-f/--force] [--sync] [--script]
```

- Force-resets local branch to match remote exactly
- `--sync` runs `gt submit --no-interactive` after teleport
- Two modes: in-place (default) or `--new-slot` for fresh worktree
- Shows divergence info and asks confirmation before overwriting

## Key Files

- `src/erk/cli/commands/pr/checkout_cmd.py` — checkout command
- `src/erk/cli/commands/pr/teleport_cmd.py` — teleport command
- `src/erk/cli/commands/checkout_helpers.py` — shared helpers
- `src/erk/cli/commands/exec/scripts/cmux_checkout_workspace.py` — cmux integration

## cmux-open-pr Command

The `cmux-open-pr` exec script (renamed from `cmux-checkout-workspace`) uses a `--mode` flag to select the operation:

```
erk exec cmux-open-pr --pr <NUMBER> [--branch <BRANCH>] [--mode {checkout|teleport}]
```

- `--mode checkout` (default): lightweight, runs `erk pr checkout {pr} --script`
- `--mode teleport`: heavyweight, runs `erk pr teleport {pr} --new-slot --script --sync`

## TUI Integration

The TUI has separate registry entries and keybindings for checkout and teleport, matching the CLI split.

## Decision Guide

| Scenario                          | Use                            |
| --------------------------------- | ------------------------------ |
| Review a PR locally               | `checkout`                     |
| Match remote after agent push     | `teleport`                     |
| Fresh worktree with Graphite sync | `teleport --new-slot --sync`   |
| CMUX workspace for quick review   | `cmux-open-pr --mode checkout` |
| CMUX workspace matching remote    | `cmux-open-pr --mode teleport` |
