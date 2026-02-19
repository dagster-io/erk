---
title: Dependency Graph Architecture
read_when:
  - "working with ObjectiveNode or DependencyGraph types"
  - "implementing dependency-aware step traversal"
  - "converting between roadmap phases and graph representations"
tripwires:
  - action: "using find_next_node() for dependency-aware traversal"
    warning: "Use DependencyGraph.next_node() instead. find_next_node() is position-based and ignores dependencies."
  - action: "using ObjectiveValidationSuccess.graph without checking issue_body for enrichment"
    warning: "ObjectiveValidationSuccess includes issue_body specifically for phase name enrichment. Pass result.issue_body to enrich_phase_names() when you need phase names in display contexts."
last_audited: "2026-02-17 00:00 PT"
audit_result: clean
---

# Dependency Graph Architecture

The dependency graph converts flat roadmap phases into a directed acyclic graph (DAG) where nodes have explicit dependency edges. This enables dependency-aware traversal instead of position-based step selection.

## Types

**Location:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py`

### ObjectiveNode

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py, ObjectiveNode -->

Frozen dataclass representing a single step in the dependency graph. See `ObjectiveNode` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py`. Fields: `id`, `description`, `status`, `plan`, `pr`, `depends_on`.

### DependencyGraph

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py, DependencyGraph -->

Frozen dataclass containing a tuple of `ObjectiveNode` with traversal methods. See `DependencyGraph` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py`.

**Key methods:**

| Method                      | Purpose                                                                               |
| --------------------------- | ------------------------------------------------------------------------------------- |
| `unblocked_nodes()`         | Returns nodes whose dependencies are all in terminal status (done/skipped)            |
| `pending_unblocked_nodes()` | Returns all unblocked nodes with "pending" status, in position order                  |
| `min_dep_status(node_id)`   | Returns the most blocking dependency status for a node (lowest `_STATUS_ORDER` value) |
| `next_node()`               | Returns first unblocked pending node, or `None` if all complete                       |
| `is_complete()`             | Returns `True` if all nodes are in terminal status                                    |

Terminal statuses: `{"done", "skipped"}`.

## Conversion Functions

### build_graph()

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py, build_graph -->

Preferred entry point for graph construction. Inspects nodes for explicit `depends_on` fields and delegates accordingly:

- If **any** node has explicit `depends_on`: uses `graph_from_nodes()` (preserves explicit dependencies)
- Otherwise: uses `graph_from_phases()` (infers sequential dependencies)

### graph_from_phases()

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py, graph_from_phases -->

Converts `list[RoadmapPhase]` into a `DependencyGraph`. See `graph_from_phases()` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py`.

**Dependency rules:**

- First step in a phase depends on the last step of the previous phase (if any)
- Subsequent steps in a phase depend on the previous step in the same phase
- This creates a linear chain within phases and sequential ordering between phases

### Round-Trip Conversion

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py, nodes_from_graph -->

See `nodes_from_graph()` and `phases_from_graph()` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py`.

**Phase name limitation:** `phases_from_graph()` returns placeholder phase names. Use `enrich_phase_names()` to restore actual names from body text. See `phase-name-enrichment.md` for details.

## Fallback Behavior: Pending -> In-Progress

`find_graph_next_node()` (in `view_cmd.py`) applies a two-tier fallback when selecting the next actionable node:

1. First, look for the first unblocked pending node via `graph.next_node()`
2. If no pending nodes exist, fall back to the first `in_progress` node from the phase list

This handles the common case where all steps have been dispatched (status = `in_progress`) but none have landed yet.

## Node Discovery Function Comparison

Three functions serve different next-node discovery needs:

| Function                 | Location              | Dependency-Aware | Fallback to in_progress | Use Case                                   |
| ------------------------ | --------------------- | ---------------- | ----------------------- | ------------------------------------------ |
| `find_next_node()`       | `roadmap.py`          | No               | No                      | Position-based, for simple roadmaps        |
| `find_graph_next_node()` | `view_cmd.py`         | Yes              | Yes                     | Display in `erk objective view`            |
| `graph.next_node()`      | `dependency_graph.py` | Yes              | No                      | Core graph traversal, returns pending only |

**Rule of thumb:** Use `graph.next_node()` for programmatic decisions (objective plan, implement). Use `find_graph_next_node()` for display contexts where showing an in-progress node is better than showing nothing.

## Usage Pattern

```python
from erk_shared.gateway.github.metadata.dependency_graph import (
    DependencyGraph,
    graph_from_phases,
)

graph = graph_from_phases(roadmap.phases)
next_node = graph.next_node()
if next_node is not None:
    # Implement this node
    ...
```

## Status Priority Order

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py:21-28 -->
<!-- See also: docs/learned/objectives/dependency-status-resolution.md -->

The `_STATUS_ORDER` dict assigns a numeric priority to each status. `min_dep_status()` uses this ordering to return the most blocking upstream dependency status — `pending` is lowest priority (most blocking), `done`/`skipped` are highest (least blocking). See the source or `dependency-status-resolution.md` for the full mapping.

## Related Topics

- [Objective Lifecycle](objective-lifecycle.md) - Overall objective mutation flow
- [Roadmap Status System](roadmap-status-system.md) - Two-tier status resolution
- [Dependency Status Resolution](dependency-status-resolution.md) - Display logic and fan-out dispatch
