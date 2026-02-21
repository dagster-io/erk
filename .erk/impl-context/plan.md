# Fix: Add `impl-signal submitted` to transition lifecycle to "implemented"

## Context

After successful implementation (local or remote), `lifecycle_stage` stays at `"planned"` / `"implementing"` instead of transitioning to `"implemented"`. This causes `erk dash` to show stale status.

**Root cause:** The `impl-signal` system only has `started` and `ended` events — `started` sets `"implementing"`, but `ended` only updates timestamps. There's no event for "PR successfully submitted", which is when `"implemented"` should be set. The local and remote paths have divergent post-implementation pipelines, so the fix needs a shared abstraction rather than two ad-hoc patches.

**Fix:** Add a new `impl-signal submitted` event that sets `lifecycle_stage: "implemented"`, called from both paths after PR submission succeeds.

## Changes

### 1. Add `submitted` event to `impl-signal`

**File:** `src/erk/cli/commands/exec/scripts/impl_signal.py`

- Add `_signal_submitted()` function following the pattern of `_signal_ended()`:
  - Read plan ref from `.impl/` (or `.worker-impl/`)
  - Build metadata dict with `"lifecycle_stage": "implemented"`
  - Call `backend.update_metadata()` (no comment needed — the PR is already visible)
  - Does NOT require `--session-id` (unlike `started`)
- Update `@click.argument("event", type=click.Choice(["started", "ended", "submitted"]))` (line 356)
- Add dispatch in `impl_signal()`: `elif event == "submitted": _signal_submitted(ctx, session_id)`

### 2. Call from local path

**File:** `.claude/commands/erk/plan-implement.md`

After Step 13 (`erk pr submit`), add:

```bash
erk exec impl-signal submitted 2>/dev/null || true
```

This goes after `erk pr submit` succeeds but before `erk pr check`.

### 3. Call from remote path

**File:** `.github/workflows/plan-implement.yml`

Add a new step after "Trigger CI workflows" (after line 451):

```yaml
    - name: Update lifecycle stage to implemented
      if: steps.implement.outputs.implementation_success == 'true' && steps.handle_outcome.outputs.has_changes == 'true' && (steps.submit.outcome == 'success' || steps.handle_conflicts.outcome == 'success')
      run: |
        erk exec impl-signal submitted
```

### 4. Add tests

**File:** `tests/unit/cli/commands/exec/scripts/test_impl_signal.py`

Add tests following existing patterns (using `CliRunner`, `ErkContext.for_test()`, `FakeGitHubIssues`):

- `test_submitted_updates_lifecycle_stage` — happy path, verify metadata contains `lifecycle_stage: "implemented"`
- `test_submitted_no_plan_ref` — error path, missing `.impl/`
- `test_submitted_no_session_id_ok` — verify `--session-id` is not required

### 5. Manually fix PR #7717

After deploying: `erk exec update-lifecycle-stage --plan-id 7717 --stage implemented`

## Key files

- `src/erk/cli/commands/exec/scripts/impl_signal.py` — main change
- `tests/unit/cli/commands/exec/scripts/test_impl_signal.py` — tests
- `.claude/commands/erk/plan-implement.md` — local path integration (Step 13)
- `.github/workflows/plan-implement.yml` — remote path integration (after line 451)

## Verification

1. Run `impl_signal` unit tests
2. Read modified files to confirm changes
3. Manually fix #7717 and confirm `erk dash` shows "implemented"
