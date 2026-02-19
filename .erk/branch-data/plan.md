# Plan: Update `erk plan submit` for Draft PR Plans

## Context

When plans are stored as draft PRs (via `ERK_PLAN_BACKEND=draft_pr`), `erk plan submit` currently treats them as issues: it creates a **new** branch with `P{N}-` prefix, creates a **new** draft PR, and uses "issue" language throughout. This is wrong because:

1. The plan draft PR already has a branch (created during `plan save`)
2. The plan draft PR IS the implementation PR - no separate PR should be created
3. All user-facing text says "issue" when it should say "plan"

The fix: make `submit` backend-aware so it reuses the existing branch/PR for draft PR plans, and update all language from "issue" to "plan".

## Primary File

`src/erk/cli/commands/submit.py` (~1017 lines)

## Changes

### 1. Add backend detection helper

```python
def _is_draft_pr_backend(ctx: ErkContext) -> bool:
    return ctx.plan_backend.get_provider_name() == "github-draft-pr"
```

### 2. Rename data types

**`ValidatedIssue` → `ValidatedPlan`**:

- Keep `number: int` (plan number - issue# or PR#)
- Replace `issue: IssueInfo` with `plan: Plan` (from `plan_store.types`)
- Add `is_draft_pr: bool`
- Keep `branch_name`, `branch_exists`, `pr_number`, `is_learn_origin`

**`SubmitResult`** field renames:

- `issue_number` → `plan_number`
- `issue_title` → `plan_title`
- `issue_url` → `plan_url`

### 3. Refactor validation: `_validate_issue_for_submit` → `_validate_plan_for_submit`

Use `ctx.plan_backend.get_plan()` for **both** backends (returns a `Plan` with `labels`, `state`, `url`, `title`).

**For issue-based plans** (existing behavior):

- Generate branch name with `generate_issue_branch_name()`
- Check for existing local branches with `_find_existing_branches_for_issue()`
- Check if branch exists on remote

**For draft PR plans** (new path):

- Get PR details via `ctx.github.get_pr(repo.root, plan_number)` to get `head_ref_name` (the existing branch)
- Branch always exists (was created during plan save)
- PR number = plan number (the plan IS the PR)
- Skip `_find_existing_branches_for_issue()` entirely
- Skip `_prompt_existing_branch_action()` entirely

### 4. Add draft PR submission path in `_submit_single_plan`

Rename `_submit_single_issue` → `_submit_single_plan`. Add early return for draft PR plans:

**Draft PR path** (new, much simpler):

1. Fetch the remote branch: `ctx.git.remote.fetch_branch(repo.root, "origin", branch_name)`
2. Create local tracking branch if needed, checkout
3. Fetch plan content via `ctx.plan_store.get_plan()`
4. Create `.worker-impl/` folder (reuse existing `create_worker_impl_folder()`)
5. Commit: `"Add plan for #{plan_number}"`
6. Push to remote
7. Skip draft PR creation entirely (plan PR already exists)
8. Skip `_close_orphaned_draft_prs()` (no separate issue to check)
9. Restore original branch
10. Continue to workflow dispatch (same as issue path)

**Issue path** (existing behavior): unchanged.

### 5. Update workflow dispatch section

The workflow dispatch section in `_submit_single_plan` is shared for both paths. Only difference:

- Plan number is used as `plan_id` (works for both)
- PR number: for draft PR = plan number, for issue = newly created PR number

The queued event comment and dispatch metadata writes already use `ctx.plan_backend` which is backend-agnostic.

### 6. Update all user-facing strings

| Current                                                 | Updated                                            |
| ------------------------------------------------------- | -------------------------------------------------- |
| `"Submit issue for remote AI implementation"`           | `"Submit plan for remote AI implementation"`       |
| `"Validating {N} issue(s)..."`                          | `"Validating {N} plan(s)..."`                      |
| `"Validating issue #{N}..."`                            | `"Validating plan #{N}..."`                        |
| `"All {N} issue(s) validated"`                          | `"All {N} plan(s) validated"`                      |
| `"Submitting issue #{N}..."`                            | `"Submitting plan #{N}..."`                        |
| `"Submitting issue {i}/{N}: #{num}"`                    | `"Submitting plan {i}/{N}: #{num}"`                |
| `"{N} issue(s) submitted successfully!"`                | `"{N} plan(s) submitted successfully!"`            |
| `"Submitted issues:"`                                   | `"Submitted plans:"`                               |
| `"Issue: {url}"`                                        | `"Plan: {url}"`                                    |
| `"Issue #{N} not found"`                                | `"Plan #{N} not found"`                            |
| `"Issue #{N} does not have erk-plan label"`             | `"Plan #{N} does not have erk-plan label"`         |
| `"Cannot submit non-plan issues..."`                    | `"Cannot submit non-plans..."`                     |
| `"Issue #{N} is CLOSED"`                                | `"Plan #{N} is CLOSED"`                            |
| `"Cannot submit closed issues..."`                      | `"Cannot submit closed plans..."`                  |
| `"Dispatch metadata written to issue"`                  | `"Dispatch metadata written to plan"`              |
| `"Issue Queued for Implementation"` (event title)       | `"Plan Queued for Implementation"`                 |
| `"Issue submitted by..."`                               | `"Plan submitted by..."`                           |
| `"Found existing local branch(es) for this issue:"`     | `"Found existing local branch(es) for this plan:"` |
| `"Add plan for issue #{N}"` (commit msg)                | `"Add plan for #{N}"`                              |
| `"[erk-plan] Initialize implementation for issue #{N}"` | `"[erk-plan] Initialize implementation for #{N}"`  |

### 7. Update CLI argument and help text

- Rename `issue_numbers` parameter → `plan_numbers`
- Update help docstring: `ISSUE_NUMBERS` → `PLAN_NUMBERS`
- Update docstring examples and requirements text

### 8. Update helper function names

- `_format_issue_ref` → keep name (only used in issue path, internal)
- `is_issue_learn_plan` → `is_learn_plan` (just checks labels)
- `_find_existing_branches_for_issue` → keep name (only used in issue path)
- `_close_orphaned_draft_prs` → keep name (only used in issue path)
- `_validate_issue_for_submit` → `_validate_plan_for_submit`
- `_submit_single_issue` → `_submit_single_plan`

### 9. Import changes

Add:

- `from erk_shared.plan_store.types import Plan, PlanNotFound` (Plan already imported via PlanNotFound)
- `from erk_shared.gateway.github.types import PRNotFound` (already imported)

Remove (if unused after refactor):

- `from erk_shared.gateway.github.issues.types import IssueInfo, IssueNotFound` (may still be needed for issue path)

Keep `IssueNotFound` since the issue path still uses `ctx.issues.get_issue()` for things like learn plan detection in `submit_cmd`. Actually, the learn plan detection in `submit_cmd` (lines 938-960) calls `ctx.issues.get_issue()` directly. For draft PR plans, this would need to use `ctx.plan_backend.get_plan()` instead. Let me handle this: use `ctx.plan_backend.get_plan()` to check for learn plan labels since Plan has `labels`.

## Tests

### String assertion updates

All test files in `tests/commands/submit/` need "issue" → "plan" string updates:

- `test_basic_submission.py`: `"issue(s) submitted successfully"` → `"plan(s) submitted successfully"`
- `test_validation.py`: `"does not have erk-plan label"`, `"Cannot submit non-plan"`, etc.
- Other test files: similar string updates

### Draft PR submission tests

Add tests in `test_basic_submission.py` (or a new `test_draft_pr_submission.py`) that:

1. Set up a plan with `backend="draft_pr"`
2. Pre-configure the branch on remote (since it was "created during plan save")
3. Call `submit_cmd` with the plan number
4. Verify: NO new branch created, NO new PR created
5. Verify: `.worker-impl/` committed to existing branch
6. Verify: workflow triggered with correct inputs (plan_id = pr_number)

The conftest `setup_submit_context` already supports `backend="draft_pr"` and creates a `DraftPRPlanBackend` with `FakeGitHub`.

For draft PR tests, also need to set up:

- `FakeGit.remote_branches` with the plan's branch
- `FakeGitHub.prs` with the plan's PR

## Verification

1. Run submit tests: `uv run pytest tests/commands/submit/ -v`
2. Run validation tests: `uv run pytest tests/commands/submit/test_validation.py -v`
3. Type check: `uv run ty check src/erk/cli/commands/submit.py`
4. Lint: `uv run ruff check src/erk/cli/commands/submit.py`
5. Manual smoke test (if ERK_PLAN_BACKEND=draft_pr is configured):
   - Create a draft PR plan via plan mode
   - Run `erk plan submit <plan_number>`
   - Verify it reuses the existing branch and PR
