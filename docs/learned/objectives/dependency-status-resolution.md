---
title: Dependency Status Resolution
read_when:
  - "implementing dependency status display in TUI"
  - "understanding how fan-out dispatch selects nodes"
  - "working with pending_unblocked_nodes or min_dep_status"
tripwires:
  - action: "using graph_from_phases() when nodes have explicit depends_on fields"
    warning: "Prefer build_graph() over graph_from_phases(). build_graph() detects explicit depends_on and delegates to graph_from_nodes() when appropriate."
  - action: "looping next_node() for fan-out dispatch"
    warning: "Use pending_unblocked_nodes() for fan-out dispatch. next_node() only returns a single node."
---

# Dependency Status Resolution

How objective node dependency statuses are resolved and displayed.

## Status Priority

The `_STATUS_ORDER` dict in `dependency_graph.py` defines priority ordering. See source for current values:

> `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py:21-28`

`min_dep_status(node_id)` returns the **lowest** status among a node's upstream dependencies (the most blocking one).

## Display Logic

The `objective_deps_display` field in `PlanRowData` shows the dependency status of the next node:

| Condition                           | Display                                                           |
| ----------------------------------- | ----------------------------------------------------------------- |
| No next node                        | `-`                                                               |
| Next node has no dependencies       | `ready`                                                           |
| All dependencies in terminal status | `ready`                                                           |
| Some dependencies non-terminal      | Status text of most blocking dep (e.g., `pending`, `in progress`) |

## Fan-Out Dispatch

The `--all-unblocked` flag on `erk objective plan` dispatches one-shot workflows for all pending unblocked nodes:

1. `_resolve_all_unblocked()` calls `graph.pending_unblocked_nodes()` to find all eligible nodes
2. Each node is dispatched sequentially via `dispatch_one_shot()` with objective context
3. After dispatch, the node's PR number is updated in the objective roadmap

**Source:** `_resolve_all_unblocked()` in `src/erk/cli/commands/objective/plan_cmd.py`

### When to Use Which

| Function                    | Use Case                                                  |
| --------------------------- | --------------------------------------------------------- |
| `pending_unblocked_nodes()` | Fan-out dispatch (all eligible nodes)                     |
| `next_node()`               | Single dispatch (first eligible node)                     |
| `unblocked_nodes()`         | All unblocked regardless of status (includes in_progress) |

## Related Topics

- [Dependency Graph Architecture](dependency-graph.md) - Graph types and traversal methods
- [Objective Lifecycle](objective-lifecycle.md) - Overall objective mutation flow
