# Eliminate All Issue-Based Plan References

## Context

Erk migrated away from GitHub Issues as a plan storage backend to draft PRs. That migration removed `PlanBackendType` and the issue-based code paths, but left behind many lingering references: class names (`IssueNextSteps`, `IssueNumberEvent`), function names (`format_next_steps_plain`), comments, and documentation. This PR scours the codebase to eliminate every remaining "issue-based plan" reference.

## Core Type Changes

### 1. Consolidate `IssueNextSteps` + `PlannedPRNextSteps` → `PlanNextSteps`
**File:** `packages/erk-shared/src/erk_shared/output/next_steps.py`

- Delete `IssueNextSteps` entirely
- Rename `PlannedPRNextSteps` → `PlanNextSteps`
  - Rename field `pr_number: int` → `plan_number: int`
  - Remove unused `branch_name: str` field (stored but never used in any property)
- Delete `format_next_steps_plain()` (dead production code — only called in tests that test `IssueNextSteps`)
- Rename `format_planned_pr_next_steps_plain()` → `format_plan_next_steps_plain()`
  - Remove `branch_name` parameter (was passed to `PlannedPRNextSteps` but never used)
- Update `format_next_steps_markdown()` to use `PlanNextSteps` instead of `IssueNextSteps`
- Update module docstring ("Issue and planned PR next steps" → "Plan next steps")

### 2. Rename `IssueNumberEvent` → `PlanNumberEvent`

**Files:**
- `packages/erk-shared/src/erk_shared/core/prompt_executor.py` — definition + `ExecutorEvent` union
- `src/erk/core/prompt_executor.py` — re-exports
- `src/erk/core/codex_output_parser.py` — usage
- `src/erk/cli/output.py` — import + match cases at lines 222, 358, 475

## Caller Updates

### 3. Update callers of renamed functions
- `src/erk/cli/commands/pr/create_cmd.py`: `format_planned_pr_next_steps_plain` → `format_plan_next_steps_plain`, remove `branch_name=` arg
- `src/erk/cli/commands/exec/scripts/plan_save.py`: same as above
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py`: `format_next_steps_markdown` signature unchanged, no update needed

## Code Comment Cleanup

Update or remove inline "issue-based" references in:
- `src/erk/core/services/plan_list_service.py` lines 373, 375 (docstring says "unused for issue-based plans")
- `src/erk/core/services/objective_list_service.py` line 35 ("issue-based path" comment)
- `src/erk/core/context.py` line 629 ("Objectives are always issue-based regardless of plan backend")
- `src/erk/cli/commands/pr/shared.py` line 278 (docstring "issue-based plan details format")
- `src/erk/cli/commands/pr/check_cmd.py` line 117 (comment "vs issue-based (comment)")
- `packages/erk-shared/src/erk_shared/plan_store/planned_pr_lifecycle.py` lines 4, 21, 27 (module docstring)

## Test Updates

### 4. Update/remove test classes for deleted types
- `tests/unit/shared/test_next_steps.py`: Remove `TestIssueNextSteps` class and `format_next_steps_plain` tests; update remaining tests to use `PlanNextSteps`
- `packages/erk-shared/tests/unit/output/test_next_steps.py`: Rename `PlannedPRNextSteps` → `PlanNextSteps`, `format_planned_pr_next_steps_plain` → `format_plan_next_steps_plain`, remove `format_next_steps_plain` tests

### 5. Update event rename in tests/fakes
- `tests/unit/core/test_codex_output_parser.py`: `IssueNumberEvent` → `PlanNumberEvent`
- `tests/fakes/prompt_executor.py`:
  - `IssueNumberEvent` → `PlanNumberEvent`
  - `simulated_issue_number` → `simulated_plan_number` (field + constructor arg + docstring)

### 6. Minor test docstring fixes
- `tests/unit/cli/commands/exec/scripts/test_setup_impl.py` line 4: remove "issue-based setup via `_handle_issue_setup`"
- `tests/test_utils/plan_helpers.py` line 247: update "migration helper: converts issue-based test data" comment

## Documentation Cleanup

### 7. Delete `docs/topics/why-github-issues.md`
This entire document explains why Erk used GitHub Issues for plans — a historical rationale for a backend that no longer exists. Delete it.

Remove the link from `docs/topics/index.md`.

### 8. Update `docs/learned/planning/*.md` files
Update "issue-based" references in:
- `docs/learned/planning/next-steps-output.md` — rewrite to describe unified `PlanNextSteps` and `format_plan_next_steps_plain`; remove `IssueNextSteps` vs `PlannedPRNextSteps` framing; remove table row for `format_next_steps_plain (CLI issue plans)`
- `docs/learned/planning/lifecycle.md` — remove lines 292 (P-prefix note), 1085–1087 (issue-based comparison block)
- `docs/learned/planning/planned-pr-lifecycle.md` — remove "Unlike issue-based plans" comparative framing; update cross-reference
- `docs/learned/planning/planned-pr-learn-pipeline.md` — remove "vs. issue-based plans" framing
- `docs/learned/planning/planned-pr-backend.md` — remove "P-prefix: issue-based plan branches" entry
- `docs/learned/planning/index.md` — update read-when conditions that mention `IssueNextSteps`/`PlannedPRNextSteps` and "issue-based"

## Verification

1. Run `make fast-ci` (via devrun agent) — all tests should pass with the renamed types
2. Verify no remaining references: `grep -rn "issue-based\|IssueNextSteps\|IssueNumberEvent" --include="*.py" --include="*.md" | grep -v CHANGELOG`
3. Confirm `format_plan_next_steps_plain` is called correctly from `create_cmd.py` and `plan_save.py` without `branch_name`
