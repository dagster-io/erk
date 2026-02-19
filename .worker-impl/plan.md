# Plan: Add `--all-unblocked` Flag to `erk objective plan`

Part of Objective #7390, Node 2.1

## Context

Currently `erk objective plan --one-shot` dispatches exactly one node at a time (either the `--next` node or a specific `--node`). For objectives with fan-out dependency graphs, multiple nodes can become unblocked simultaneously after a parent completes. To leverage this parallelism, we need an `--all-unblocked` flag that discovers all pending unblocked nodes and dispatches a separate one-shot workflow for each.

## Design Decisions

1. **`--all-unblocked` implies `--one-shot`**: Interactive mode can only plan one node at a time. Rather than requiring `--one-shot --all-unblocked`, the flag implies one-shot mode automatically.
2. **Sequential dispatch loop**: Each node gets its own skeleton issue, branch, draft PR, and workflow trigger — dispatched sequentially in a loop (not parallelized). This reuses `dispatch_one_shot()` as-is.
3. **Individual node status updates**: Each node is marked "planning" after its dispatch. Atomic batching is deferred to Node 2.2.
4. **New `pending_unblocked_nodes()` method**: A small addition to `DependencyGraph` that returns all pending nodes whose deps are satisfied (vs `next_node()` which returns only the first).

## Implementation

### Phase 1: Add `pending_unblocked_nodes()` to DependencyGraph

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py`

Add method to `DependencyGraph`:

```python
def pending_unblocked_nodes(self) -> list[ObjectiveNode]:
    """All unblocked nodes with pending status, in position order."""
    return [node for node in self.unblocked_nodes() if node.status == "pending"]
```

This complements `next_node()` (returns first) and `unblocked_nodes()` (returns all statuses).

### Phase 2: Add `--all-unblocked` flag and handler to plan_cmd.py

**File:** `src/erk/cli/commands/objective/plan_cmd.py`

#### 2a. Add Click option

Add `--all-unblocked` flag to `plan_objective()`:

```python
@click.option(
    "--all-unblocked",
    "all_unblocked",
    is_flag=True,
    default=False,
    help="Dispatch all unblocked pending nodes via one-shot (one workflow per node)",
)
```

#### 2b. Validate flag combinations

In `plan_objective()`:
- `--all-unblocked` is mutually exclusive with `--node` and `--next`
- `--all-unblocked` implies `--one-shot` (if not set, auto-enable; warn if `--dry-run` or `--model` used without explicit `--one-shot` — actually these are fine since `--all-unblocked` implies it)
- When `--all-unblocked` is set, route to new `_handle_all_unblocked()`

#### 2c. Add `_resolve_all_unblocked()` function

New function parallel to `_resolve_next()`:

```python
@dataclass(frozen=True)
class ResolvedAllUnblocked:
    issue_number: int
    nodes: list[tuple[ObjectiveNode, str]]  # (node, phase_name) pairs
```

- Takes same args as `_resolve_next()` (ctx, issue_ref)
- Validates the objective exists
- Builds graph, gets `pending_unblocked_nodes()`
- Enriches phase names
- Returns all pending unblocked nodes with their phase names
- Raises `ClickException` if no pending unblocked nodes

#### 2d. Add `_handle_all_unblocked()` function

New function that:
1. Calls `_resolve_all_unblocked()` to get all pending unblocked nodes
2. Displays count and list of nodes being dispatched
3. Loops through each node:
   - Builds instruction (same format as `_handle_one_shot`)
   - Creates `OneShotDispatchParams` with `objective_issue` and `node_id`
   - Calls `dispatch_one_shot()`
   - On success, calls `_update_objective_node()` to mark as "planning"
4. Displays summary of dispatched nodes

#### 2e. Update codespace run passthrough

**File:** `src/erk/cli/commands/codespace/run/objective/plan_cmd.py`

Add `--all-unblocked` flag passthrough (same pattern as existing `-d` passthrough).

### Phase 3: Tests

#### 3a. DependencyGraph tests

**File:** `packages/erk-shared/tests/unit/github/metadata/test_dependency_graph.py`

Add tests for `pending_unblocked_nodes()`:
- Returns multiple pending nodes when fan-out allows it
- Excludes done/in_progress/skipped nodes
- Returns empty list when all nodes are done
- Returns empty list when pending nodes are blocked

#### 3b. Plan command tests

**File:** `tests/unit/cli/commands/objective/test_plan_cmd.py` (new file)

Test the core logic:
- `test_resolve_all_unblocked_returns_pending_nodes` — validates resolution
- `test_resolve_all_unblocked_no_pending_raises` — error case
- `test_all_unblocked_mutually_exclusive_with_node` — flag validation
- `test_all_unblocked_mutually_exclusive_with_next` — flag validation
- `test_handle_all_unblocked_dispatches_each_node` — integration test with fakes
- `test_handle_all_unblocked_dry_run` — shows preview without dispatching
- `test_all_unblocked_updates_objective_nodes` — verifies each node marked "planning"

#### 3c. Codespace passthrough test

**File:** `tests/unit/cli/commands/codespace/run/objective/test_plan_cmd.py`

Add test for `--all-unblocked` flag passthrough.

## Files Modified

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py` | Add `pending_unblocked_nodes()` method |
| `src/erk/cli/commands/objective/plan_cmd.py` | Add `--all-unblocked` flag, `_resolve_all_unblocked()`, `_handle_all_unblocked()` |
| `src/erk/cli/commands/codespace/run/objective/plan_cmd.py` | Add `--all-unblocked` passthrough |
| `packages/erk-shared/tests/unit/github/metadata/test_dependency_graph.py` | Tests for `pending_unblocked_nodes()` |
| `tests/unit/cli/commands/objective/test_plan_cmd.py` | New test file for plan_cmd logic |
| `tests/unit/cli/commands/codespace/run/objective/test_plan_cmd.py` | Add passthrough test |

## Verification

1. Run dependency graph tests: `pytest packages/erk-shared/tests/unit/github/metadata/test_dependency_graph.py`
2. Run plan command tests: `pytest tests/unit/cli/commands/objective/test_plan_cmd.py`
3. Run codespace passthrough tests: `pytest tests/unit/cli/commands/codespace/run/objective/test_plan_cmd.py`
4. Run ty type checker on modified files
5. Run ruff lint on modified files
6. Manual smoke test: `erk objective plan 7390 --all-unblocked --dry-run`