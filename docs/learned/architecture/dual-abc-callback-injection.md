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

The TUI app bridges the two ABCs using lambda injection when constructing `RealCommandExecutor`:

```python
executor = RealCommandExecutor(
    browser_launch=self._provider.browser.launch,
    clipboard_copy=self._provider.clipboard.copy,
    close_plan_fn=self._provider.close_plan,
    notify_fn=self._notify_with_severity,
    refresh_fn=self.action_refresh,
    submit_to_queue_fn=self._provider.submit_to_queue,
    update_objective_fn=lambda oi, pn, br: self._update_objective_async(
        objective_issue=oi,
        pr_num=pn,
        branch=br,
    ),
)
```

<!-- Source: src/erk/tui/app.py, _push_streaming_detail -->

See `_push_streaming_detail()` in `src/erk/tui/app.py:519-558`.

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

`FakeCommandExecutor` tracks calls for assertion:

```python
class FakeCommandExecutor(CommandExecutor):
    def __init__(self):
        self.updated_objectives: list[tuple[int, int, str]] = []

    def update_objective_after_land(
        self, *, objective_issue, pr_num, branch
    ):
        self.updated_objectives.append((objective_issue, pr_num, branch))
```

## Related Topics

- [Modal Streaming Pattern](../tui/modal-streaming-pattern.md) - How streaming commands use CommandExecutor
- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) - General ABC implementation pattern
