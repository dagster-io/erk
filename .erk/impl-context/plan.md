# Plan: Rename issue_number to plan_number — Node 8.2

**Part of Objective #7724, Node 8.2**

## Context

Objective #7724 systematically renames `issue_number` to `plan_number` across the codebase to better reflect that these identifiers refer to plans, not generic GitHub issues. Phases 1-7 are complete. Node 8.2 targets 6 CLI command files, one of which (`objective_helpers.py`) is already done.

## Files to Modify

### 1. `src/erk/cli/commands/run/shared.py`
- Rename function `extract_issue_number` → `extract_plan_number`
- Update docstring: "Extract issue number" → "Extract plan number"

### 2. `src/erk/cli/commands/run/list_cmd.py`
- Update import: `extract_issue_number` → `extract_plan_number`
- Rename all `issue_num` → `plan_num` (~15 occurrences)
- Rename `issue_numbers` → `plan_numbers`
- Rename `issue_map` references stay if they refer to GitHub issue objects (check context), or rename if plan-specific

### 3. `src/erk/cli/commands/wt/create_cmd.py`
- Rename `issue_number_parsed` → `plan_number_parsed` (~8 occurrences across lines 568, 615, 657-658, 662, 666-667, 671)
- Update assertion message: `"issue_number_parsed must be set"` → `"plan_number_parsed must be set"`
- Update user-facing messages: `"Failed to fetch issue #"` → `"Failed to fetch plan #"`, `"gh issue view"` → keep (it's a real gh command)
- **Keep `setup.issue_number` as-is** (lines 918, 926) — this accesses `IssueBranchSetup.issue_number` from erk_shared, which is Phase 9 scope

### 4. `src/erk/cli/commands/admin.py`
- Rename local variable `issue_number` → `plan_number` (lines 461, 462, 470, 471, 527)
- Fix workflow input keys to match `plan-implement.yml` inputs:
  - `"issue_number"` → `"plan_id"` (the workflow expects `plan_id`)
  - `"issue_title"` → `"plan_title"` (the workflow expects `plan_title`)

### 5. `src/erk/cli/commands/learn/learn_cmd.py`
- Rename function `_extract_issue_number` → `_extract_plan_number` (definition at line 40)
- Update docstring
- Rename local var `issue_number` → `plan_number` (lines 111, 112, 115)

### 6. `src/erk/cli/commands/objective_helpers.py`
- **No changes needed** — already uses `plan_number`

## Boundary Rules

- **erk_shared attributes stay**: `setup.issue_number`, `result.number` etc. from erk_shared types are Phase 9 scope
- **Generic GitHub references stay**: `"gh issue view"` command text stays as-is
- **Workflow input keys match the workflow**: admin.py keys align with `plan-implement.yml` input names (`plan_id`, `plan_title`)

## Execution Order

1. `run/shared.py` (upstream function definition)
2. `run/list_cmd.py` (consumes the renamed function)
3. `wt/create_cmd.py` (independent)
4. `admin.py` (independent)
5. `learn/learn_cmd.py` (independent)

## Verification

1. `ruff check src/erk/cli/commands/run/ src/erk/cli/commands/wt/create_cmd.py src/erk/cli/commands/admin.py src/erk/cli/commands/learn/learn_cmd.py` — no lint errors
2. `ty check` — no type errors
3. Grep for stale `issue_number` in the 5 modified files — only `setup.issue_number` should remain (wt/create_cmd.py)
4. `make fast-ci` — all tests pass
