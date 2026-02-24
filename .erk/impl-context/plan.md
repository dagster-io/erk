# Fix `erk plan check` for draft-PR plan format

## Context

CI run [#22346587637](https://github.com/dagster-io/erk/actions/runs/22346587637) failed at the "Validate plan format" step for one-shot plan issue #8045 with `[FAIL] plan-body content extractable`.

**Root cause:** The plan backend was migrated to always use `DraftPRPlanBackend` (Objective #7911), but `erk plan check` was never updated to validate the draft-PR format. The hardcoded condition at `src/erk/core/context.py:611` (`if "draft_pr" == "draft_pr"`) always selects `DraftPRPlanBackend`, which stores plan content in the issue/PR body wrapped in `<details><summary>original-plan</summary>`, not in a comment. The validator only checks for plan content in the first comment's `plan-body` metadata block.

**What happened in the CI run:**
1. One-shot dispatch created skeleton issue #8045 with `create_plan_issue()`
2. The one-shot workflow ran `erk exec plan-update-issue --plan-number 8045`
3. `plan-update-issue` resolved the backend as `DraftPRPlanBackend` (due to the hardcoded condition)
4. `DraftPRPlanBackend.update_plan_content()` wrote the plan into the issue body in `<details><summary>original-plan</summary>` format
5. `erk plan check` looked for `plan-body` in the first comment, found only the `submission-queued` comment, and failed

## Changes

### 1. Update `validate_plan_format` in `src/erk/cli/commands/plan/check_cmd.py`

After checks 1-2 (plan-header), detect the plan format using `has_original_plan_section(issue_body)`:

- **Draft-PR format** (body has `original-plan` section): Run 1 check — "plan content extractable from body" — using `extract_plan_content(issue_body)`. Verify the extracted content is non-empty.
- **Issue-based format** (no `original-plan` section): Run existing checks 3-4 unchanged (first comment exists, plan-body content extractable from comment).

Add imports:
```python
from erk_shared.plan_store.draft_pr_lifecycle import extract_plan_content, has_original_plan_section
```

### 2. Add tests in `tests/commands/plan/test_check.py`

**CLI test** — `test_check_valid_draft_pr_plan_passes`:
- Build issue body with `build_plan_stage_body(plan_header_block, plan_content)`
- Comments list can be empty or contain a non-plan comment
- Assert exit code 0 and `[PASS] plan content extractable from body`

**Programmatic test** — `test_validate_plan_format_passes_draft_pr_plan`:
- Same setup, call `validate_plan_format()` directly
- Assert `PlanValidationSuccess` with `passed=True`
- Assert check count is 3 (plan-header present, plan-header valid, plan content from body)

Add import:
```python
from erk_shared.plan_store.draft_pr_lifecycle import build_plan_stage_body
```

## Files to modify

- `src/erk/cli/commands/plan/check_cmd.py` — add format detection branch
- `tests/commands/plan/test_check.py` — add 2 tests for draft-PR format

## Existing utilities to reuse

- `has_original_plan_section(pr_body)` — `packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py:127`
- `extract_plan_content(pr_body)` — `packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py:142`
- `build_plan_stage_body(metadata_body, plan_content)` — `packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py:94` (for tests)

## Verification

1. `pytest tests/commands/plan/test_check.py` — all tests pass (existing + new)
2. `ruff check src/erk/cli/commands/plan/check_cmd.py tests/commands/plan/test_check.py`
3. `ty check src/erk/cli/commands/plan/check_cmd.py tests/commands/plan/test_check.py`
