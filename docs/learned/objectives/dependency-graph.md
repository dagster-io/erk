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

| Method              | Purpose                                                                    |
| ------------------- | -------------------------------------------------------------------------- |
| `unblocked_nodes()` | Returns nodes whose dependencies are all in terminal status (done/skipped) |
| `next_node()`       | Returns first unblocked pending node, or `None` if all complete            |
| `is_complete()`     | Returns `True` if all nodes are in terminal status                         |

Terminal statuses: `{"done", "skipped"}`.

## Conversion Functions

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

## Related Topics

- [Objective Lifecycle](objective-lifecycle.md) - Overall objective mutation flow
- [Roadmap Status System](roadmap-status-system.md) - Two-tier status resolution
