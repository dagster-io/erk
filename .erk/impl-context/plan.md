# Objective Nodes Detail Screen

## Context

The Objectives tab in `erk dash -i` shows a high-level row per objective with a sparkline and progress count, but there's no way to drill into individual nodes. The user wants a keyboard shortcut that opens a modal listing all nodes in the selected objective, showing PR status, CI checks, and run info for nodes with affiliated PRs.

## Approach

Add a new `ObjectiveNodesScreen` modal triggered by `b` ("breakdown") from the Objectives view. The screen parses the objective body to extract the dependency graph, then fetches PR details for nodes with PR references, displaying a rich node list.

## Files to Modify

### 1. New: `src/erk/tui/screens/objective_nodes_screen.py`

Create a modal screen following the `CheckRunsScreen` pattern:

- **Constructor**: Takes `provider: PlanDataProvider`, `plan_id: int`, `plan_body: str`, `full_title: str`
- **compose()**: Header with objective title, loading indicator, scrollable content area, footer
- **on_mount()**: Kicks off async `_fetch_nodes()` worker
- **_fetch_nodes()** (threaded worker):
  1. Parse objective body via `parse_graph(plan_body)` to get `DependencyGraph` and phases
  2. Collect PR numbers from nodes that have `node.pr` set (strip `#` prefix)
  3. Call `provider.fetch_plans_by_ids(pr_numbers)` to get `PlanRowData` for each PR
  4. Build a lookup dict: `pr_number -> PlanRowData`
  5. Call back to `_on_nodes_loaded()` on app thread
- **_on_nodes_loaded()**: Renders markdown table/list of nodes:
  - Columns: node ID, status symbol, description (truncated), PR#, PR state, checks, run state
  - Nodes without PRs show just ID, status, description
  - Use the same status symbols from `_STATUS_SYMBOLS` in `dependency_graph.py`

### 2. Modify: `src/erk/tui/app.py`

- Add binding: `Binding("b", "view_nodes", "Nodes", show=False)`

### 3. Modify: `src/erk/tui/actions/navigation.py`

- Import `ObjectiveNodesScreen`
- Add `action_view_nodes()`:
  - Guard: only works in `ViewMode.OBJECTIVES`
  - Get selected row, check `plan_body` is non-empty
  - Push `ObjectiveNodesScreen` with provider, plan_id, plan_body, full_title

### 4. Modify: `src/erk/tui/screens/help_screen.py`

- Add `b       View objective nodes` under Actions section

### 5. Modify: `tests/fakes/plan_data_provider.py` (if needed for `fetch_plans_by_ids`)

- Ensure `FakePlanDataProvider.fetch_plans_by_ids()` works for testing

### 6. New: `tests/tui/screens/test_objective_nodes_screen.py`

- Unit test for `_format_node_line()` and the rendering logic
- Integration test using `FakePlanDataProvider` with canned objective body + PR data

## Key Reusable Code

- `parse_graph()` from `erk_shared.gateway.github.metadata.dependency_graph` — parses body into graph + phases
- `_STATUS_SYMBOLS` from same module — node status symbols (already used in sparkline)
- `PlanDataProvider.fetch_plans_by_ids()` — fetches PR data for a set of plan/PR numbers
- `CheckRunsScreen` pattern — async loading modal with threaded worker (template for new screen)
- `find_graph_next_node()` — identifies the next actionable node (for highlighting)

## Display Format

Each node rendered as a markdown list item:

```
## Phase 1: Foundation
- **1.1** done   Scaffold project structure           #8701 MERGED  checks:5/5
- **1.2** done   Add core gateway ABC                 #8705 MERGED  checks:5/5

## Phase 2: Implementation
- **2.1** in_progress  Build CLI commands              #8710 OPEN   checks:3/5  run:in_progress
- **2.2** pending      Add TUI integration             -
- **2.3** pending      Write documentation              -
```

Nodes grouped by phase. Next actionable node highlighted (e.g., bold or colored marker).

## Verification

1. Run `erk dash -i`, switch to Objectives view (press `3`)
2. Select an objective with nodes, press `b`
3. Verify modal shows all nodes with correct statuses
4. Verify nodes with PRs show PR state, check counts, run state
5. Press Esc/q/Space to close
6. Press `?` to verify help screen shows the new binding
7. Run tests: `make fast-ci`
