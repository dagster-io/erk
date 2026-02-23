# Plan: Merge `plan`/`pr` into single `planned_pr` field in objective roadmap

## Context

In the draft-PR plan backend (now the only backend), a plan IS a draft PR — they share the same GitHub PR number. The current roadmap format has separate `plan` and `pr` fields on each node, plus separate "Plan" and "PR" columns in the markdown table. This is redundant: when both are set, they always contain the same value (e.g., `plan: "#7971", pr: "#7971"`). Merging into a single `planned_pr` field simplifies the data model, CLI interface, and display.

## Approach

Merge `plan: str | None` and `pr: str | None` into a single `planned_pr: str | None` across the data model, YAML schema, CLI, rendering, and tests. Bump schema version from "4" to "5". Support parsing v4 (auto-coalesce `pr` > `plan` > null) for existing objectives.

## Changes

### 1. Core data model (`packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`)

- **RoadmapNode**: Replace `plan: str | None` + `pr: str | None` with `planned_pr: str | None`
- **validate_roadmap_frontmatter()**:
  - Accept schema_version "5" (new) with `planned_pr` key
  - Accept schema_version "2"/"3"/"4" (existing) with separate `plan`/`pr` keys — coalesce: `pr or plan or None`
- **render_roadmap_block_inner()**: Emit `schema_version: "5"` with `planned_pr` key
- **update_node_in_frontmatter()**: Replace separate `plan`/`pr` params with single `planned_pr` param. Simplify status inference: `planned_pr` set → `in_progress`
- **render_roadmap_tables()**: Merge "Plan"/"PR" columns into single "Planned PR" column. Change `pr_count` to count done nodes instead of `step.pr is not None`
- **serialize_phases()**: Replace `plan`/`pr` keys with `planned_pr`

### 2. Dependency graph (`packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py`)

- **ObjectiveNode**: Replace `plan: str | None` + `pr: str | None` with `planned_pr: str | None`
- Update `graph_from_phases()`, `graph_from_nodes()`, `nodes_from_graph()` to pass `planned_pr`

### 3. Render roadmap exec script (`src/erk/cli/commands/exec/scripts/objective_render_roadmap.py`)

- Update table header: `| Node | Description | Status | Planned PR |`
- Update table rows to emit single `planned_pr` column (always `-` for new roadmaps)

### 4. Update objective node CLI (`src/erk/cli/commands/exec/scripts/update_objective_node.py`)

- Replace `--plan`/`--pr` options with single `--planned-pr` option
- Remove the validation that `--plan` is required when `--pr` is set (no longer needed)
- Update `_replace_table_in_text()`: Match 4-column rows (was 5-column)
- Update `_find_node_refs()`: Return single `planned_pr` value
- Update `_replace_node_refs_in_body()`: Pass single `planned_pr`
- Update `_build_output()`: Replace `previous_plan`/`new_plan`/`previous_pr`/`new_pr` with `previous_planned_pr`/`new_planned_pr`

### 5. View command (`src/erk/cli/commands/objective/view_cmd.py`)

- **_format_node_status()**: Rename `plan` param → `planned_pr`
- Merge `max_plan_width`/`max_pr_width` into `max_planned_pr_width`
- Merge separate "plan"/"pr" table columns into single "planned_pr" column
- Update JSON output: replace `plan`/`pr` keys with `planned_pr`

### 6. Check command (`src/erk/cli/commands/objective/check_cmd.py`)

- Merge plan/pr consistency checks: single check for `planned_pr` reference format
- Update orphaned done check: `node.status == "done" and node.planned_pr is None`
- Merge plan/pr `#` prefix validation into single `planned_pr` check

### 7. Fetch context (`src/erk/cli/commands/exec/scripts/objective_fetch_context.py`)

- Update `step.plan == plan_ref` → `step.planned_pr == plan_ref` for step matching

### 8. Skill/command docs (update CLI examples)

- `.claude/commands/erk/objective-update-with-landed-pr.md` — `--planned-pr` instead of `--plan`/`--pr`
- `.claude/commands/erk/objective-update-with-closed-plan.md` — `--planned-pr ""`
- `.claude/commands/erk/plan-save.md` — `--planned-pr`
- `.claude/commands/local/objective-reevaluate.md` — `--planned-pr`
- `.claude/skills/erk-exec/reference.md` — update parameter docs
- `.claude/skills/objective/references/format.md` — update format docs

### 9. CI workflow (`.github/workflows/one-shot.yml`)

- Change `--plan "$PLAN_NUMBER"` → `--planned-pr "$PLAN_NUMBER"`

### 10. Tests

- `test_roadmap.py` — update `.pr`/`.plan` assertions → `.planned_pr`
- `test_roadmap_frontmatter.py` — update all plan/pr assertions and YAML fixtures
- `test_dependency_graph.py` — update ObjectiveNode assertions
- `test_update_objective_node.py` — update --plan/--pr to --planned-pr, update output keys
- `test_objective_render_roadmap.py` — update table format assertions

### 11. Docs (update roadmap-related learned docs)

- `docs/learned/architecture/roadmap-mutation-semantics.md` — if it references plan/pr separately
- `docs/learned/objectives/roadmap-status-system.md` — update two-tier status docs
- `docs/learned/reference/objective-summary-format.md` — update format reference

## Migration strategy

- **Parsing**: `validate_roadmap_frontmatter()` accepts v2/3/4 (coalesces `pr ?? plan` into `planned_pr`) and v5 (reads `planned_pr` directly)
- **Writing**: Always emits v5 with `planned_pr`
- **Existing objectives**: First read coalesces to v5 in memory; next write (via `update-objective-node` or any mutation) upgrades the on-disk YAML to v5
- **No explicit migration script needed**: objectives upgrade lazily on next mutation

## Verification

1. Run `make fast-ci` — all unit tests pass
2. `erk objective view 7911` — renders correctly with single "planned_pr" column (existing v4 YAML auto-coalesced)
3. `erk objective check 7911` — passes all validation checks
4. `erk exec update-objective-node 7911 --node 1.2 --planned-pr "#9999" --status in_progress` — sets single field, then revert
5. `erk exec objective-render-roadmap` with test JSON — produces 4-column table (Node | Description | Status | Planned PR)
