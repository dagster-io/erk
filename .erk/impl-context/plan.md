# Plan: Objective #8381 — Phase 7 Cleanup (Nodes 7.1, 7.2, 7.4)

## Context

Objective #8381 standardizes plan-as-PR terminology across the codebase. Phases 1-6 updated docs and user-facing strings. Phase 7 tackles dead code removal and class renaming to eliminate remaining "Issue" terminology from internal code. Nodes 7.1, 7.2, and 7.4 are combined into one PR since they're closely related.

**Key findings**:
- Node 7.1: `IssuePlanSource` and `prepare_plan_source_from_issue()` are genuinely dead — no callers exist. Remove them.
- Node 7.2: Script already deleted in prior commit. Only a stale docstring reference remains.
- Node 7.4: `IssueNextSteps`/`IssueNumberEvent` don't exist. Real rename targets are `IssueBranchSetup`, `IssueValidationFailed`, `PrepareIssueResult` in `issue_workflow.py`, plus the module name itself.

## Changes

### 1. Delete dead code (Node 7.1)

In `src/erk/cli/commands/implement_shared.py`:
- Delete `IssuePlanSource` class (lines 483-495)
- Delete `prepare_plan_source_from_issue()` function (lines 498-557)
- Remove now-unused imports: `IssueBranchSetup`, `IssueValidationFailed` from `erk_shared.issue_workflow` (lines 20-21), `prepare_plan_for_worktree` (line 22), `click` (if only used by deleted code), `user_output` (if only used by deleted code)

### 2. Clean up stale docstring (Node 7.2)

In `packages/erk-shared/src/erk_shared/plan_store/create_plan_draft_pr.py` line 6:
- Remove `- erk exec create-plan-from-context (stdin plan)` from the docstring list

### 3. Rename module `issue_workflow.py` → `plan_workflow.py` (Node 7.4)

- Rename file: `packages/erk-shared/src/erk_shared/issue_workflow.py` → `plan_workflow.py`
- Update module docstring
- Update all imports in 4 source files + 1 test file:
  - `src/erk/cli/commands/branch/create_cmd.py`
  - `src/erk/cli/commands/branch/checkout_cmd.py`
  - `src/erk/cli/commands/wt/create_cmd.py`
  - `src/erk/cli/commands/implement_shared.py` (if any imports remain after step 1)
  - `tests/unit/shared/test_issue_workflow.py`
- Update docstring reference in `packages/erk-shared/src/erk_shared/naming.py` (line 283)

### 4. Rename classes and type alias in `plan_workflow.py` (Node 7.4)

| Current | New |
|---------|-----|
| `IssueBranchSetup` | `PlanBranchSetup` |
| `IssueValidationFailed` | `PlanValidationFailed` |
| `PrepareIssueResult` | `PreparePlanResult` |

- Update class definitions, docstrings, return type annotations
- Update `prepare_plan_for_worktree()` return annotation and docstring
- Update all `isinstance()` checks and type annotations in the 3 importing source files
- Update all references in test file

### 5. Rename test file

- `tests/unit/shared/test_issue_workflow.py` → `test_plan_workflow.py`
- Update test docstrings that reference "issue"

### 6. Update remaining docstrings

- In `plan_workflow.py`: update prose like "preparing an issue for worktree creation" → "preparing a plan for worktree creation"
- Error messages referencing "Issue #" → "Plan #" where appropriate (check `IssueValidationFailed` construction sites)

**Note on field names**: Fields like `issue_url`, `issue_title`, `objective_issue` in `PlanBranchSetup` should NOT be renamed — they refer to GitHub issue URLs/titles which is still accurate. Only class/function/module names change.

## Files Modified

1. `packages/erk-shared/src/erk_shared/issue_workflow.py` → renamed to `plan_workflow.py` (class renames + docstrings)
2. `src/erk/cli/commands/implement_shared.py` (delete dead code + update remaining imports)
3. `src/erk/cli/commands/branch/create_cmd.py` (imports + class name usage)
4. `src/erk/cli/commands/branch/checkout_cmd.py` (imports + class name usage)
5. `src/erk/cli/commands/wt/create_cmd.py` (imports + class name usage)
6. `packages/erk-shared/src/erk_shared/naming.py` (docstring reference to module name)
7. `packages/erk-shared/src/erk_shared/plan_store/create_plan_draft_pr.py` (stale docstring)
8. `tests/unit/shared/test_issue_workflow.py` → renamed to `test_plan_workflow.py`

## Verification

1. Run `ruff check` and `ruff format` on all modified files
2. Run `ty` for type checking
3. Run `pytest tests/unit/shared/test_plan_workflow.py` (renamed test file)
4. Run `pytest tests/unit/cli/commands/` to verify callers still work
5. Grep for any remaining `IssueBranchSetup|IssueValidationFailed|IssuePlanSource|PrepareIssueResult|prepare_plan_source_from_issue` to confirm complete rename
6. Run full fast-ci

## Objective Updates

After landing, update objective #8381:
- Mark 7.1 as done
- Mark 7.2 as done (was already deleted, docstring cleaned up)
- Mark 7.4 as done (IssueNextSteps/IssueNumberEvent don't exist; real targets renamed)
