# Plan: Add `depends_on` to Roadmap Schema (Objective #7390, Node 1.1)

## Context

Part of **Objective #7390 — Parallel Dependency Graphs**. Currently, roadmap nodes in YAML only have `id`, `description`, `status`, `plan`, `pr`. Dependency information (`depends_on`) only exists on `ObjectiveNode` in the dependency graph layer, inferred at runtime by `graph_from_phases()`. This node adds explicit `depends_on` to the YAML schema so objectives can express fan-in/fan-out relationships that sequential phase ordering cannot represent.

## Key Design Decision: `None` vs `()` semantics

`RoadmapNode.depends_on` will be `tuple[str, ...] | None`:
- **`None`** = not specified in YAML (v2 backward compat — infer via `graph_from_phases`)
- **`()`** = explicitly no dependencies (root node in fan-out graph)
- **`("1.1", "2.1")`** = depends on these specific nodes (fan-in)

The serializer omits `depends_on` from YAML when it's `None`, preserving backward compatibility with v2 bodies. When any node has `depends_on is not None`, the serializer writes it for all nodes.

## Implementation

### Step 1: Update `RoadmapNode` dataclass

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`

Add field to `RoadmapNode`:
```python
@dataclass(frozen=True)
class RoadmapNode:
    id: str
    description: str
    status: RoadmapNodeStatus
    plan: str | None
    pr: str | None
    depends_on: tuple[str, ...] | None  # None = not specified, () = no deps
```

### Step 2: Update parser (`validate_roadmap_frontmatter`)

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py` (line ~93-143)

In the per-step parsing loop, after reading `raw_pr`:
- Read `raw_depends_on = step_dict.get("depends_on")`
- If present: validate it's a `list[str]`, convert to `tuple[str, ...]`
- If absent: set to `None`
- Pass to `RoadmapNode` constructor

### Step 3: Update serializer (`render_roadmap_block_inner`)

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py` (line ~183-212)

In the dict comprehension building node data:
- Check if ANY node in the list has `depends_on is not None`
- If so: write `depends_on` for ALL nodes (using `list(s.depends_on)` or `[]`)
- If not: omit `depends_on` entirely (backward compat)

### Step 4: Update `serialize_phases`

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py` (line ~542-561)

Add `depends_on` to the per-step dict (as `list` or `None`).

### Step 5: Update `nodes_from_graph` to preserve `depends_on`

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py` (line ~108-123)

Currently strips `depends_on` when converting `ObjectiveNode` → `RoadmapNode`. Update to preserve it:
```python
depends_on=node.depends_on
```

### Step 6: Add `graph_from_nodes` function

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py`

New function that builds a `DependencyGraph` directly from `RoadmapNode` objects with explicit `depends_on`:
```python
def graph_from_nodes(nodes: list[RoadmapNode]) -> DependencyGraph:
    """Build DependencyGraph from nodes with explicit depends_on fields."""
```

Uses `node.depends_on` directly instead of inferring from phase ordering.

### Step 7: Update `parse_graph` to use explicit deps when available

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py` (line ~195-213)

After parsing phases, check if any node has `depends_on is not None`:
- If yes: flatten nodes and use `graph_from_nodes()`
- If no: use `graph_from_phases()` (backward compat)

### Step 8: Update all `RoadmapNode` constructor callsites

Every existing `RoadmapNode(...)` call needs `depends_on=None` added:

- `roadmap.py:validate_roadmap_frontmatter()` — handled in Step 2 (reads from YAML)
- `roadmap.py:update_node_in_frontmatter()` — uses `replace()`, auto-preserves new field
- `objective_render_roadmap.py:_render_roadmap()` — pass `depends_on=None`
- `dependency_graph.py:nodes_from_graph()` — handled in Step 5

### Step 9: Update tests

**Files to update (add `depends_on=None` to existing constructors):**
- `packages/erk-shared/tests/unit/github/metadata/test_roadmap.py`
- `packages/erk-shared/tests/unit/github/metadata/test_roadmap_frontmatter.py`
- `packages/erk-shared/tests/unit/github/metadata/test_dependency_graph.py`

**New tests to add:**

In `test_roadmap_frontmatter.py`:
- `test_parse_with_depends_on` — YAML with `depends_on` → populated field
- `test_parse_without_depends_on` — YAML without `depends_on` → `None`
- `test_render_with_depends_on` — nodes with `depends_on` → YAML includes field
- `test_render_without_depends_on` — nodes with `None` depends_on → YAML omits field
- `test_roundtrip_with_depends_on` — parse → render → parse preserves deps
- `test_validate_depends_on_not_list_rejected` — invalid `depends_on` type
- `test_validate_depends_on_non_string_items_rejected` — invalid item types
- `test_update_node_preserves_depends_on` — `update_node_in_frontmatter` roundtrip

In `test_dependency_graph.py`:
- `test_graph_from_nodes_explicit_deps` — builds graph from explicit deps
- `test_graph_from_nodes_fan_out` — two nodes depend on same parent
- `test_graph_from_nodes_fan_in` — one node depends on two parents
- `test_parse_graph_uses_explicit_deps_when_present`
- `test_parse_graph_falls_back_to_inferred_deps`
- `test_nodes_from_graph_preserves_depends_on`

## Files Modified

| File | Changes |
|------|---------|
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py` | Add `depends_on` to `RoadmapNode`, update parser/serializer/serialize_phases |
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py` | Add `graph_from_nodes()`, update `parse_graph()`, update `nodes_from_graph()` |
| `src/erk/cli/commands/exec/scripts/objective_render_roadmap.py` | Add `depends_on=None` to `RoadmapNode` constructors |
| `packages/erk-shared/tests/unit/github/metadata/test_roadmap.py` | Add `depends_on=None` to all constructors |
| `packages/erk-shared/tests/unit/github/metadata/test_roadmap_frontmatter.py` | Add `depends_on=None` to all constructors + new tests |
| `packages/erk-shared/tests/unit/github/metadata/test_dependency_graph.py` | Update `_step` helper + new tests |

## Verification

1. Run unit tests: `pytest packages/erk-shared/tests/unit/github/metadata/test_roadmap.py packages/erk-shared/tests/unit/github/metadata/test_roadmap_frontmatter.py packages/erk-shared/tests/unit/github/metadata/test_dependency_graph.py tests/unit/cli/commands/exec/scripts/test_objective_render_roadmap.py -v`
2. Run type checker: `ty check packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py`
3. Run linter: `ruff check packages/erk-shared/src/erk_shared/gateway/github/metadata/`
4. Verify backward compat: existing v2/v3 YAML bodies (without `depends_on`) still parse correctly via existing tests
5. Verify round-trip: YAML with `depends_on` → parse → render → parse preserves data