# Show planning run ID in TUI dashboard

## Context

Planning-stage PRs created via MCP/one-shot workflow store `created_from_workflow_run_url` in their plan-header metadata, but the TUI dashboard "run" column only displays workflow runs looked up via `last_dispatched_node_id`. Since planning PRs haven't been dispatched yet, `last_dispatched_node_id` is None, and the run column shows "-" — even though the planning workflow run URL is available in metadata.

## Approach

Add a fallback in `_build_row_data()` to extract the run ID from `created_from_workflow_run_url` when no dispatched workflow run exists. This is purely a display-layer change — no API calls, no service layer changes.

### File: `src/erk/tui/data/real_provider.py`

In `_build_row_data()` (around line 641), after the `if workflow_run is not None:` block, add an `elif` that:

1. Reads `CREATED_FROM_WORKFLOW_RUN_URL` from `plan.header_fields` via `header_str()`
2. Parses the run ID from the URL (format: `https://github.com/{owner}/{repo}/actions/runs/{run_id}`)
3. Sets `run_id`, `run_url`, and `run_id_display` (plain text, no Rich link since we don't have a `WorkflowRun` object for `format_workflow_run_id`)
4. Leaves `run_status`, `run_conclusion` as None and `run_state_display` as "-" (we don't know status without an API call, which is fine for planning runs)

Add import for `CREATED_FROM_WORKFLOW_RUN_URL` from `erk_shared.gateway.github.metadata.schemas`.

### File: `tests/tui/test_real_provider.py` (or equivalent)

Add a test case for a plan with `created_from_workflow_run_url` in header_fields but no dispatched workflow run, verifying the run_id and run_url are populated.

## Verification

1. Run existing TUI tests: `pytest tests/tui/`
2. Run `erk dash` and verify planning-stage PRs show run IDs
3. Verify impl-stage PRs with dispatched runs still show correctly (no regression)
