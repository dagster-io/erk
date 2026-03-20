# Plan: Rename CLI flags from "plan" to "pr" (Objective #9109, Node 8.2)

## Context

Part of Objective #9109 — renaming "plan" terminology to "pr" across all APIs. This is the final node (8.2): renaming CLI flags where "plan" is used as a PR identifier. All prior nodes (1.1-8.1) are complete. No backwards compatibility needed per project policy.

## Scope

Six rename groups, ordered by dependency:

### Group 1: `--for-plan` -> `--for-pr` (branch checkout/create + next_steps output)

**Click option definitions:**
- `src/erk/cli/commands/branch/checkout_cmd.py:420` — `--for-plan` option + param `for_plan` -> `for_pr`
- `src/erk/cli/commands/branch/create_cmd.py:36` — `--for-plan` option + param `for_plan` -> `for_pr`

**Shared output generator (generates `--for-plan` strings):**
- `packages/erk-shared/src/erk_shared/output/next_steps.py` — All `--for-plan` in `PrNextSteps` properties (lines 23, 27, 35, 39, 44, 51)

**TUI hardcoded strings:**
- `src/erk/tui/screens/plan_detail_screen.py` — Lines 362, 368, 680, 686, 993

### Group 2: `--from-plan` -> `--from-pr` (wt create)

**Click option definition:**
- `src/erk/cli/commands/wt/create_cmd.py:457` — `--from-plan` option + param `from_plan` -> `from_pr`

**Also rename related flags in same file:**
- `create_cmd.py:441` — `--from-plan-file` -> `--from-pr-file`, param `from_plan_file` -> `from_pr_file`
- `create_cmd.py:452` — `--keep-plan-file` -> `--keep-pr-file`, param `keep_plan_file` -> `keep_pr_file`
- `create_cmd.py:468` — `--copy-plan` -> `--copy-pr`, param `copy_plan` -> `copy_pr`

### Group 3: `--plan` -> `--pr` (duplicate_check, objective_fetch_context)

- `src/erk/cli/commands/pr/duplicate_check_cmd.py:29` — `--plan` / `-p` option + param `plan` -> `pr`
- `src/erk/cli/commands/exec/scripts/objective_fetch_context.py:153` — `--plan` option (param already `pr_number_arg`, keep as-is)

### Group 4: `--learn-plan` -> `--learn-pr` (track_learn_result)

- `src/erk/cli/commands/exec/scripts/track_learn_result.py:76` — `--learn-plan` option + param `learn_plan` -> `learn_pr`
- Also rename error codes: `missing-learn-plan` -> `missing-learn-pr`, `unexpected-learn-plan` -> `unexpected-learn-pr`

### Group 5: `get-plans-for-objective` -> `get-prs-for-objective` (exec command rename)

Follow the 9-place checklist:
1. **Script file**: Rename `get_plans_for_objective.py` -> `get_prs_for_objective.py`, update `@click.command(name=...)`
2. **exec/group.py**: Update import (line 56-57) and `add_command` registration (line 216)
3. **Test file**: Rename `test_get_plans_for_objective.py` -> `test_get_prs_for_objective.py`, update imports
4. **Skill reference**: Update `.claude/skills/erk-exec/reference.md` (lines 51, 510-514)
5. **Slash commands**: Update `.claude/commands/local/objective-view.md` (line 90)
6. **docs/learned/**: Grep and update references
7. **Help text**: Update docstrings within the script
8. **CHANGELOG**: Skip (no CHANGELOG entry for internal renames per project convention)
9. **Workflows**: Grep `.github/workflows/` for references

### Group 6: Fix stale `--plan` in objective_helpers.py

- `src/erk/cli/commands/objective_helpers.py:91` — Change `--plan {pr_number}` to `--pr {pr_number}` in slash command invocation (the slash command already expects `--pr`)

## Files to Modify (Source)

| File | Changes |
|------|---------|
| `src/erk/cli/commands/branch/checkout_cmd.py` | `--for-plan` -> `--for-pr`, param rename, help text, error messages |
| `src/erk/cli/commands/branch/create_cmd.py` | `--for-plan` -> `--for-pr`, param rename, help text |
| `src/erk/cli/commands/wt/create_cmd.py` | `--from-plan` -> `--from-pr`, `--from-plan-file` -> `--from-pr-file`, `--keep-plan-file` -> `--keep-pr-file`, `--copy-plan` -> `--copy-pr` |
| `src/erk/cli/commands/pr/duplicate_check_cmd.py` | `--plan` -> `--pr`, param rename |
| `src/erk/cli/commands/exec/scripts/objective_fetch_context.py` | `--plan` -> `--pr` (param name already correct) |
| `src/erk/cli/commands/exec/scripts/track_learn_result.py` | `--learn-plan` -> `--learn-pr`, error codes |
| `src/erk/cli/commands/exec/scripts/get_plans_for_objective.py` | Rename file -> `get_prs_for_objective.py`, command name |
| `src/erk/cli/commands/exec/group.py` | Update import and registration for renamed command |
| `src/erk/cli/commands/objective_helpers.py` | Fix `--plan` -> `--pr` in slash command string |
| `packages/erk-shared/src/erk_shared/output/next_steps.py` | `--for-plan` -> `--for-pr` in all properties |
| `src/erk/tui/screens/plan_detail_screen.py` | `--for-plan` -> `--for-pr` in 5 hardcoded strings |

## Files to Modify (Tests)

| File | Changes |
|------|---------|
| `tests/unit/cli/commands/exec/scripts/test_get_plans_for_objective.py` | Rename -> `test_get_prs_for_objective.py`, update imports |
| `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py` | Update `--for-plan` assertions |
| `tests/unit/cli/commands/exec/scripts/test_track_learn_result.py` | Update `--learn-plan` invocations and error code assertions |
| `tests/unit/cli/commands/exec/scripts/test_objective_fetch_context.py` | Update `--plan` invocations |
| `tests/unit/cli/commands/branch/test_create_cmd.py` | Update `--for-plan` invocations |
| `tests/commands/management/test_impl.py` | Update `--from-plan-file` invocations |
| `tests/tui/commands/test_execute_command.py` | Update `--for-plan` assertions |
| `tests/tui/app/test_plan_detail_screen.py` | Update `--for-plan` assertions |
| `packages/erk-shared/tests/unit/output/test_next_steps.py` | Update `--for-plan` assertions |
| `packages/erk-shared/tests/unit/github/test_objective_issues.py` | Update if references `--for-plan` |

## Files to Modify (Docs/Skills)

| File | Changes |
|------|---------|
| `.claude/skills/erk-exec/reference.md` | Update `--plan` -> `--pr` for objective_fetch_context, `--learn-plan` -> `--learn-pr`, command name |
| `.claude/commands/local/objective-view.md` | `get-plans-for-objective` -> `get-prs-for-objective` |
| `.claude/commands/erk/learn.md` | `--learn-plan` -> `--learn-pr` |
| `docs/learned/` (multiple files) | Grep and update `--for-plan`, `--from-plan`, command references |

## Implementation Order

1. **erk-shared package first** (next_steps.py) — downstream code depends on this
2. **CLI source files** (Groups 1-4, 6) — mechanical renames
3. **Exec command rename** (Group 5) — file rename + registration update
4. **TUI** — update hardcoded strings
5. **Tests** — update all test invocations and assertions
6. **Docs/skills** — update all documentation references
7. **Regenerate exec reference docs** via `erk-dev gen-exec-reference-docs`

## Verification

1. Run `ruff check` and `ty` for lint/type errors
2. Run unit tests: `pytest tests/unit/cli/commands/branch/ tests/unit/cli/commands/exec/scripts/ tests/unit/cli/commands/pr/`
3. Run TUI tests: `pytest tests/tui/`
4. Run shared package tests: `pytest packages/erk-shared/tests/unit/output/`
5. Run full test suite to catch any missed references
6. Grep for stale references: `rg --type py --type md "for.plan|from.plan|learn.plan|get.plans.for.objective" --glob '!CHANGELOG*'`
