# Plan: Enrich `erk objective list` CLI to match TUI dashboard

## Context

The `/erk:objective-list` Claude Code command shows a minimal 3-column table (issue, title, created) using raw `gh issue list`. The `erk dash` TUI objectives tab shows 9 rich columns (issue, slug, prog, state, deps-state, deps, next, updated, created by) by parsing roadmaps and computing dependency graphs. The user wants the CLI output (and thus the Claude Code skill) to match the TUI.

## Approach

### Step 1: Enhance `erk objective list` CLI command

**File:** `src/erk/cli/commands/objective/list_cmd.py`

Add roadmap parsing and graph computation to build the same columns as the TUI. Import the same functions used by `RealPlanDataProvider._build_row_data()`:

- `extract_objective_slug` from `erk_shared.gateway.github.metadata.core`
- `parse_roadmap` from `erk_shared.gateway.github.metadata.roadmap`
- `build_graph`, `compute_graph_summary`, `build_state_sparkline`, `find_graph_next_node`, `_TERMINAL_STATUSES` from `erk_shared.gateway.github.metadata.dependency_graph`

Update the Rich table to show 9 columns matching the TUI:
| issue | slug | prog | state | deps-state | deps | next | updated | created by |

For each plan, compute:
- **slug**: `extract_objective_slug(body)` or title with "Objective: " prefix stripped, truncated to 25 chars
- **prog**: `done/total` from `compute_graph_summary(graph)`
- **state**: sparkline from `build_state_sparkline(graph.nodes)`
- **deps-state**: "ready" or status of min dep for next node
- **deps**: PR numbers of blocking deps (show up to 3)
- **next**: next node ID from `find_graph_next_node(graph, phases)`
- **updated**: `format_relative_time(plan.updated_at)`
- **created by**: `plan.metadata.get("author", "")`

### Step 2: Update the Claude Code skill

**File:** `.claude/commands/erk/objective-list.md`

Replace the `gh issue list` approach with simply running `erk objective list` and displaying the output directly. The CLI command now produces the rich table, so the skill just needs to run it and relay.

## Key files

- `src/erk/cli/commands/objective/list_cmd.py` — CLI command to enhance
- `.claude/commands/erk/objective-list.md` — skill to simplify
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` (lines 780-840) — reference logic to replicate

## Verification

1. Run `erk objective list` and compare output columns to `erk dash` objectives tab
2. Run `/erk:objective-list` in Claude Code and verify it shows the same rich data
3. Run fast-ci to ensure no regressions
