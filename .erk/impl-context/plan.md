# Eliminate "Closes #N" from PR Bodies

## Context

Plans migrated from GitHub issues to draft PRs (`github-draft-pr` backend). The "Closes #N" pattern in PR footers was designed for issue-based plans — merging a PR would auto-close its linked issue. With draft PRs, the plan IS the PR, making "Closes #N" self-referential (e.g., PR #8232 says "Closes #8232"). This vestigial pattern should be completely eliminated from the system.

## Changes

### 1. Remove "Closes #N" from `build_pr_body_footer()`

**File:** `packages/erk-shared/src/erk_shared/gateway/github/pr_footer.py`

- Remove `issue_number` and `plans_repo` parameters from `build_pr_body_footer()`
- Remove the `ClosingReference` dataclass
- Remove `extract_closing_reference()` function
- The function just generates the `---` separator + checkout command

### 2. Remove `ClosingReference` imports from finalize

**File:** `packages/erk-shared/src/erk_shared/gateway/gt/operations/finalize.py`

- Remove `_extract_closing_ref_from_pr()` function (unused — only caller was deleted)
- Remove imports of `ClosingReference`, `extract_closing_reference`

### 3. Remove `has_issue_closing_reference()`

**File:** `packages/erk-shared/src/erk_shared/gateway/pr/submit.py`

- Delete `has_issue_closing_reference()` function

### 4. Replace `issue_number` with `plan_id` on `SubmitState`

**File:** `src/erk/cli/commands/pr/submit_pipeline.py`

- Rename field `issue_number: int | None` → `plan_id: str | None` on `SubmitState`
- In `prepare_state()`: set `plan_id` from `validate_plan_linkage()` directly (no `int()` conversion)
- In auto-repair block (lines 151-162): use `plan_id` instead of `issue_number`
- In `_graphite_first_flow()`: change `is_plan_impl = state.issue_number is not None` → `is_plan_impl = state.plan_id is not None`
- In `_core_submit_flow()` (3 call sites): remove `issue_number` from `build_pr_body_footer()` calls
- In `finalize_pr()`: remove `issue_number=None` from `assemble_pr_body()` call
- In `generate_description()` (~line 792): same
- In `make_initial_state()`: change `issue_number=None` → `plan_id=None`

### 5. Remove `issue_number` from `assemble_pr_body()`

**File:** `src/erk/cli/commands/pr/shared.py`

- Remove `issue_number` and `plans_repo` parameters from `assemble_pr_body()`
- Update the call to `build_pr_body_footer()` (just pass `pr_number`)
- In `build_plan_details_section()`: change `"(Issue #{issue_num})"` → `"(Plan #{issue_num})"` (or remove the parenthetical)

### 6. Update `rewrite_cmd.py`

**File:** `src/erk/cli/commands/pr/rewrite_cmd.py`

- Remove `issue_number=None` kwarg from `assemble_pr_body()` call

### 7. Remove "Closes #N" check from `pr check`

**File:** `src/erk/cli/commands/pr/check_cmd.py`

- Remove the `has_issue_closing_reference` import
- Remove Check 1 (issue closing reference) entirely from `_check_pr_body()`

### 8. Simplify `objective_helpers.py`

**File:** `src/erk/cli/commands/objective_helpers.py`

- Remove `has_issue_closing_reference` import
- Remove the closing-ref logic. Since "Closes #N" no longer exists, always offer to close the plan manually after landing if it's still open.

### 9. Update/delete exec scripts

**File:** `src/erk/cli/commands/exec/scripts/get_closing_text.py`
- Delete this command entirely. It only outputs "Closes #N" text.

**File:** `src/erk/cli/commands/exec/scripts/get_pr_body_footer.py`
- Remove `--plan-number` and `--plans-repo` options
- Update call to `build_pr_body_footer()` (just pass `pr_number`)

**File:** `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py`
- Remove `plan_number` parameter from `_build_pr_body()`
- Remove `--planned-pr` flag (no longer needed for "Closes #" differentiation — keep `is_planned_pr` parameter for the metadata_prefix path which is still needed for plan section format)

Wait — `--planned-pr` controls both:
1. Whether to include "Closes #N" (removing)
2. Whether to use `extract_plan_header_block` / `build_original_plan_section` format (keeping)

So `--planned-pr` flag stays, but the `plan_number=None` branch in `_build_pr_body` is simplified.

**File:** `src/erk/cli/commands/exec/scripts/register_one_shot_plan.py`
- Remove "Op 3: PR closing reference" block entirely (lines 90-104)

### 10. Update `output_filter.py`

**File:** `src/erk/core/output_filter.py`

- Remove the "Closes #123" fallback pattern (lines 295-298)

### 11. Update CI workflow

**File:** `.github/workflows/plan-implement.yml`

- The `PLANNED_PR_FLAG` logic (lines 427-435) can be simplified — `--planned-pr` flag may still be needed for plan section format, but `plan_number` no longer feeds into "Closes #N"

### 12. Update slash command

**File:** `.claude/commands/erk/git-pr-push.md`

- Remove Step 6 (Get Closing Text) entirely
- Remove `closing_text` usage from Step 7 (Create GitHub PR)
- In Step 7.5 (Add Checkout Footer): remove `--plan-number` from `get-pr-body-footer` call
- Update Step 8 description to remove closing reference validation

### 13. Update skill reference

**File:** `.claude/skills/erk-exec/reference.md`

- Update `get-pr-body-footer` documentation (remove `--plan-number`, `--plans-repo`)
- Remove `get-closing-text` entry
- Update any descriptions mentioning "Closes #N"

### 14. Update exec command registration

Remove `get_closing_text` from the Click group that registers exec subcommands.

### 15. Update documentation

**File:** `docs/learned/architecture/pr-body-assembly.md`
- Remove the tripwire about "adding Closes #N for github-draft-pr backend"
- Remove the `issue_number` column from the backend comparison table
- Update function signatures described in the doc

### 16. Update tests

Delete or update tests that verify "Closes #N" behavior:

- `packages/erk-shared/tests/unit/github/test_pr_footer.py` — Remove `TestBuildPrBodyFooterWithIssue`, `TestExtractClosingReference`, `TestClosingReference` classes and related tests. Keep footer structure tests.
- `tests/unit/test_pr_footer.py` — Remove closing reference test methods
- `tests/commands/pr/test_check.py` — Remove all "Closes #N" assertions
- `tests/unit/cli/commands/exec/scripts/test_get_closing_text.py` — Delete entirely
- `tests/unit/cli/commands/exec/scripts/test_get_pr_body_footer.py` — Update to not pass `--plan-number`
- `tests/unit/cli/commands/exec/scripts/test_ci_update_pr_body.py` — Remove "Closes #" assertions
- `tests/unit/cli/commands/exec/scripts/test_register_one_shot_plan.py` — Remove self-referential close test
- `tests/commands/pr/test_rewrite.py` — Remove "Closes #" assertion
- `tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py` — Remove "Closes #" assertion
- `tests/unit/cli/commands/exec/scripts/test_update_pr_description.py` — Remove "Closes #" assertions
- `tests/commands/land/test_plan_issue_closure.py` — Update for simplified closure logic
- `tests/core/test_prompt_executor.py` — Remove "Closes #N" pattern tests
- `tests/unit/cli/commands/exec/scripts/test_pr_sync_commit.py` — Remove "Closes #" from test PR bodies
- `tests/unit/cli/commands/exec/scripts/test_set_local_review_marker.py` — Remove "Closes #" from test bodies
- `tests/unit/services/test_plan_list_service.py` — Remove "Closes #" from test bodies

## Verification

1. Run `make fast-ci` to verify all tests pass
2. Run `make all-ci` for full suite including integration tests
3. Verify `erk pr submit` in a test worktree produces PR body without "Closes #"
4. Verify `erk pr check` no longer validates closing references
5. Verify `erk exec get-pr-body-footer --pr-number 123` outputs footer without closing ref
