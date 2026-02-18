# Plan: Objective #7391 Phase 2 — Rename "step" to "node" in display strings, functions, variables, and dict keys

## Context

Part of **Objective #7391**, Steps 2.1–2.5.

Phase 1 (PR #7385) added dependency graph infrastructure. Phase 2 renames user-facing display strings, function names, variable names, and dict keys from "step" terminology to "node" terminology. This is a mechanical rename affecting ~112 occurrences across ~18 files.

LibCST is available as a dev dependency and the `libcst-refactor` agent is battle-tested for this kind of batch rename. The crossover point documented in `docs/learned/refactoring/libcst-systematic-imports.md` is ~10 files — this refactor is well above that threshold.

## Implementation

### Phase A: Manual display string edits (Steps 2.1 + 2.2)

6 string literal changes in 2 files. Too few and too specific for LibCST.

**`src/erk/cli/commands/objective/view_cmd.py`:**
- Line 289: `"steps done"` → `"nodes done"` (in f-string)
- Line 300: `"step"` → `"node"` (table column header)
- Line 330: `"Steps"` → `"Nodes"` (field label)
- Lines 351, 356: `"Next step"` → `"Next node"` (field labels, 2 occurrences)

**`src/erk/tui/widgets/plan_table.py`:**
- Line 152: `"next step"` → `"next node"` (column display header)
- Line 152: `key="next_step"` → `key="next_node"` (column key, for consistency)

### Phase B: LibCST identifier renames (Steps 2.3 + 2.4)

~80 identifier changes across 17+ files. Use `libcst-refactor` agent with a single transformer.

**Rename map (all Python identifiers — function names, variable names, field names, parameters, keyword arguments, attribute access, imports):**

| Old name | New name | Category |
|----------|----------|----------|
| `find_graph_next_step` | `find_graph_next_node` | 2.3 function |
| `find_next_step` | `find_next_node` | 2.3 function |
| `_format_step_status` | `_format_node_status` | 2.3 function |
| `objective_done_steps` | `objective_done_nodes` | 2.4 field |
| `objective_total_steps` | `objective_total_nodes` | 2.4 field |
| `objective_next_step_display` | `objective_next_node_display` | 2.4 field |
| `next_step` | `next_node` | 2.4 variable/field |

**Target files (production):**
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py`
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`
- `src/erk/cli/commands/objective/view_cmd.py`
- `src/erk/cli/commands/objective/check_cmd.py`
- `src/erk/cli/commands/plan/plan_cmd.py` (accesses `result.next_step`)
- `src/erk/cli/commands/exec/scripts/objective_fetch_context.py`
- `src/erk/tui/data/types.py`
- `src/erk/tui/widgets/plan_table.py`
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py`
- `packages/erk-shared/src/erk_shared/objective_fetch_context_result.py`

**Target files (tests):**
- `packages/erk-shared/tests/unit/github/metadata/test_dependency_graph.py`
- `packages/erk-shared/tests/unit/github/metadata/test_roadmap.py`
- `tests/unit/cli/commands/objective/test_check_cmd.py`
- `tests/unit/cli/commands/exec/scripts/test_objective_fetch_context.py`
- `tests/unit/cli/commands/exec/scripts/test_dash_data.py`
- `tests/tui/test_plan_table.py`
- `tests/tui/commands/test_execute_command.py`

**EXCLUSIONS — DO NOT RENAME `next_step` or `total_steps` in these files (different domain):**
- `packages/erk-shared/src/erk_shared/gateway/github/metadata_blocks.py` (ImplementationStatusSchema)
- `src/erk/cli/commands/plan/log_cmd.py` (ImplementationStatusMetadata)
- Any tests for ImplementationStatus

### Phase C: Dict key string renames (Step 2.5)

13 string literal changes across 7 files. These are quoted strings (`"total_steps"`, `"next_step"`) used as dict keys — not Python identifiers. Manual Edit tool with targeted replacements, scoped to the roadmap summary domain only.

**`"total_steps"` → `"total_nodes"` in:**
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py` (1: dict key set)
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py` (1: dict key set)
- `src/erk/cli/commands/objective/view_cmd.py` (1: dict key read)
- `src/erk/cli/commands/objective/check_cmd.py` (1: dict key read)
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` (1: dict key read)
- `packages/erk-shared/tests/unit/github/metadata/test_roadmap.py` (3: assertions)
- `packages/erk-shared/tests/unit/github/metadata/test_dependency_graph.py` (2: assertions)
- `tests/unit/cli/commands/objective/test_check_cmd.py` (2: assertions)
- `tests/unit/cli/commands/exec/scripts/test_objective_fetch_context.py` (1: assertion)

**`"next_step"` → `"next_node"` in JSON output contexts:**
- `src/erk/cli/commands/objective/check_cmd.py` (1: JSON key in `_output_json`)
- `tests/unit/cli/commands/objective/test_check_cmd.py` (1-2: assertions on JSON key)
- `tests/unit/cli/commands/exec/scripts/test_objective_fetch_context.py` (1-2: assertions on JSON key)

### Phase D: Docstring and documentation updates

Update references to old names in:
- Module docstring in `dependency_graph.py` (references `RoadmapStep` — but that's Phase 3 scope)
- Docstrings in `types.py` for renamed fields
- `docs/learned/objectives/dependency-graph.md` — references `find_next_step`
- `docs/learned/objectives/tripwires.md` — references `find_next_step`
- `docs/learned/objectives/roadmap-parser.md` — references `find_next_step`
- `docs/learned/cli/output-styling.md` — references `_format_step_status`

### Phase E: Verification

1. `ruff check --fix` — fix import sorting violations
2. `ty check` — verify type consistency
3. `pytest tests/unit/ tests/tui/` — run affected test suites
4. `git diff` review — confirm no unintended changes, no changes to metadata_blocks.py domain

## Execution Order

1. Phase A first (manual string edits — no dependencies)
2. Phase B next (LibCST batch rename — the bulk of the work)
3. Phase C after B (dict key strings — depends on B completing cleanly)
4. Phase D after C (docs — depends on final names being settled)
5. Phase E last (verify everything)

## LibCST Approach Notes

The `libcst-refactor` agent will create an ephemeral transformer script with:
- `leave_Name` — handles function names, variable names, field names, parameters via a whitelist dictionary
- `leave_FunctionDef` — handles function definition renames
- `leave_Attribute` — handles attribute access (e.g., `result.next_step` → `result.next_node`, `row.objective_next_step_display` → `row.objective_next_node_display`)

The transformer processes ONLY the listed target files (not the entire codebase) to avoid false positives with `next_step` in the ImplementationStatus domain.

## Breaking Change Note

The JSON output keys `"next_step"` and `"total_steps"` in `erk objective check --json-output` will change to `"next_node"` and `"total_nodes"`. Per AGENTS.md: "We can break backwards compatibility at will."