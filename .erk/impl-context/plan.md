# Phase 4: CLI flag, constant, and help text renames

**Objective:** #9318, Nodes 4.1–4.5
**Goal:** Rename remaining "plan" terminology in CLI flags, constants, enum values, and help text to "pr" terminology.

## Context

This is Phase 4 of the plan-to-PR terminology rename objective. Phases 1–3 renamed types, classes, module files, and context properties. Phase 4 targets user-facing CLI flags, display constants, and help text — the surface area visible to CLI users.

## Node 4.1: Rename CLI flags in wt/create_cmd.py

**Files:**
- `src/erk/cli/commands/wt/create_cmd.py`
- `tests/commands/workspace/create/test_plan_file_operations.py`
- `tests/commands/test_create_copy_impl.py`
- `tests/commands/implement/test_file_mode.py`
- `tests/commands/implement/test_execution_modes.py`

**Renames:**
| Old | New |
|-----|-----|
| `--from-plan-file` | `--from-pr-file` |
| `--keep-plan-file` | `--keep-pr-file` |
| `--copy-plan` | `--copy-pr` |
| `from_plan_file` (param) | `from_pr_file` |
| `keep_plan_file` (param) | `keep_pr_file` |
| `copy_plan` (param) | `copy_pr` |
| `is_plan_derived` (local var) | `is_pr_derived` |
| `plan_stem` (local var) | `pr_stem` |
| `plan_content` (local var) | `pr_content` |

Also update error messages and help text strings referencing these flags.

## Node 4.2: Rename SortKey.PLAN_ID

**Files:**
- `src/erk/tui/sorting/types.py` — `PLAN_ID` → `PR_ID`, display label `"by plan#"` → `"by pr#"`, comments
- `src/erk/tui/sorting/logic.py` — references to `SortKey.PLAN_ID` → `SortKey.PR_ID`, comments
- `src/erk/cli/commands/pr/list/cli.py` (line 346) — `SortKey.PLAN_ID` → `SortKey.PR_ID`
- `src/erk/cli/commands/pr/list/operation.py` (line 126) — `SortKey.PLAN_ID` → `SortKey.PR_ID`
- `src/erk/cli/commands/exec/scripts/create_impl_context_from_plan.py` (line 50) — docstring `PLAN_ID` → `PR_ID`
- `src/erk/tui/widgets/status_bar.py` (line 146) — docstring example `"by plan#"` → `"by pr#"`
- `tests/tui/commands/test_registry.py` — if references exist

## Node 4.3: Rename PLAN_HEADING_PREFIX and has_plan_title_prefix

**Files:**
- `src/erk/cli/constants.py`:
  - `PLAN_HEADING_PREFIX` → `PR_HEADING_PREFIX` (line 16). **Keep string value `"Plan: "`** — this is a display heading for plan markdown content, changing it would break parsing of existing plan issues.
  - `has_plan_title_prefix()` → `has_pr_title_prefix()` (line 10)
  - Comment on line 15 → update
- `tests/unit/cli/test_constants.py` — rename test functions
- Import sites for `has_plan_title_prefix` (4 files):
  - `src/erk/cli/commands/pr/dispatch_cmd.py`
  - `src/erk/cli/commands/pr/duplicate_check_cmd.py`
  - `src/erk/cli/commands/implement.py`
- Duplicate in `packages/erk-shared/src/erk_shared/plan_workflow.py` (`_has_plan_title_prefix`) → `_has_pr_title_prefix`

**Note:** `PLAN_HEADING_PREFIX` has zero import sites outside constants.py — unused. Consider deleting instead of renaming if truly dead code. Verify during implementation.

## Node 4.4: Update help text in pr/view/cli.py

**File:** `src/erk/cli/commands/pr/view/cli.py`

**Changes:**
- Line 1: Module docstring `"Command to fetch and display a single plan."` → `"Command to fetch and display a single PR."`
- Line 224: `"─── Plan ───"` → `"─── PR Body ───"`
- Line 230: `help="Show full plan body"` → `help="Show full PR body"`
- Line 240: `"Fetch and display a plan by identifier."` → `"Fetch and display a PR by identifier."`
- Line 245: `"infers the plan number"` → `"infers the PR number"`
- Line 248: `"the complete plan body"` → `"the complete PR body"`
- Line 262: `"plan branch with a plan reference file"` → `"PR branch with a PR reference file"`
- Line 183-184: `_display_plan` → `_display_pr` (function name + docstring)

## Node 4.5: Update help text in one_shot/cli.py and metadata_helpers.py

**File 1:** `src/erk/cli/commands/one_shot/cli.py`
- Line 11: Example docstring — update `plan_number` → `pr_number` (already done in line 110, inconsistent with line 11)
- Line 96: `"plans, implements, and submits"` — "plans" here means "creates a plan" (verb), keep as-is
- `--plan-only` flag (line 49) — this is a semantic flag about the planning phase, not the plan/PR entity. **Keep as-is.**

**File 2:** `src/erk/cli/commands/pr/metadata_helpers.py`
- Line 1: Module docstring `"Helpers for plan dispatch metadata updates."` → `"Helpers for PR dispatch metadata updates."`
- Line 3-4: `"updating plan dispatch metadata"` → `"updating PR dispatch metadata"`
- Line 33: Docstring `"Resolve node_id and write dispatch metadata to plan header."` → `"...to PR header."`
- Line 36: `"If plan not found"` → `"If PR not found"`
- Line 42: Comment `"Check plan exists"` → `"Check PR exists"`
- Line 46: Error message `f"Plan #{pr_number} not found"` → `f"PR #{pr_number} not found"`
- Line 60: Function `maybe_update_plan_dispatch_metadata` → `maybe_update_pr_dispatch_metadata`
- Line 66: Docstring updates throughout
- Import sites for `maybe_update_plan_dispatch_metadata` (2 code files):
  - `src/erk/cli/commands/launch_cmd.py`
  - `tests/unit/cli/commands/pr/test_metadata_helpers.py`
- 6 docs/learned/ files reference the old function name — update those too

## Implementation approach

Use `rename-swarm` skill with haiku agents for the mechanical renames in nodes 4.1, 4.2, and 4.3. Handle nodes 4.4 and 4.5 (prose/help text) manually since they require judgment about which "plan" references to change.

**Order:** 4.3 first (constants used by other files), then 4.1, 4.2, 4.4, 4.5 in any order.

## Verification

1. `make fast-ci` — run unit tests + linting
2. `ty` — type checking
3. Grep for remaining `PLAN_ID`, `PLAN_HEADING_PREFIX`, `has_plan_title_prefix`, `from_plan_file`, `keep_plan_file`, `copy_plan` to confirm no stragglers
4. Grep for `plan` in changed files to ensure no missed references
