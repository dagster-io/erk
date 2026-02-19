---
title: Dual ABC Callback Injection Pattern
read_when:
  - "adding a new command to the TUI CommandExecutor"
  - "bridging TUI callbacks between CommandExecutor and PlanDataProvider"
  - "understanding lambda parameter abbreviation in TUI app.py"
tripwires:
  - action: "importing PlanDataProvider in CommandExecutor or vice versa"
    warning: "These ABCs cannot directly reference each other due to circular imports. Use lambda injection to bridge them."
last_audited: "2026-02-19 00:00 PT"
audit_result: clean
---

# Dual ABC Callback Injection Pattern

The TUI needs both UI callback exposure (`CommandExecutor`) and subprocess execution (`PlanDataProvider`), but circular imports prevent direct coupling between these interfaces.

## Problem

`CommandExecutor` (defined in `packages/erk-shared/src/erk_shared/gateway/command_executor/abc.py`) defines operations that palette commands can perform (open URL, copy clipboard, close plan, update objective). `PlanDataProvider` provides the data layer. Both have overlapping operations (like `update_objective_after_land`), but neither can import the other.

## Solution: Lambda Injection

The TUI app bridges the two ABCs using lambda injection when constructing `RealCommandExecutor`. Each callback maps a `PlanDataProvider` method or app method to a `RealCommandExecutor` constructor parameter, with abbreviated lambda parameters for the `update_objective_fn` bridge.

<!-- Source: src/erk/tui/app.py, _push_streaming_detail -->

See `_push_streaming_detail()` in `src/erk/tui/app.py:519-558` for the full constructor call.

## Lambda Parameter Abbreviation Convention

Parameters in bridge lambdas are abbreviated to 2-3 characters, with immediate expansion to keyword arguments:

| Abbreviation | Full Parameter    |
| ------------ | ----------------- |
| `oi`         | `objective_issue` |
| `pn`         | `pr_num`          |
| `br`         | `branch`          |

This keeps the lambda on a single line while the keyword expansion makes the target method's API explicit.

## CommandExecutor ABC

<!-- Source: packages/erk-shared/src/erk_shared/gateway/command_executor/abc.py, CommandExecutor -->

The `CommandExecutor` ABC in `packages/erk-shared/src/erk_shared/gateway/command_executor/abc.py` defines these abstract methods:

| Method                          | Purpose                               |
| ------------------------------- | ------------------------------------- |
| `open_url()`                    | Open URL in browser                   |
| `copy_to_clipboard()`           | Copy text to clipboard                |
| `close_plan()`                  | Close plan and linked PRs             |
| `notify()`                      | Show notification to user             |
| `refresh_data()`                | Trigger data refresh                  |
| `update_objective_after_land()` | Update objective after landing a PR   |
| `submit_to_queue()`             | Submit plan for remote implementation |

## Testing

`FakeCommandExecutor` tracks calls for assertion by recording arguments to `updated_objectives` (and similar lists for other methods).

<!-- Source: packages/erk-shared/src/erk_shared/gateway/command_executor/fake.py, FakeCommandExecutor -->

See `FakeCommandExecutor` in `packages/erk-shared/src/erk_shared/gateway/command_executor/fake.py` for the full implementation.

## Related Topics

- [Modal Streaming Pattern](../tui/modal-streaming-pattern.md) - How streaming commands use CommandExecutor
- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) - General ABC implementation pattern
