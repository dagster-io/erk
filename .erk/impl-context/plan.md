# Show Workflow Run Data in Objective Nodes Screen

## Context

The objective nodes screen (`erk dash` → select objective → nodes view) displays columns for `run-id`, `run`, and `chks` but they always show `-`. The root cause: `fetch_prs_by_ids()` in `real_provider.py` hardcodes `workflow_run=None` when building row data for each planned PR. The main `fetch_prs()` method fetches workflow runs via GraphQL, but `fetch_prs_by_ids()` skips this step entirely. Additionally, the "n" key (open run in browser) has no binding in this screen.

## Changes

### 1. Fetch workflow runs in `fetch_prs_by_ids()`

**File:** `src/erk/tui/data/real_provider.py` (lines 370-406)

The method already fetches planned PRs and converts them to `Plan` objects (which have parsed `header_fields` including `last_dispatched_node_id`). We need to:

1. Extract `last_dispatched_node_id` from each planned PR's header fields
2. Batch-query workflow runs via the existing GraphQL infrastructure
3. Pass the matched workflow run to `_build_row_data()` instead of `None`

**Add imports:**
- `LAST_DISPATCHED_NODE_ID` — add to existing schemas import
- `from erk_shared.gateway.github.graphql_queries import GET_WORKFLOW_RUNS_BY_NODE_IDS_QUERY`
- `from erk_shared.gateway.github.pr_data_parsing import parse_workflow_runs_nodes_response`

**Add between planned PR fetch and row building** (after line 388):

```python
# Extract dispatch node IDs from planned PRs for workflow run lookup
node_id_to_pr: dict[str, int] = {}
for plan in plans:
    node_id = header_str(plan.header_fields, LAST_DISPATCHED_NODE_ID)
    if node_id is not None:
        node_id_to_pr[node_id] = int(plan.pr_identifier)

# Batch fetch workflow runs via GraphQL
workflow_runs: dict[int, WorkflowRun | None] = {}
if node_id_to_pr:
    try:
        node_ids = list(node_id_to_pr.keys())
        response = self._http_client.graphql(
            query=GET_WORKFLOW_RUNS_BY_NODE_IDS_QUERY,
            variables={"nodeIds": node_ids},
        )
        runs_by_node_id = parse_workflow_runs_nodes_response(response, node_ids)
        for node_id, run in runs_by_node_id.items():
            workflow_runs[node_id_to_pr[node_id]] = run
    except Exception as e:
        logger.warning("Failed to fetch workflow runs in fetch_prs_by_ids: %s", e)
```

**Change line 399** from `workflow_run=None` to `workflow_run=workflow_runs.get(pr_number)`.

### 2. Add "n" key binding to ObjectiveNodesScreen

**File:** `src/erk/tui/screens/objective_nodes_screen.py`

- Add `Binding("n", "open_run", "Run", show=False)` to `BINDINGS` (after "p" binding)
- Add `action_open_run` method (same pattern as `action_open_pr`, using `row.run_url`)
- Update footer hint to include `n: run`

## Key files

- `src/erk/tui/data/real_provider.py` — core fix (workflow run fetching)
- `src/erk/tui/screens/objective_nodes_screen.py` — "n" binding + footer
- `packages/erk-shared/src/erk_shared/gateway/github/graphql_queries.py` — `GET_WORKFLOW_RUNS_BY_NODE_IDS_QUERY` (reuse)
- `packages/erk-shared/src/erk_shared/gateway/github/pr_data_parsing.py` — `parse_workflow_runs_nodes_response` (reuse)

## Verification

1. Run existing tests: `pytest tests/tui/data/test_provider.py`
2. Run `erk dash -i`, navigate to an objective with dispatched planned PRs, verify run-id/run/chks columns populate
3. Press "n" on a node with a run — should open GitHub Actions in browser
4. Press "n" on a node without a run — no-op (no crash)
