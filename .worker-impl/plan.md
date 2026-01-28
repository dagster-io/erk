# Plan: Objective #6201 Steps 1.3 and 1.4

**Part of Objective #6201, Steps 1.3 and 1.4**

Create PR via `gh pr create` with title/body linking back to plan issue, then update plan issue metadata to track the review PR number.

## Summary

Implement a single `erk exec plan-create-review-pr` command that:

1. Creates a draft PR from the plan review branch
2. Updates the plan issue's metadata with the new `review_pr` field

## Implementation Phases

### Phase 1: Schema Extension

Add `review_pr` field to plan-header schema.

**File: `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py`**

1. Add `"review_pr"` to `PlanHeaderFieldName` Literal type (~line 346)
2. Add constant: `REVIEW_PR: Literal["review_pr"] = "review_pr"` (~line 389)
3. Add to `PlanHeaderSchema` docstring and optional_fields validation

### Phase 2: Plan Header Functions

Add update and extract functions for `review_pr`.

**File: `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py`**

1. Add import: `REVIEW_PR` from schemas
2. Add `update_plan_header_review_pr(issue_body: str, review_pr: int) -> str`
   - Follow pattern of `update_plan_header_comment_id` (lines 463-501)
3. Add `extract_plan_header_review_pr(issue_body: str) -> int | None`
   - For Phase 2 of objective (pr-address detection)

### Phase 3: CLI Command

Create the new command.

**File: `src/erk/cli/commands/exec/scripts/plan_create_review_pr.py` (NEW)**

Structure (following `plan_create_review_branch.py` pattern):

- `CreateReviewPRSuccess` dataclass: `success, issue_number, pr_number, pr_url`
- `CreateReviewPRError` dataclass: `success, error, message`
- `CreateReviewPRException` for LBYL error handling
- `_format_pr_body(issue_number, plan_title)` - PR body with warning about not merging
- `_create_review_pr_impl()` - core logic
- `plan_create_review_pr` Click command

Command signature:

```
erk exec plan-create-review-pr <issue-number> <branch-name> <plan-title>
```

Logic:

1. Create draft PR with `github.create_pr(repo_root, branch, title, body, base="master", draft=True)`
2. LBYL: Check issue exists via `github_issues.issue_exists()`
3. Get issue body, update with `update_plan_header_review_pr()`
4. Write updated body via `github_issues.update_issue_body()`

PR Format:

- Title: `Plan Review: {plan_title} (#{issue_number})`
- Body: Markdown with link to issue, warning that PR won't be merged

### Phase 4: Command Registration

**File: `src/erk/cli/commands/exec/group.py`**

1. Add import for `plan_create_review_pr`
2. Add registration: `exec_group.add_command(plan_create_review_pr, name="plan-create-review-pr")`
   - Insert alphabetically (~line 197)

### Phase 5: Unit Tests

**File: `tests/unit/cli/commands/exec/scripts/test_plan_create_review_pr.py` (NEW)**

Test cases:

1. `test_plan_create_review_pr_success` - PR created, metadata updated
2. `test_plan_create_review_pr_pr_title_format` - Verify title contains issue reference
3. `test_plan_create_review_pr_pr_body_format` - Verify body has issue link and warning
4. `test_plan_create_review_pr_draft_mode` - Verify draft=True passed
5. `test_plan_create_review_pr_metadata_updated` - Verify issue body has review_pr field
6. `test_plan_create_review_pr_issue_not_found` - Error case
7. `test_json_output_structure_success` - Verify output schema
8. `test_json_output_structure_error` - Verify error schema

Use `FakeGitHub` and `FakeGitHubIssues` following existing test patterns.

### Phase 6: Schema Tests

**File: `packages/erk-shared/tests/unit/github/metadata/test_plan_header.py`**

Add tests for:

- `test_update_plan_header_review_pr`
- `test_extract_plan_header_review_pr`
- `test_extract_plan_header_review_pr_not_present`

## Files to Modify

| File                                                                        | Action                       |
| --------------------------------------------------------------------------- | ---------------------------- |
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py`     | Add `REVIEW_PR` field        |
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py` | Add update/extract functions |
| `src/erk/cli/commands/exec/scripts/plan_create_review_pr.py`                | NEW - command impl           |
| `src/erk/cli/commands/exec/group.py`                                        | Register command             |
| `tests/unit/cli/commands/exec/scripts/test_plan_create_review_pr.py`        | NEW - command tests          |
| `packages/erk-shared/tests/unit/github/metadata/test_plan_header.py`        | Add function tests           |

## Related Documentation

- Skills to load: `fake-driven-testing`, `dignified-python`
- Pattern reference: `plan_create_review_branch.py`, `update_plan_header_comment_id()`

## Verification

1. **Unit tests**: Run `uv run pytest tests/unit/cli/commands/exec/scripts/test_plan_create_review_pr.py`
2. **Schema tests**: Run `uv run pytest packages/erk-shared/tests/unit/github/metadata/test_plan_header.py`
3. **Manual test**:
   - Save a plan to GitHub issue
   - Run `erk exec plan-create-review-branch <issue>`
   - Run `erk exec plan-create-review-pr <issue> <branch> "<title>"`
   - Verify PR created as draft with correct title/body
   - Verify issue metadata contains `review_pr: <pr-number>`
