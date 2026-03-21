# Plan: Consolidated Learn Documentation Update

> **Consolidates:** #9329, #9328, #9323, #9322, #9317, #9316, #9315, #9312, #9309, #9305, #9304, #9302, #9300, #9299, #9295, #9291, #9289, #9284, #9283

## Context

19 erk-learn plans accumulated from recent implementation sessions covering two major workstreams: **PR terminology rename** (plan→PR, 5 plans) and **slot system extraction** (8 plans), plus 6 miscellaneous bug fix/improvement plans. All source PRs have been merged to master. The documentation has not caught up with the code changes, leaving stale references and missing coverage.

## Source Plans

| # | Title | Items |
| --- | --- | --- |
| #9322 | Rename plan-oriented types to PR terminology (Nodes 1.1-1.4) | 2 |
| #9317 | Standardize CLI flags from "plan" to "PR" terminology | 2 |
| #9295 | Rename test helpers and fake executor methods | 1 |
| #9289 | Rename workflow YAML inputs/env vars plan_id→pr_number | 2 |
| #9283 | Rename plan variables/types in CLI/TUI/shared packages | 1 |
| #9323 | Make `erk slot co` commands copy-pasteable | 1 |
| #9316 | Move slot allocation logic to `erk.core` | 2 |
| #9312 | Remove `--new-slot` flag from `erk slot checkout` | 1 |
| #9309 | Replace `erk br co --for-plan` with `erk slot co` | 1 |
| #9304 | Extract slot naming utilities to erk-shared | 1 |
| #9299 | Add script mode and activation navigation | 1 |
| #9284 | Extract slot system into erk-slots package | 2 |
| #9291 | Extract CLI infrastructure to erk-shared | 2 |
| #9329 | Escape pipe characters in objective roadmap tables | 1 |
| #9328 | Improve `erk pr teleport` help string | 1 |
| #9315 | Fix exit plan mode hook copy | 0 |
| #9305 | Fix false positive review for ternary context managers | 0 |
| #9302 | Fix "p" keybinding for objective issues | 0 |
| #9300 | Delete `get-pr-for-plan` exec command | 1 |

## Investigation Findings

### Items Already Documented (Skip)
- **#9305**: Ternary context manager guidance already added to `.claude/skills/dignified-code-simplifier/SKILL.md`
- **#9302**: "p" keybinding already documented in `docs/learned/tui/keyboard-shortcuts.md`
- **#9315**: Simple copy fix, no documentation value

### Stale Documentation (Must Fix)
1. **`docs/learned/planning/next-steps-output.md`** — References `PlanNextSteps` (now `PrNextSteps`), `format_plan_next_steps_plain` (now `format_pr_next_steps_plain`), and `erk br co --for-plan` (now `erk slot co`)
2. **`docs/learned/erk/slot-pool-architecture.md`** — References `src/erk/cli/commands/slot/common.py` (moved to `src/erk/core/slot_allocation.py`), mentions removed `--new-slot` flag
3. **`docs/learned/cli/erk-exec-commands.md`** — Line 14 tripwire says "use 'plan' terminology" but should say "use 'PR' terminology"

### New Documentation Needed
- Slot system package extraction pattern (erk-slots, erk-shared infrastructure)
- Markdown table cell escaping utility

## Implementation Steps

### Step 1: Fix `next-steps-output.md` (from #9309, #9283, #9289, #9323)

**File:** `docs/learned/planning/next-steps-output.md`

**Changes:**
- Frontmatter line 5: "understanding PlanNextSteps" → "understanding PrNextSteps"
- Frontmatter tripwire line 9: "PlanNextSteps" → "PrNextSteps"
- Line 22: `PlanNextSteps` → `PrNextSteps`
- Line 30: `format_plan_next_steps_plain` → `format_pr_next_steps_plain`
- Add `branch_name` parameter documentation (added by #9309)
- Update command examples from `erk br co --for-plan` to `erk slot co {branch_name}`
- Document the `source <(erk slot co ... --script)` shell activation pattern

**Source:** `packages/erk-shared/src/erk_shared/output/next_steps.py`

**Verification:** All class/function names in doc match actual names in source file

### Step 2: Fix `slot-pool-architecture.md` (from #9316, #9312, #9284, #9291)

**File:** `docs/learned/erk/slot-pool-architecture.md`

**Changes:**
- Update all references from `src/erk/cli/commands/slot/common.py` → `src/erk/core/slot_allocation.py`
- Remove `--new-slot` flag documentation (lines ~178-183)
- Add note about slot commands living in `packages/erk-slots/` package
- Add note about naming utilities in `packages/erk-shared/src/erk_shared/slots/naming.py`
- Document conditional loading pattern (`importlib.util.find_spec()` in `src/erk/cli/cli.py`)

**Source files:**
- `src/erk/core/slot_allocation.py` (moved allocation logic)
- `packages/erk-slots/` (package structure)
- `packages/erk-shared/src/erk_shared/slots/naming.py` (pure naming utilities)
- `packages/erk-shared/src/erk_shared/cli_alias.py` (extracted from erk)
- `packages/erk-shared/src/erk_shared/cli_group.py` (ErkCommandGroup)

**Verification:** grep for old paths in the doc yields zero matches; all referenced files exist

### Step 3: Fix `erk-exec-commands.md` tripwire (from #9317, #9300)

**File:** `docs/learned/cli/erk-exec-commands.md`

**Changes:**
- Line 14 tripwire: change "use 'plan' terminology not 'issue'" → "use 'PR' terminology not 'issue' or 'plan'"
- Remove any reference to deleted `get-pr-for-plan` command
- Verify `get-prs-for-objective` command is documented (renamed from `get-plans-for-objective`)

**Source:** `src/erk/cli/commands/exec/scripts/` directory for current command inventory

**Verification:** tripwire text matches current naming convention

### Step 4: Create `docs/learned/objectives/markdown-table-escaping.md` (from #9329)

**File:** `docs/learned/objectives/markdown-table-escaping.md`

**Content outline:**
1. Problem: Pipe characters (`|`) in objective roadmap cell content break markdown table rendering
2. Solution: `escape_md_table_cell()` utility in `erk_shared.gateway.github.metadata.roadmap`
3. What it escapes: pipes (`|` → `\|`) and newlines (→ space)
4. Where applied: `roadmap.py` rendering and `objective_render_roadmap.py` exec script
5. Tripwire: Always use `escape_md_table_cell()` when rendering user-provided text in markdown tables

**Source:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`

**Verification:** Function exists and tests pass in `test_roadmap.py`

### Step 5: Update `docs/learned/cli/checkout-teleport-split.md` (from #9328)

**File:** `docs/learned/cli/checkout-teleport-split.md`

**Changes:**
- Add section documenting the 5 capabilities that `erk pr teleport` provides beyond `gh pr checkout`:
  1. Force-resets local branch to match remote
  2. Worktree pool integration
  3. Graphite registration/tracking
  4. Shell activation scripts
  5. `--sync` mode for `gt submit`

**Source:** `src/erk/cli/commands/pr/teleport_cmd.py` (lines 47-76, docstring)

**Verification:** Capability list matches the current help text

### Step 6: Update category indexes

**Files:**
- `docs/learned/objectives/index.md` — add entry for `markdown-table-escaping.md`
- `docs/learned/objectives/tripwires.md` — add tripwire for `escape_md_table_cell()`

**Verification:** `docs/learned/index.md` categories still route correctly

## Overlap Analysis

- **PR terminology rename** (#9322, #9317, #9295, #9289, #9283): All five plans touch the same rename. Consolidated into Steps 1 and 3 — update existing docs rather than create new ones.
- **Slot system extraction** (#9323, #9316, #9312, #9309, #9304, #9299, #9284, #9291): Eight plans covering one large refactor. Consolidated into Step 2 — update the existing slot-pool-architecture.md.
- **#9305, #9302, #9315**: Already documented or too thin for standalone docs. No action needed.

## Attribution

- **Steps 1**: #9309, #9283, #9289, #9323
- **Step 2**: #9316, #9312, #9284, #9291, #9304, #9299
- **Step 3**: #9317, #9300
- **Step 4**: #9329
- **Step 5**: #9328
- **Step 6**: Supporting step for Step 4

## Verification

After implementation:
1. Grep `docs/learned/` for `PlanNextSteps` — should return zero matches
2. Grep `docs/learned/` for `src/erk/cli/commands/slot/common.py` — should return zero matches
3. Grep `docs/learned/` for `--new-slot` — should return zero matches
4. Grep `docs/learned/` for `get-pr-for-plan` — should return zero matches
5. Verify all referenced source files exist
6. Verify new `markdown-table-escaping.md` is in the objectives index
