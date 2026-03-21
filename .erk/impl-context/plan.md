# Plan: `erk exec objective-execute-plan` — Sequential Stacked Execution Skeleton

## Context

We want to autonomously execute an objective as a Graphite stack of PRs. Each node in the objective's roadmap becomes a PR that builds on the previous node's branch, forming a linear stack.

The first step is proving the mechanics: an exec script that resolves the next N nodes from the dependency graph in execution order, accounting for the fact that completing node 1 unblocks node 2. Dry-run / preview only — no actual dispatch.

## Implementation

### 1. Add `simulate_next_n()` to `DependencyGraph`

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py`

Add method to `DependencyGraph` class after `next_node()` (~line 100):

```python
def simulate_next_n(self, *, count: int) -> list[ObjectiveNode]:
```

Logic: repeatedly find `next_node()`, record it, replace it with a done-status copy in a working list, rebuild graph, repeat. Returns original (pending-status) nodes. Pure function, no mutation.

### 2. Create exec script `objective_execute_plan.py`

**File:** `src/erk/cli/commands/exec/scripts/objective_execute_plan.py` (new)

Command: `erk exec objective-execute-plan <objective_number> --count N [--json]`

Follows the exec script pattern (Click command, `@click.pass_context`, context helpers):

1. Fetch + validate objective via `validate_objective()`
2. Build dependency graph
3. Call `graph.simulate_next_n(count=count)`
4. Enrich with phase names
5. Output numbered execution plan (text or JSON)

JSON output format:
```json
{
  "objective": 42,
  "nodes": [
    {"position": 1, "id": "1.1", "description": "...", "phase": "Foundation", "slug": "..."},
    {"position": 2, "id": "1.2", "description": "...", "phase": "Foundation", "slug": "..."}
  ],
  "total_pending": 5,
  "requested": 3,
  "resolved": 2
}
```

Text output:
```
Execution plan for objective #42 (2 of 3 requested nodes resolved):

  1. [1.1] Add user model (Phase: Foundation)
  2. [1.2] Add user API endpoint (Phase: Foundation)
```

### 3. Unit tests for `simulate_next_n()`

**File:** `tests/unit/gateway/github/metadata/test_dependency_graph.py`

Tests using existing `_make_node` helper:
- Linear chain, request N < total → returns first N in order
- Cross-phase unblocking
- Request more than available → returns only available
- Skips non-pending nodes (done, in_progress)
- Complete graph → empty list
- `count=1` matches `next_node()`

### 4. Test for exec script

**File:** `tests/unit/cli/commands/exec/scripts/test_objective_execute_plan.py` (new)

Uses `CliRunner` + `ErkContext.for_test()` with `FakeRemoteGitHub` that returns a valid objective with roadmap. Verifies JSON output structure and node ordering.

## Key Files

| File | Action |
|------|--------|
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py` | Edit: add `simulate_next_n()` |
| `src/erk/cli/commands/exec/scripts/objective_execute_plan.py` | Create |
| `tests/unit/gateway/github/metadata/test_dependency_graph.py` | Edit: add tests |
| `tests/unit/cli/commands/exec/scripts/test_objective_execute_plan.py` | Create |
| `src/erk/cli/commands/exec/scripts/objective_plan_setup.py` | Reference: exec script pattern |
| `src/erk/cli/commands/objective/plan_cmd.py` | Reference: resolution + phase enrichment |

## Verification

1. `uv run pytest tests/unit/gateway/github/metadata/test_dependency_graph.py` — simulate_next_n tests pass
2. `uv run pytest tests/unit/cli/commands/exec/scripts/test_objective_execute_plan.py` — script tests pass
3. `uv run ty check` — type checks pass
4. `uv run ruff check` — lint passes
