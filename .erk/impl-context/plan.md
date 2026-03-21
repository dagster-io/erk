# Plan: Rename CLI flags from plan to PR terminology (Objective #9109, Node 8.2)

## Context

This is the final node of Objective #9109 (Rename "plan" terminology to "pr" across all APIs). 36 of 37 nodes are complete. This node renames CLI flags where "plan" is used as a PR identifier. Flags like `--from-plan-file`, `--keep-plan-file`, and `--copy-plan` are NOT in scope — they refer to local plan files, not PR identifiers.

## Phase 1: Rename `--for-plan` to `--for-pr` (branch checkout/create + TUI)

### Source files

1. **`src/erk/cli/commands/branch/checkout_cmd.py`**
   - Line 420: `"--for-plan"` → `"--for-pr"`
   - Line 421: `"for_plan"` param name → `"for_pr"` (Click dest)
   - Line 431: `for_plan: str | None` → `for_pr: str | None`
   - Update all references to `for_plan` variable throughout the file (~15 occurrences)
   - Update help text, error messages, and comments referencing `--for-plan`

2. **`src/erk/cli/commands/branch/create_cmd.py`**
   - Line 36: `"--for-plan"` → `"--for-pr"`
   - Line 37: `"for_plan"` → `"for_pr"`
   - Update all `for_plan` variable references and error messages

3. **`src/erk/tui/screens/plan_detail_screen.py`** (5 hardcoded strings)
   - Line 362: `f"erk br co --for-plan {self._row.pr_number}"`
   - Line 368: `f'source "$(erk br co --for-plan {self._row.pr_number} --script)"'`
   - Line 680: `f"erk br co --for-plan {row.pr_number}"`
   - Line 686: `f'source "$(erk br co --for-plan {row.pr_number} --script)"'`
   - Line 993: `f"erk br co --for-plan {self._row.pr_number}"`

4. **`src/erk/tui/commands/types.py`** line 64: update docstring reference

5. **`packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py`** line 432: hardcoded `erk br co --for-plan` string

### Test files

6. **`tests/commands/branch/test_checkout_cmd.py`** (~30 occurrences of `--for-plan`)
7. **`tests/unit/cli/commands/branch/test_create_cmd.py`** (~20 occurrences)
8. **`tests/tui/commands/test_execute_command.py`** lines 146-147
9. **`tests/tui/app/test_plan_detail_screen.py`** line 207
10. **`packages/erk-shared/tests/unit/github/test_objective_issues.py`** line 311

## Phase 2: Rename `--from-plan` to `--from-pr` (wt create)

### Source files

11. **`src/erk/cli/commands/wt/create_cmd.py`**
    - Line 457: `"--from-plan"` → `"--from-pr"`
    - Line 458: `"from_plan"` → `"from_pr"`
    - Update all `from_plan` variable references
    - Update error messages referencing `--from-plan` (lines 556, 568, 571-573, 640-641)
    - NOTE: `--from-plan-file` and `--keep-plan-file` stay unchanged

### Test files

12. **`tests/commands/test_create_copy_impl.py`** (references to `--from-plan`)
13. **`tests/core/test_impl_issue_wt_workflow.py`** line 117 comment

## Phase 3: Rename `--plan` to `--pr` in exec scripts

### Source files

14. **`src/erk/cli/commands/pr/duplicate_check_cmd.py`**
    - Line 29: `"--plan"` → `"--pr"`
    - Line 30: `"-p"` stays (short flag)
    - Line 31: param name `plan` stays... actually we need to rename to avoid conflict. Check if `pr` conflicts. The param feeds into `plan: str | None` on line 39.
    - Rename param `plan` → `pr` throughout the function
    - Update help text and examples referencing `--plan`

15. **`src/erk/cli/commands/exec/scripts/objective_fetch_context.py`**
    - Line 153: `"--plan"` → `"--pr"`
    - Line 154: `"pr_number_arg"` dest stays (already uses pr naming internally)

## Phase 4: Rename `--learn-plan` to `--learn-pr` (track_learn_result)

### Source files

16. **`src/erk/cli/commands/exec/scripts/track_learn_result.py`**
    - Line 76: `"--learn-plan"` → `"--learn-pr"`
    - Param name `learn_plan` → `learn_pr` throughout
    - Update error messages referencing `--learn-plan` (lines 105, 115, 135)

### Test files

17. **`tests/unit/cli/commands/exec/scripts/test_track_learn_result.py`** (~8 occurrences)

## Phase 5: Rename `get-plans-for-objective` to `get-prs-for-objective`

### Source files

18. **`src/erk/cli/commands/exec/scripts/get_plans_for_objective.py`**
    - Rename file to `get_prs_for_objective.py`
    - Line 28: command name `"get-plans-for-objective"` → `"get-prs-for-objective"`
    - Line 31: function name `get_plans_for_objective` → `get_prs_for_objective`
    - Update docstrings

19. **`src/erk/cli/commands/exec/group.py`**
    - Line 56-57: Update import path and function name
    - Line 216: Update `name="get-plans-for-objective"` → `"get-prs-for-objective"`

### Test files

20. **`tests/unit/cli/commands/exec/scripts/test_get_plans_for_objective.py`**
    - Rename file to `test_get_prs_for_objective.py`
    - Update imports and function references throughout

## Phase 6: Update callers (skills, commands, docs)

21. **`.claude/skills/erk-exec/reference.md`** — `get-plans-for-objective` → `get-prs-for-objective`, `--learn-plan` → `--learn-pr`
22. **`.claude/commands/erk/learn.md`** — `--learn-plan` → `--learn-pr`
23. **`.claude/commands/local/objective-view.md`** — `get-plans-for-objective` → `get-prs-for-objective`
24. **`packages/erk-shared/src/erk_shared/plan_workflow.py`** line 5: docstring `--from-plan` → `--from-pr`
25. **`docs/learned/` files** — Update references:
    - `docs/learned/cli/checkout-three-path-logic.md` — `--for-plan` → `--for-pr`
    - `docs/learned/cli/index.md` — `--for-plan` → `--for-pr`
    - `docs/learned/cli/learn-plan-land-flow.md` — `--for-plan` → `--for-pr`
    - `docs/learned/cli/erk-exec-commands.md` — `--learn-plan` → `--learn-pr`
    - `docs/learned/planning/branch-name-inference.md` — `--for-plan` → `--for-pr`
    - `docs/learned/planning/next-steps-output.md` — `--for-plan` → `--for-pr`
    - `docs/learned/planning/plan-execution-patterns.md` — `--for-plan` → `--for-pr`
    - `docs/learned/planning/stacked-plan-branch-rebase.md` — `--for-plan` → `--for-pr`
    - `docs/learned/planning/learn-workflow.md` — `--learn-plan` → `--learn-pr`
    - `docs/learned/architecture/command-boundaries.md` — `--for-plan` → `--for-pr`
    - `docs/learned/glossary.md` — `--from-plan` → `--from-pr`

## Out of Scope

- `--from-plan-file` — refers to a local plan file path, not a PR identifier
- `--keep-plan-file` — refers to a local plan file, not a PR identifier
- `--copy-plan` — refers to copying plan context, not a PR identifier
- `CHANGELOG.md` — historical entries stay as-is
- `docs-site-archived/` — archived content, not updated
- `docs/public-content/` — public docs reference `--from-plan-file` which is out of scope

## Verification

1. Run `ruff check` and `ruff format` via devrun agent
2. Run `ty` type checker via devrun agent
3. Run unit tests for affected files via devrun agent:
   - `pytest tests/commands/branch/test_checkout_cmd.py`
   - `pytest tests/unit/cli/commands/branch/test_create_cmd.py`
   - `pytest tests/unit/cli/commands/exec/scripts/test_get_prs_for_objective.py`
   - `pytest tests/unit/cli/commands/exec/scripts/test_track_learn_result.py`
   - `pytest tests/tui/`
4. Run `make fast-ci` for full validation
