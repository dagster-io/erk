# Plan: End-to-End Fan-Out/Fan-In Verification

Part of Objective #7390, Node 1.4

## Context

Schema v3 introduced `depends_on` on roadmap nodes (PR #7471), enabling non-sequential dependency graphs (fan-out, fan-in). The graph construction functions (`graph_from_nodes`, `graph_from_phases`) and the smart dispatcher (`parse_graph`) work correctly. However, **4 call sites** bypass `parse_graph` and call `graph_from_phases` directly, which infers sequential dependencies and silently ignores explicit `depends_on` fields. This means the `view`, `check`, `plan`, and `fetch-context` commands all show incorrect unblocked status for parallel-dependency objectives.

## Phase 1: Add `build_graph()` helper and fix all call sites

### 1A. Add `build_graph()` to `dependency_graph.py`

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py`

Add between `graph_from_nodes()` (line 126) and `nodes_from_graph()` (line 129):

```python
def build_graph(phases: list[RoadmapPhase]) -> DependencyGraph:
    """Build graph from phases, using explicit deps when available."""
    all_nodes = [node for phase in phases for node in phase.nodes]
    has_explicit_deps = any(node.depends_on is not None for node in all_nodes)
    if has_explicit_deps:
        return graph_from_nodes(all_nodes)
    return graph_from_phases(phases)
```

Then refactor `parse_graph()` to delegate to `build_graph(phases)` instead of duplicating the dispatch logic.

### 1B. Fix 4 call sites

Replace `graph_from_phases(phases)` → `build_graph(phases)` and update imports:

| File | Line | Current | Fixed |
|------|------|---------|-------|
| `src/erk/cli/commands/objective/view_cmd.py` | 205 | `graph_from_phases(phases)` | `build_graph(phases)` |
| `src/erk/cli/commands/objective/check_cmd.py` | 123 | `graph_from_phases(phases)` | `build_graph(phases)` |
| `src/erk/cli/commands/objective/plan_cmd.py` | 54 | `graph_from_phases(phases)` | `build_graph(phases)` |
| `src/erk/cli/commands/exec/scripts/objective_fetch_context.py` | 99 | `graph_from_phases(phases)` | `build_graph(phases)` |

## Phase 2: Tests

### 2A. Unit tests for `build_graph()`

**File:** `packages/erk-shared/tests/unit/github/metadata/test_dependency_graph.py`

Add `TestBuildGraph` class with:
- `test_uses_explicit_deps_when_present` — fan-out nodes with explicit deps, verify both children unblocked simultaneously
- `test_falls_back_to_inferred_deps` — nodes with `depends_on=None`, verify sequential inference
- `test_fan_out_unblocked_simultaneously` — 1 parent (done) + 2 children → both children unblocked
- `test_fan_in_blocked_until_all_parents_done` — 2 parents (1 done, 1 pending) + 1 merge → merge blocked
- `test_fan_in_unblocked_when_all_parents_done` — 2 parents (both done) + 1 merge → merge unblocked
- `test_empty_phases` — empty input returns empty graph

### 2B. Round-trip test

**File:** `packages/erk-shared/tests/unit/github/metadata/test_dependency_graph.py`

Add `test_fan_out_fan_in_round_trip` — create nodes with fan-out + fan-in → render to YAML via `render_roadmap_block_inner()` → parse back via `parse_graph()` → verify `depends_on` preserved and unblocked nodes correct.

### 2C. view_cmd tests with fan-out/fan-in

**File:** `tests/unit/cli/commands/objective/test_view_cmd.py`

Add schema v3 fixture `OBJECTIVE_WITH_FAN_OUT_FAN_IN` with:
- Node 1.1 (done, no deps)
- Node 2.1, 2.2 (pending, both depend on 1.1 — fan-out)
- Node 3.1 (pending, depends on 2.1 + 2.2 — fan-in)

Tests:
- `test_view_fan_out_json_shows_multiple_unblocked` — JSON output has 2.1 and 2.2 in `unblocked` array
- `test_view_fan_out_human_shows_unblocked_status` — human output shows "pending (unblocked)" for both 2.1 and 2.2

### 2D. check_cmd tests with fan-out/fan-in

**File:** `tests/unit/cli/commands/objective/test_check_cmd.py`

- `test_fan_out_fan_in_passes_validation` — objective with explicit deps validates successfully
- `test_fan_out_fan_in_json_output` — JSON has correct next_node and summary

## Verification

1. Run `pytest packages/erk-shared/tests/unit/github/metadata/test_dependency_graph.py` — new `build_graph` + round-trip tests
2. Run `pytest tests/unit/cli/commands/objective/test_view_cmd.py` — new + existing view tests
3. Run `pytest tests/unit/cli/commands/objective/test_check_cmd.py` — new + existing check tests
4. Run `make fast-ci` — full unit test suite for regressions

## Files Modified

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py` | Add `build_graph()`, refactor `parse_graph()` |
| `src/erk/cli/commands/objective/view_cmd.py` | Import + call site fix |
| `src/erk/cli/commands/objective/check_cmd.py` | Import + call site fix |
| `src/erk/cli/commands/objective/plan_cmd.py` | Import + call site fix |
| `src/erk/cli/commands/exec/scripts/objective_fetch_context.py` | Import + call site fix |
| `packages/erk-shared/tests/unit/github/metadata/test_dependency_graph.py` | `TestBuildGraph` + round-trip test |
| `tests/unit/cli/commands/objective/test_view_cmd.py` | Fan-out/fan-in tests |
| `tests/unit/cli/commands/objective/test_check_cmd.py` | Fan-out/fan-in tests |