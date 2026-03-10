# Plan: Rename Click Arguments/Options (Objective #9109, Node 2.3)

Part of Objective #9109, Node 2.3: Rename Click arguments/options: plan_number -> pr_number, plan_id -> pr_number across CLI commands.

## Context

Objective #9109 is renaming "plan" terminology to "pr" across all APIs. Phases 1 and 2.1-2.2 are done (core types, gateway ABCs, JSON output fields, TypedDict fields). Node 2.3 renames the Click argument/option declarations and their corresponding function parameter names. This must also update all callers (workflows, skills, commands) that pass these CLI flags, to prevent breakage.

## Scope

**In scope:** Click decorators, function parameter names, internal variable usage, and all callers of the renamed flags.

**Out of scope:** Help strings and error messages (node 2.4), skill/command documentation prose (node 4.2).

## Rename Mapping

| Current CLI Flag | Current Param | New CLI Flag | New Param |
|-----------------|---------------|-------------|-----------|
| `--plan-number` | `plan_number` | `--pr-number` | `pr_number` |
| `--plan-id` (int) | `plan_id` | `--pr-number` | `pr_number` |
| `--plan-id` (str) | `plan_id` | `--pr-id` | `pr_id` |
| positional `plan_number` | `plan_number` | positional `pr_number` | `pr_number` |
| positional `plan_id` (int) | `plan_id` | positional `pr_number` | `pr_number` |
| `--plan` / `-p` | `plan` | `--plan` / `-p` | `plan` (keep - this is admin test helper) |

**Special cases:**
- `update_plan_header.py`: `plan_id` is `type=str` -> rename to `pr_id` (str)
- `dispatch_cmd.py`: `plan_numbers` (tuple) -> `pr_numbers` (tuple), CLI name `plan_numbers` positional -> `pr_numbers`
- `admin.py`: `--plan` / `-p` option is for an admin test command, rename to `--pr` / `-p`

## Phase 1: Exec Script Click Decorators + Function Params (14 files)

Rename Click decorators and function parameter names. Also rename internal variable usage of the old parameter name within each function.

### Files with `--plan-number` option:
1. `src/erk/cli/commands/exec/scripts/store_tripwire_candidates.py` - `plan_number` param
2. `src/erk/cli/commands/exec/scripts/register_one_shot_plan.py` - `plan_number` param
3. `src/erk/cli/commands/exec/scripts/post_workflow_started_comment.py` - `plan_number` param + helper fn
4. `src/erk/cli/commands/exec/scripts/plan_update.py` - `plan_number` param

### Files with `--plan-id` option (int):
5. `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py` - `plan_id` param -> `pr_number`
6. `src/erk/cli/commands/exec/scripts/handle_no_changes.py` - `plan_id` param -> `pr_number` + helpers
7. `src/erk/cli/commands/exec/scripts/track_learn_result.py` - `plan_id` param -> `pr_number`
8. `src/erk/cli/commands/exec/scripts/fetch_sessions.py` - `plan_id` param -> `pr_number`
9. `src/erk/cli/commands/exec/scripts/push_session.py` - `plan_id` param -> `pr_number`
10. `src/erk/cli/commands/exec/scripts/upload_impl_session.py` - `plan_id` param -> `pr_number`

### Files with positional `plan_number` argument:
11. `src/erk/cli/commands/exec/scripts/close_pr.py` - positional `plan_number`
12. `src/erk/cli/commands/exec/scripts/get_pr_for_plan.py` - positional `plan_number`
13. `src/erk/cli/commands/exec/scripts/get_plan_info.py` - positional `plan_number`
14. `src/erk/cli/commands/exec/scripts/get_plan_metadata.py` - positional `plan_number`
15. `src/erk/cli/commands/exec/scripts/add_plan_label.py` - positional `plan_number`

### Files with positional `plan_id` argument:
16. `src/erk/cli/commands/exec/scripts/update_plan_header.py` - positional `plan_id` (str) -> `pr_id`
17. `src/erk/cli/commands/exec/scripts/create_impl_context_from_plan.py` - positional `plan_id` (int) -> `pr_number`
18. `src/erk/cli/commands/exec/scripts/setup_impl.py` - option `--issue` with dest `plan_number` -> `pr_number`

## Phase 2: Non-Exec Command Click Decorators + Function Params (3 files)

19. `src/erk/cli/commands/pr/prepare_cmd.py` - positional `plan_number` -> `pr_number`
20. `src/erk/cli/commands/pr/dispatch_cmd.py` - positional `plan_numbers` -> `pr_numbers` + extensive internal usage
21. `src/erk/cli/commands/admin.py` - `--plan`/`-p` -> `--pr`/`-p`

## Phase 3: Update Callers (Workflows + Commands + Skills)

Update all external callers that pass the renamed CLI flags:

### GitHub Workflows:
22. `.github/workflows/plan-implement.yml` - `--plan-number`, `--plan-id` flags
23. `.github/workflows/one-shot.yml` - `--plan-number` flag

### Claude Commands/Skills:
24. `.claude/commands/erk/system/one-shot-plan.md` - `--plan-number`
25. `.claude/commands/erk/system/consolidate-learn-plans-plan.md` - `--plan-number`
26. `.claude/commands/local/plan-update.md` - `--plan-number`
27. `.claude/commands/erk/learn.md` - `--plan-number`, `--plan-id`
28. `.claude/skills/erk-planning/SKILL.md` - references to CLI args
29. `.claude/skills/erk-planning/references/workflow.md` - references to CLI args

## Phase 4: Update Internal Variable Names

Within each modified function, rename all local variables that shadow the old parameter name:
- `plan_number` -> `pr_number` (local vars, f-strings)
- `plan_id` -> `pr_number` or `pr_id` (matching the param rename)
- Helper function parameters that receive the renamed values

**Note:** Do NOT rename error message text or help strings - those are node 2.4.

## Verification

1. Run `ruff check` to verify no syntax errors
2. Run `ty` for type checking
3. Run `pytest tests/` to verify no test breakage
4. Grep for remaining `plan_number` and `plan_id` in Click decorators to verify completeness:
   - `rg "click\.(argument|option).*plan_(number|id)" src/erk/cli/`
   - `rg "\-\-plan-(number|id)" .github/ .claude/`
