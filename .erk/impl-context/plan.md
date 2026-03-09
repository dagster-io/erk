# Fix: Incremental dispatch does not update plan-header dispatch metadata

## Context

When `erk exec incremental-dispatch` triggers a workflow run against a PR, the dashboard's `run-id` and `run` columns show nothing because the plan-header metadata is never updated. Regular `erk pr dispatch` calls `write_dispatch_metadata()` after triggering the workflow, which writes `last_dispatched_run_id`, `last_dispatched_node_id`, and `last_dispatched_at` to the PR's plan-header metadata block. The TUI dashboard reads these fields to display workflow run status. Incremental dispatch skips this step entirely.

## Fix

Add a best-effort `write_dispatch_metadata()` call to `incremental_dispatch.py` after the workflow is triggered, matching the pattern used in `dispatch_cmd.py` lines 308-322.

### File: `src/erk/cli/commands/exec/scripts/incremental_dispatch.py`

After line 181 (`user_output("Workflow dispatched")`), add:

```python
# Update plan-header dispatch metadata (best-effort)
try:
    plan_backend = require_plan_backend(ctx)
    write_dispatch_metadata(
        plan_backend=plan_backend,
        github=github,
        repo_root=repo_root,
        plan_number=pr_number,
        run_id=run_id,
        dispatched_at=time.now().isoformat(),
    )
    user_output(click.style("✓", fg="green") + " Dispatch metadata written")
except Exception as e:
    user_output(
        click.style("Warning: ", fg="yellow") + f"Failed to update dispatch metadata: {e}"
    )
```

New imports needed:
- `from erk.cli.commands.pr.metadata_helpers import write_dispatch_metadata`
- `from erk_shared.context.helpers import require_plan_backend` (add to existing import)

### File: `tests/unit/cli/commands/exec/scripts/test_incremental_dispatch.py`

Add a test that verifies dispatch metadata gets written to the plan-header after a successful incremental dispatch. The existing `test_incremental_dispatch_success` test should be extended or a new test added to assert that `plan_backend.update_metadata()` was called with the run_id fields.

## Verification

1. Run `uv run pytest tests/unit/cli/commands/exec/scripts/test_incremental_dispatch.py`
2. Run `uv run ty check src/erk/cli/commands/exec/scripts/incremental_dispatch.py`
