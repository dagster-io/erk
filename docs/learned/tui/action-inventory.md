---
title: TUI Action Command Inventory
read_when:
  - "adding actions to the dashboard"
  - "understanding TUI command execution patterns"
  - "replicating TUI functionality in another frontend"
last_audited: "2026-02-05"
audit_result: edited
---

# TUI Action Command Inventory

Complete inventory of all TUI commands. See `src/erk/tui/commands/registry.py` for the canonical command definitions with availability predicates and execution patterns.

## Command Categories

| Category | Count | Purpose                                         |
| -------- | ----- | ----------------------------------------------- |
| ACTION   | 5     | Mutative operations (close, submit, land, etc.) |
| OPEN     | 3     | Browser navigation                              |
| COPY     | 6     | Clipboard operations                            |

**Total:** 14 commands

## ACTION Commands (5)

| Command              | Display                                        | Shortcut | Availability              | Execution         |
| -------------------- | ---------------------------------------------- | -------- | ------------------------- | ----------------- |
| close_plan           | `erk plan close <issue_number>`                | —        | Always                    | In-process HTTP   |
| submit_to_queue      | `erk plan submit <issue_number>`               | `s`      | Has issue URL             | In-process HTTP   |
| land_pr              | `erk land <pr_number>`                         | —        | Open PR with workflow run | Subprocess (600s) |
| fix_conflicts_remote | `erk launch pr-fix-conflicts --pr <pr_number>` | `5`      | Has PR                    | Subprocess (600s) |
| address_remote       | `erk launch pr-address --pr <pr_number>`       | —        | Has PR                    | Subprocess (600s) |

## OPEN Commands (3)

| Command    | Shortcut | Availability  | Action          |
| ---------- | -------- | ------------- | --------------- |
| open_issue | `i`      | Has issue URL | Open in browser |
| open_pr    | `p`      | Has PR URL    | Open in browser |
| open_run   | `r`      | Has run URL   | Open in browser |

## COPY Commands (6)

| Command               | Display                                            | Shortcut | Availability  |
| --------------------- | -------------------------------------------------- | -------- | ------------- |
| copy_checkout         | `erk br co <branch>` or `erk pr co <pr_number>`    | `c`      | Has branch    |
| copy_pr_checkout      | `source "$(erk pr checkout <pr> --script)" && ...` | `e`      | Has PR        |
| copy_prepare          | `erk prepare <issue_number>`                       | `1`      | Always        |
| copy_prepare_activate | `source "$(erk prepare <issue> --script)" && ...`  | `4`      | Always        |
| copy_submit           | `erk plan submit <issue_number>`                   | `3`      | Always        |
| copy_replan           | `erk plan replan <issue_number>`                   | `6`      | Has issue URL |

## Execution Patterns

Three execution patterns across all commands:

- **In-process HTTP** (2 commands): Fast operations completing in <500ms
- **Subprocess Streaming** (3 commands): Long-running operations up to 600s with real-time output
- **Browser/Clipboard** (9 commands): Instant operations

## Command Context

All commands receive a `CommandContext` with the selected `PlanRowData` row and `PlanDataProvider` interface. See `src/erk/tui/commands/types.py` for the type definition.

## Related Documentation

- [TUI Data Contract Reference](data-contract.md) - PlanRowData fields that commands operate on
- [TUI Command Execution](command-execution.md) - Implementation details of execution patterns
- [TUI Streaming Output](streaming-output.md) - Cross-thread UI updates for streaming commands
- [Desktop Dashboard Interaction Model](../desktop-dash/interaction-model.md) - How commands translate to desktop UI
