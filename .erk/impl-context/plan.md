# Plan: Clear error when trigger_workflow finds a skipped/cancelled run

## Context

When `trigger_workflow` polls for a workflow run matching its correlation ID, it filters out runs with conclusion `"skipped"` or `"cancelled"`. This was intended to skip stale runs and keep polling for the "real" one, but when the matched run IS the triggered run (same distinct_id), the method polls all 15 attempts and then reports a confusing "could not find run ID" error — even though the run is visible in the diagnostics.

This happened with `learn.yml` when `vars.CLAUDE_ENABLED` was `'false'`, causing the job to skip instantly.

## Change

**File:** `packages/erk-shared/src/erk_shared/gateway/github/real.py`

In the `trigger_workflow` polling loop (lines ~380-391), restructure the matching logic:

1. When a run's displayTitle matches the distinct_id but its conclusion is `"skipped"` or `"cancelled"`, raise immediately with a clear error message explaining the run was found but skipped/cancelled, rather than continuing to poll.

2. The error message should include the workflow name, run ID, conclusion, and displayTitle so the user understands what happened.

Current code (lines 380-391):
```python
for run in runs_data:
    conclusion = run.get("conclusion")
    if conclusion in ("skipped", "cancelled"):
        continue
    display_title = run.get("displayTitle", "")
    if f":{distinct_id}" in display_title:
        run_id = run["databaseId"]
        return str(run_id)
```

New structure:
```python
for run in runs_data:
    display_title = run.get("displayTitle", "")
    if f":{distinct_id}" not in display_title:
        continue
    conclusion = run.get("conclusion")
    if conclusion in ("skipped", "cancelled"):
        # Matched run was skipped/cancelled — no point polling further
        raise RuntimeError(
            f"Workflow '{workflow}' run was {conclusion}.\n"
            f"Run ID: {run['databaseId']}, title: '{display_title}'\n"
            f"This usually means a job-level condition was not met "
            f"(e.g., vars.CLAUDE_ENABLED is 'false')."
        )
    run_id = run["databaseId"]
    return str(run_id)
```

## Verification

- `uv run pytest tests/unit/core/github/test_trigger_workflow.py` (existing tests still pass — they use FakeGitHub, unaffected)
- No new tests needed — this is a `RealGitHub` method that calls subprocess; the existing tests cover the fake. The fix is a control flow change in error reporting.
