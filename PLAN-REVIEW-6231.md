# Plan: Objective #6201 Steps 3.2-3.4 — Complete Review PR Lifecycle

Part of Objective #6201, Steps 3.2, 3.3, 3.4

## Goal

Extend the existing `plan-review-complete` command to fully close out the review lifecycle: delete the review branch, clear metadata, and guard against redundant re-reviews.

## Implementation

### Phase 1: Schema — Add `last_review_pr` field

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py`

1. Add constant `LAST_REVIEW_PR: Literal["last_review_pr"] = "last_review_pr"` near existing `REVIEW_PR` constant (~line 393)
2. Add `LAST_REVIEW_PR` to `PlanHeaderSchema.validate()` `optional_fields` set (~line 465-496)
3. Add validation block for `last_review_pr` (same pattern as `review_pr` at lines 730-734): must be int or null, must be positive when provided

### Phase 2: Metadata functions — `clear_plan_header_review_pr`

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py`

1. Import `LAST_REVIEW_PR` from schemas
2. Add `clear_plan_header_review_pr(issue_body: str) -> str`:
   - Extract plan-header block
   - Archive current `review_pr` value to `last_review_pr` (if not None)
   - Set `review_pr` to None
   - Validate and re-render
   - Same pattern as existing `update_plan_header_review_pr` (~line 1337)

### Phase 3: Extend `plan-review-complete` command (Steps 3.2 + 3.3)

**File:** `src/erk/cli/commands/exec/scripts/plan_review_complete.py`

Extend `_plan_review_complete_impl` with three new operations after the existing LBYL checks:

1. **Get PR details** (before closing): `github.get_pr(repo_root, review_pr)` → `PRDetails | PRNotFound`. LBYL: if `PRNotFound`, raise with error `"pr_not_found"`. Extract `head_ref_name` for the branch name.
2. **Close PR** (existing): `github.close_pr(repo_root, review_pr)`
3. **Delete branch** (Step 3.2): `github.delete_remote_branch(repo_root, branch_name)` → returns `bool`
4. **Clear metadata** (Step 3.3): Call `clear_plan_header_review_pr(issue.body)` to get updated body, then `github_issues.update_issue_body(repo_root, issue_number, BodyText(content=updated_body))`

Update response dataclass:
```python
@dataclass(frozen=True)
class PlanReviewCompleteSuccess:
    success: bool
    issue_number: int
    pr_number: int
    branch_name: str
    branch_deleted: bool
```

New imports: `PRNotFound`, `PRDetails` from types; `clear_plan_header_review_pr` from plan_header; `BodyText` from types.

### Phase 4: Guard against re-review (Step 3.4)

**File:** `.claude/commands/erk/review-plan.md`

Update the skill's Step 2 (Check for Existing Review) to add after the existing `review_pr` check:

- Run `erk exec get-plan-metadata <issue> last_review_pr`
- If value is not null: display warning "Plan was previously reviewed via PR #N" and ask user to confirm before creating a new review PR

This is a soft guard — the user can proceed. No code changes needed beyond updating the skill markdown.

## Files to Modify

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py` | Add `LAST_REVIEW_PR` constant and validation |
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py` | Add `clear_plan_header_review_pr` function |
| `src/erk/cli/commands/exec/scripts/plan_review_complete.py` | Extend with branch deletion, metadata clearing |
| `tests/unit/cli/commands/exec/scripts/test_plan_review_complete.py` | Update existing + add new tests |
| `.claude/commands/erk/review-plan.md` | Add `last_review_pr` guard in Step 2 |

## Tests

**Update existing tests** in `test_plan_review_complete.py`:
- All existing tests need `pr_details` configured in `FakeGitHub` constructor (since impl now calls `get_pr`). For error tests that should fail before reaching `get_pr`, no change needed.

**New test cases:**

1. `test_plan_review_complete_deletes_branch` — asserts `fake_gh.deleted_remote_branches` contains the branch name, output JSON has `branch_name` and `branch_deleted: true`
2. `test_plan_review_complete_clears_review_pr_metadata` — asserts `fake_gh_issues.updated_bodies` was called, updated body has `review_pr: null`
3. `test_plan_review_complete_sets_last_review_pr` — asserts updated body has `last_review_pr: <old_pr_number>`
4. `test_plan_review_complete_pr_not_found` — no `pr_details` configured → exit 1, error `"pr_not_found"`
5. `test_plan_review_complete_branch_delete_returns_false` — command still succeeds with `branch_deleted: false`

**Metadata unit tests** (add to existing plan_header test file or new file):
- `test_clear_plan_header_review_pr` — review_pr becomes null, last_review_pr gets old value
- `test_clear_plan_header_review_pr_no_block_raises` — ValueError on missing block

## Verification

1. Run unit tests: `pytest tests/unit/cli/commands/exec/scripts/test_plan_review_complete.py -v`
2. Run metadata tests for plan_header
3. Run `ruff` and `ty` checks on modified files
4. Manual: `erk exec plan-review-complete <issue>` on a plan with active review PR — verify PR closed, branch deleted, metadata cleared

## Related Documentation

- Skills: `dignified-python`, `fake-driven-testing`
- Docs: `docs/learned/planning/plan-schema.md`