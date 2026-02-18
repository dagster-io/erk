# Plan: Phase 3 — Rename Step→Node in Python types, fields, and functions

**Part of Objective #7391, Steps 3.1–3.4**

## Context

Objective #7391 migrates "step" terminology to "node" across the objective roadmap system. Phases 1–2 (display strings, functions, variables, dict keys) are complete via PRs #7385 and #7411. Phase 3 renames the core Python types, the `RoadmapPhase.steps` field, and three public functions. Phase 4 (YAML schema keys) is explicitly out of scope.

## Rename Map

| Old | New | Kind |
|-----|-----|------|
| `RoadmapStep` | `RoadmapNode` | class |
| `RoadmapStepStatus` | `RoadmapNodeStatus` | type alias |
| `RoadmapPhase.steps` | `RoadmapPhase.nodes` | field |
| `group_steps_by_phase()` | `group_nodes_by_phase()` | function |
| `update_step_in_frontmatter()` | `update_node_in_frontmatter()` | function |
| `steps_from_graph()` | `nodes_from_graph()` | function |

**NOT renamed (Phase 4):** YAML schema key `"steps"` in `validate_roadmap_frontmatter` and `render_roadmap_block_inner`.

## Approach: LibCST batch rename + targeted manual edits

### Step 1: LibCST batch rename — types and functions (3.1, 3.3)

Use `libcst-refactor` agent to rename across all files in `packages/erk-shared/src/`, `src/erk/`, and `packages/erk-shared/tests/`:

- `RoadmapStep` → `RoadmapNode` (class name, all imports, all type annotations, all constructor calls)
- `RoadmapStepStatus` → `RoadmapNodeStatus` (type alias, all imports, all type annotations)
- `group_steps_by_phase` → `group_nodes_by_phase` (function name, all imports, all call sites)
- `update_step_in_frontmatter` → `update_node_in_frontmatter` (function name, all imports, all call sites)
- `steps_from_graph` → `nodes_from_graph` (function name, all imports, all call sites)

### Step 2: Manual field rename — `RoadmapPhase.steps` → `.nodes` (3.2)

**`roadmap.py`** — Rename the field definition and all internal usages:
- Line 47: `steps: list[RoadmapStep]` → `nodes: list[RoadmapNode]`
- Lines 254, 262, 268: `phase_map[...].append(step)` etc — update to use `nodes`
- Lines 475, 482, 514, 547, 555, 565: `phase.steps` → `phase.nodes`
- Line 547 (`serialize_phases`): also rename the JSON dict key `"steps"` → `"nodes"`

**`dependency_graph.py`** — Update attribute accesses:
- Lines 85, 105, 106, 187: `phase.steps` → `phase.nodes`
- Special care at line 85: `for i, step in enumerate(phase.steps)` — rename loop var to `roadmap_node` to avoid conflict with `ObjectiveNode` local vars

**CLI/exec scripts** — Update any `.steps` accesses in:
- `view_cmd.py`, `plan_cmd.py`, `check_cmd.py`
- Exec scripts that reference `phase.steps`

**Test files** — Update `.steps` attribute accesses and assertions.

### Step 3: Parameter and local variable renames (3.4)

- `update_node_in_frontmatter`: rename param `step_id` → `node_id`
- Update docstrings referencing "step" terminology to say "node" where appropriate
- Rename local variables: `steps` → `nodes`, `step` → `node` in functions where unambiguous
- Keep `"steps"` string literals in YAML parsing unchanged (Phase 4 scope)

### Step 4: Update docs/learned/ references

Update documentation files that reference the old names:
- `docs/learned/objectives/roadmap-parser.md`
- `docs/learned/objectives/roadmap-parser-api.md`
- `docs/learned/objectives/phase-name-enrichment.md`
- `docs/learned/objectives/roadmap-format-versioning.md`
- `docs/learned/objectives/tripwires.md`
- `docs/learned/cli/commands/update-objective-node.md`

## Files Modified

**Production (7):**
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py`
- `src/erk/cli/commands/exec/scripts/objective_fetch_context.py`
- `src/erk/cli/commands/exec/scripts/update_objective_node.py`
- `src/erk/cli/commands/exec/scripts/objective_render_roadmap.py`
- `src/erk/cli/commands/objective/view_cmd.py`
- `src/erk/cli/commands/objective/plan_cmd.py`

**Tests (3):**
- `packages/erk-shared/tests/unit/github/metadata/test_roadmap.py`
- `packages/erk-shared/tests/unit/github/metadata/test_roadmap_frontmatter.py`
- `packages/erk-shared/tests/unit/github/metadata/test_dependency_graph.py`

**Docs (6):** See Step 4 above.

## Verification

1. `make fast-ci` — unit tests, ruff lint, ruff format, ty type check
2. Grep for leftover `RoadmapStep` (should only remain in comments about migration history if any)
3. Grep for `\.steps` attribute access (should only remain in non-roadmap contexts)
4. Grep for `group_steps_by_phase|update_step_in_frontmatter|steps_from_graph` — should return zero results