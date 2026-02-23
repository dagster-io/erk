# Add `dispatch_workflow()` for Fire-and-Forget Workflow Launches

## Context

The TUI dashboard (`erk dash -i`) shells out to CLI commands like `erk launch pr-address --pr N` and `erk plan submit N -f` with a **30-second streaming timeout**. However, `trigger_workflow()` in the GitHub gateway polls for up to **~62 seconds** (11 attempts with exponential backoff) to discover the run ID after dispatching. This means the TUI kills the subprocess before it can even report success. The run URL and dispatch metadata updates that depend on the run ID are also lost.

The fix: add a new `dispatch_workflow()` gateway method that fires the workflow dispatch and returns immediately, plus a `--no-wait` CLI flag that the TUI passes to skip the polling.

## Approach: New `dispatch_workflow()` Method

Add a separate method rather than changing `trigger_workflow()`'s return type. This avoids touching the 8+ existing callers that use the run ID.

### Internal structure

```
_dispatch_workflow() -> str  (private, returns distinct_id)
    ├── dispatch_workflow() -> None   (public, fire-and-forget)
    └── trigger_workflow() -> str     (unchanged signature, calls _dispatch then polls)
```

## Implementation Steps

### 1. Gateway ABC — add `dispatch_workflow` abstract method

**File:** `packages/erk-shared/src/erk_shared/gateway/github/abc.py`

Add after `trigger_workflow` (line ~108):

```python
@abstractmethod
def dispatch_workflow(
    self, *, repo_root: Path, workflow: str, inputs: dict[str, str], ref: str | None = None
) -> None:
    """Dispatch a GitHub Actions workflow without waiting for the run to appear.

    Fire-and-forget variant of trigger_workflow(). Use when the caller
    does not need the run ID (e.g., TUI commands with tight timeouts).
    """
    ...
```

### 2. Real implementation — extract `_dispatch_workflow`, add `dispatch_workflow`

**File:** `packages/erk-shared/src/erk_shared/gateway/github/real.py`

- Extract lines 310–334 (distinct_id generation + `gh workflow run` invocation) into private `_dispatch_workflow() -> str` that returns the `distinct_id`.
- Add public `dispatch_workflow()` that calls `_dispatch_workflow()` and discards the ID.
- Refactor `trigger_workflow()` to call `_dispatch_workflow()` then run the existing polling loop using the returned `distinct_id`.

### 3. Fake implementation — add `dispatch_workflow` with tracking

**File:** `packages/erk-shared/src/erk_shared/gateway/github/fake.py`

- Add `_dispatched_workflows: list[tuple[str, dict[str, str]]]` tracking list to `__init__`.
- Add `dispatch_workflow()` that appends to the list (does NOT create a `WorkflowRun` entry — no run ID to track).
- Add `dispatched_workflows` property for test assertions.

### 4. DryRun implementation — no-op

**File:** `packages/erk-shared/src/erk_shared/gateway/github/dry_run.py`

Add `dispatch_workflow()` returning None (same pattern as existing `trigger_workflow` no-op at line 72).

### 5. Printing implementation — delegate with message

**File:** `packages/erk-shared/src/erk_shared/gateway/github/printing.py`

Add `dispatch_workflow()` that prints the command, notes "(fire-and-forget)", then delegates to `self._wrapped.dispatch_workflow(...)`.

### 6. CLI `erk launch` — add `--no-wait` flag

**File:** `src/erk/cli/commands/launch_cmd.py`

- Add `--no-wait` Click option to the `launch` command (line ~227).
- Thread `no_wait: bool` into `_trigger_pr_fix_conflicts`, `_trigger_pr_address`, `_trigger_learn`.
- When `no_wait`:
  - Call `ctx.github.dispatch_workflow(...)` instead of `ctx.github.trigger_workflow(...)`
  - Print "Workflow dispatched (fire-and-forget)" success message
  - Skip `maybe_update_plan_dispatch_metadata()` (no run_id)
  - Skip run URL printing (no run_id to construct URL from)

### 7. CLI `erk plan submit` — add `--no-wait` flag

**File:** `src/erk/cli/commands/submit.py`

- Add `--no-wait` Click option to the `submit_cmd` command.
- Thread `no_wait: bool` into `_submit_draft_pr_plan` and `_submit_single_issue`.
- When `no_wait`:
  - Call `ctx.github.dispatch_workflow(...)` instead of `ctx.github.trigger_workflow(...)`
  - Skip `write_dispatch_metadata()` (no run_id)
  - Skip PR body workflow-run-link update (no URL)
  - Skip workflow URL in queued event comment (or use "pending" text)
- Make `SubmitResult.workflow_run_id` and `workflow_url` optional (`str | None`).
- Update the summary output (line ~1312) to handle `None`: skip "Workflow:" line or print "Workflow dispatched (run ID pending)".

### 8. TUI — pass `--no-wait` to subprocess invocations

**File:** `src/erk/tui/app.py`

Add `"--no-wait"` to command lists for:
- `fix_conflicts_remote` (line ~908): `["erk", "launch", "pr-fix-conflicts", "--pr", str(row.pr_number), "--no-wait"]`
- `address_remote` (line ~937): `["erk", "launch", "pr-address", "--pr", str(row.pr_number), "--no-wait"]`
- `submit_to_queue` (line ~953): `["erk", "plan", "submit", str(row.plan_id), "-f", "--no-wait"]`

**File:** `src/erk/tui/screens/plan_detail_screen.py`

Same `"--no-wait"` additions for the duplicate command lists:
- `action_fix_conflicts_remote` (line ~372)
- `execute_command` handlers for `fix_conflicts_remote` (line ~701), `address_remote` (line ~709), `submit_to_queue` (line ~727)

**NOT changed:** The `copy_*` commands that copy CLI text for manual use should NOT include `--no-wait` since terminal users benefit from seeing the run URL.

### 9. Tests

- **New:** `tests/unit/core/github/test_dispatch_workflow.py` — test FakeGitHub tracks dispatched workflows, returns None, does not create WorkflowRun entries.
- **Update:** Tests for `launch_cmd` and `submit_cmd` that exercise the `--no-wait` flag and verify `dispatch_workflow` is called.

## Files Modified

| File | Change |
|------|--------|
| `packages/erk-shared/.../github/abc.py` | Add `dispatch_workflow` abstract method |
| `packages/erk-shared/.../github/real.py` | Extract `_dispatch_workflow`, add `dispatch_workflow`, refactor `trigger_workflow` |
| `packages/erk-shared/.../github/fake.py` | Add `dispatch_workflow` + tracking |
| `packages/erk-shared/.../github/dry_run.py` | Add `dispatch_workflow` no-op |
| `packages/erk-shared/.../github/printing.py` | Add `dispatch_workflow` with printing |
| `src/erk/cli/commands/launch_cmd.py` | Add `--no-wait` flag, conditional dispatch |
| `src/erk/cli/commands/submit.py` | Add `--no-wait` flag, make SubmitResult fields optional |
| `src/erk/tui/app.py` | Pass `--no-wait` to subprocess commands |
| `src/erk/tui/screens/plan_detail_screen.py` | Pass `--no-wait` to subprocess commands |

## Verification

1. **Unit tests:** Run `make fast-ci` — new tests for `dispatch_workflow`, updated tests for `--no-wait` paths.
2. **Manual TUI test:** `erk dash -i`, select a plan with a PR, press `l` then `a` (address remote) — should complete in <5 seconds instead of timing out at 30s.
3. **Manual CLI test:** `erk launch pr-address --pr N --no-wait` — should print "Workflow dispatched" immediately. Without `--no-wait`, existing behavior unchanged.
4. **Regression:** `erk launch pr-address --pr N` (without `--no-wait`) — should still poll and print run URL as before.
