# Plan: Stream Objective Updates in TUI After Landing

## Context

When landing a PR from the TUI dashboard, the objective update runs as a blind subprocess (`subprocess.run` with `stdout=PIPE, stdin=DEVNULL`). The user only sees toast notifications ("Updating objective #7813..." → "Objective #7813 updated") with zero visibility into what Claude is doing during the 7-step update workflow. This makes the operation feel unreliable — the user can't tell if prose reconciliation happened, which nodes were updated, or why it might have failed.

The fix: chain the objective update as a **second streaming command** in the same detail screen, just like the land-execute command itself. The user sees real-time output from both operations.

## Changes

### 1. `src/erk/tui/app.py` — Return detail screen + chain streaming command

**a)** `_push_streaming_detail`: Change return type from `None` to `PlanDetailScreen`, add `return detail_screen`.

**b)** `land_pr` handler (line 977): Replace `_update_objective_async` call with a chained `run_streaming_command` on the returned detail screen:

```python
def _on_land_success() -> None:
    self.action_refresh()
    if objective_issue is not None:
        detail_screen.run_streaming_command(
            [
                "erk", "exec", "objective-update-after-land",
                f"--objective={objective_issue}",
                f"--pr={pr_num}",
                f"--branch={branch}",
            ],
            cwd=self._provider.repo_root,
            title=f"Update Objective #{objective_issue}",
            timeout=300.0,
        )

detail_screen = self._push_streaming_detail(
    row=row,
    command=["erk", "exec", "land-execute", ...],
    title=f"Land PR #{pr_num}",
    timeout=600.0,
    on_success=_on_land_success,
)
```

Python closures are late-binding, so `detail_screen` is resolved when the callback runs (after `_push_streaming_detail` has returned), not when it's defined.

**c)** Remove `_update_objective_async` method (lines 538-567) — no longer called.

### 2. `src/erk/tui/screens/plan_detail_screen.py` — Chain streaming in execute_command

In `execute_command`'s `land_pr` handler (line 692), replace `self._executor.update_objective_after_land(...)` with `self.run_streaming_command(...)`:

```python
def _on_land_success() -> None:
    if self._executor is not None:
        self._executor.refresh_data()
    if objective_issue is not None and self._repo_root is not None:
        self.run_streaming_command(
            [
                "erk", "exec", "objective-update-after-land",
                f"--objective={objective_issue}",
                f"--pr={pr_num}",
                f"--branch={branch}",
            ],
            cwd=self._repo_root,
            title=f"Update Objective #{objective_issue}",
            timeout=300.0,
        )
```

### 3. Remove dead `update_objective_after_land` from gateway ABCs + implementations

With both TUI call sites converted to streaming, `update_objective_after_land` is unused:

- `packages/erk-shared/src/erk_shared/gateway/command_executor/abc.py` — Remove method
- `packages/erk-shared/src/erk_shared/gateway/command_executor/real.py` — Remove method + `update_objective_fn` constructor param
- `packages/erk-shared/src/erk_shared/gateway/command_executor/fake.py` — Remove method
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py` — Remove method
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` — Remove method
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py` — Remove method
- `src/erk/tui/app.py` — Remove `update_objective_fn=` from all `RealCommandExecutor(...)` calls (4 sites)

### 4. Update tests

- `tests/tui/commands/test_execute_command.py` — Update `test_land_pr_on_success_calls_update_objective` to verify `run_streaming_command` is called with the objective update command instead of `executor.update_objective_after_land()`
- `tests/fakes/` — Remove `update_objective_after_land` from fake executor/provider if no other tests reference it
- Any tests that construct `RealCommandExecutor` with `update_objective_fn` — remove parameter

## Visual Result

Before:
```
Land PR #7847 panel → "✓ Complete"
(toast) "Updating objective #7813..."
(toast) "Objective #7813 updated"  ← no detail
```

After:
```
Land PR #7847 panel → "✓ Complete"
Update Objective #7813 panel → streaming output:
  --- /erk:objective-update-with-landed-pr ... ---
    > Running erk exec objective-fetch-context...
    > Running erk exec update-objective-node...
    > Running erk exec objective-post-action-comment...
  --- Done (45s) ---
  ✓ Objective updated successfully
```

## How It Works

`run_streaming_command` can be called multiple times on the same `PlanDetailScreen`. Each call mounts a new `CommandOutputPanel` below the previous one. The worker thread captures its panel reference at start, so concurrent panels don't interfere. The `erk exec objective-update-after-land` script prints all Claude streaming events to stderr, which gets captured via `stderr=subprocess.STDOUT` in the Popen call.

## Verification

1. Land a PR linked to an objective from TUI dashboard — verify streaming output appears for both land and objective update
2. Land a PR with NO objective — verify no second panel appears
3. Land a PR where objective update fails — verify error is visible in the panel
4. Run existing TUI tests via `make fast-ci`
