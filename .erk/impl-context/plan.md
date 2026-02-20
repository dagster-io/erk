# Plan: Draft-PR Plans in CI Remote Implementation

## Context

The CI remote implementation workflow (`plan-implement.yml`) was built entirely for issue-based plans where plan = GitHub issue and implementation = separate PR. Draft-PR plans collapse these into one entity (the draft PR IS the plan), but the CI pipeline doesn't handle this:

- `ERK_PLAN_BACKEND` is never set in CI, so all exec scripts default to issue-based
- `worker_impl_folder.py` hardcodes `provider="github"` in plan-ref.json
- `ci_update_pr_body.py` always emits `Closes #plan_id` (self-referential for draft-PR)
- `handle_no_changes.py` has the same self-close bug plus misleading "close both this issue and the PR" text
- `post_workflow_started_comment.py` bypasses the PlanBackend abstraction
- `submit.py` validates via issue API and creates a new branch+PR (both already exist for draft-PR plans)

This plan makes the full pipeline work end-to-end for draft-PR plans.

## Implementation Steps

### Step 1: Add `provider` parameter to `create_worker_impl_folder()`

**File:** `packages/erk-shared/src/erk_shared/worker_impl_folder.py`

- Add keyword-only `provider: str` parameter to `create_worker_impl_folder()` (no default value per erk conventions)
- Pass it through to `save_plan_ref()` call on line 73 instead of hardcoded `"github"`

**Test:** `tests/packages/erk_shared/test_worker_impl_folder.py`

- Update all existing calls to pass `provider="github"`
- Add test: pass `provider="github-draft-pr"`, verify plan-ref.json has correct provider

### Step 2: Pass provider from backend in `create_worker_impl_from_issue.py`

**File:** `src/erk/cli/commands/exec/scripts/create_worker_impl_from_issue.py`

- After getting `backend` on line 50, get `provider = backend.get_provider_name()`
- Pass `provider=provider` to `create_worker_impl_folder()` on line 69

**Test:** `tests/unit/cli/commands/exec/scripts/test_create_worker_impl_from_issue.py`

- Add test with `DraftPRPlanBackend` context, verify plan-ref.json has `"github-draft-pr"` provider

### Step 3: Add `plan_backend` input to `plan-implement.yml`

**File:** `.github/workflows/plan-implement.yml`

- Add `plan_backend` input to both `workflow_dispatch` and `workflow_call` (default: `"github"`)
- Add `ERK_PLAN_BACKEND: ${{ inputs.plan_backend }}` as job-level env var
- Update error path on line 140: use `gh pr comment` when `draft_pr`, else `gh issue comment`

### Step 4: Make `post_workflow_started_comment.py` use PlanBackend

**File:** `src/erk/cli/commands/exec/scripts/post_workflow_started_comment.py`

- Replace `require_issues` import with `require_plan_backend`
- Use `backend.add_comment(repo_root, str(plan_id), comment_body)` instead of `github.add_comment(repo_root, plan_id, comment_body)`
- Behavior is identical (DraftPRPlanBackend.add_comment delegates to same API) but uses correct abstraction

**Test:** `tests/unit/cli/commands/exec/scripts/test_post_workflow_started_comment.py`

- Update test to inject PlanBackend via context

### Step 5: Make `handle_no_changes.py` backend-aware

**File:** `src/erk/cli/commands/exec/scripts/handle_no_changes.py`

- Get `is_draft_pr = backend.get_provider_name() == "github-draft-pr"` (backend already required on line 180)
- In `_build_pr_body()`: accept `is_draft_pr` param
  - When True: line 116 becomes "Close this PR" (no "linked plan"), line 121 omits `Closes #{plan_id}`
- In `_build_issue_comment()`: accept `is_draft_pr` param
  - When True: "close this PR" instead of "close both this issue and the PR". The comment goes to the PR itself (since plan_id IS the PR), so also drop "See PR #{pr_number}" (it's self-referential)

**Test:** `tests/unit/cli/commands/exec/scripts/test_handle_no_changes.py`

- Add test for draft-PR mode: no `Closes #N` in body, rewording correct, comment text correct

### Step 6: Make `ci_update_pr_body.py` backend-aware

**File:** `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py`

- Read `.impl/plan-ref.json` via `read_plan_ref()` to detect provider (`.impl/` exists at this point in the workflow)
- Change `_build_pr_body()` to accept `issue_number: int | None` (line 118)
- When draft-PR:
  - Get existing PR body from `pr_result.body` (already fetched on line 187)
  - Extract metadata prefix via `extract_metadata_prefix()` from `draft_pr_lifecycle`
  - Build body: metadata_prefix + summary + `build_original_plan_section(plan_content)` + footer with `issue_number=None`
- When issue-based: existing behavior unchanged

**Reusable helpers from `erk_shared.plan_store.draft_pr_lifecycle`:**

- `extract_metadata_prefix()` - preserves metadata block
- `extract_plan_content()` - gets plan from body
- `build_original_plan_section()` - wraps plan in `<details>`

**Test:** `tests/unit/cli/commands/exec/scripts/test_ci_update_pr_body.py`

- Add test for draft-PR: metadata preserved, no `Closes #N`, original plan section present

### Step 7: Make `submit.py` support draft-PR plans

**File:** `src/erk/cli/commands/submit.py`

This is the biggest change. For draft-PR plans, the branch and PR already exist (created at plan-save time). Submit needs a separate path.

**Add `_validate_draft_pr_for_submit()` function:**

- Use `ctx.github.get_pr(repo.root, plan_number)` to validate (not `ctx.issues.get_issue()`)
- Validate: PR has `erk-plan` label, PR state is OPEN
- Get branch name from `pr_result.head_ref_name`
- Return a `ValidatedIssue`-compatible struct (reuse or create new dataclass)

**Add `_submit_draft_pr_plan()` function:**

- Fetch and checkout the existing plan branch
- Create `.worker-impl/` with `provider="github-draft-pr"` on existing branch
- Commit and push `.worker-impl/` to existing branch
- Skip: no new branch creation, no new PR creation, no `Closes #N`
- Skip: no orphaned PR cleanup (the draft PR IS the plan)

**Modify `_submit_single_issue()` or `submit_cmd()`:**

- Detect backend: `is_draft_pr = ctx.plan_backend.get_provider_name() == "github-draft-pr"`
- If draft-PR, dispatch to `_submit_draft_pr_plan()`
- If issue-based, use existing flow

**Add `plan_backend` to workflow dispatch inputs (line 777-787):**

```python
"plan_backend": "draft_pr" if is_draft_pr else "github",
```

**Use `plan_backend.add_comment()` for queued comment (line 854):**

- Replace `ctx.issues.add_comment(repo.root, issue_number, comment_body)` with backend-aware call

**Pass `provider` to `create_worker_impl_folder()` calls (lines 469, ~634):**

- `provider="github-draft-pr"` for draft-PR, `provider="github"` for issue-based

**Test:** `tests/commands/plan/test_submit.py`

- Test: draft-PR submit reuses existing branch and PR (no new creations)
- Test: workflow inputs include `plan_backend: "draft_pr"`
- Test: no `Closes #N` in any PR body updates
- Test: queued comment posted via PlanBackend

## Implementation Order

1. **Step 1** (worker_impl_folder.py) - foundation, no deps
2. **Step 2** (create_worker_impl_from_issue.py) - depends on Step 1
3. **Step 3** (plan-implement.yml) - foundation, no deps
4. **Step 4** (post_workflow_started_comment.py) - simplest exec script
5. **Step 5** (handle_no_changes.py) - moderate
6. **Step 6** (ci_update_pr_body.py) - highest complexity exec script
7. **Step 7** (submit.py) - highest overall complexity, depends on Steps 1+3

Steps 1 and 3 can be done in parallel. Steps 4-6 are independent of each other.

## Key Design Decisions

- **Backend detection in CI:** `ERK_PLAN_BACKEND` env var set at job level propagates to all exec scripts via `get_plan_backend()`
- **Scripts after .impl/ setup** can also read `plan-ref.json` for the provider (belt and suspenders)
- **No default for `provider` parameter** in `create_worker_impl_folder()` per erk conventions (LBYL, explicit)
- **Self-referential close prevention:** Every place that emits `Closes #N` must check provider and pass `issue_number=None` for draft-PR
- **submit.py uses separate function** for draft-PR path rather than branching within existing functions - cleaner separation

## Verification

1. Run unit tests for each modified exec script
2. Run `tests/packages/erk_shared/test_worker_impl_folder.py` for provider parameter
3. Run `tests/commands/plan/test_submit.py` for submit flow
4. Full CI: `/local:fast-ci`
5. Manual end-to-end: set `ERK_PLAN_BACKEND=draft_pr`, create a plan, submit it, verify workflow triggers with correct inputs
