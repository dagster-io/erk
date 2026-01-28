# Plan: Create `erk exec plan-submit-for-review` Command

**Objective**: #6201 (Plan Review via Temporary PR)
**Roadmap Step**: 1.1 - Create `erk exec plan-submit-for-review` command that fetches plan content from issue

## Overview

Create a new `erk exec` command that fetches a plan issue from GitHub, validates it has the `erk-plan` label, and extracts the plan content from the first comment. This is the foundation for the PR-based plan review workflow.

## Input/Output Specification

**Input:**
- `issue_number` (required, int): The GitHub issue number to fetch

**Output (JSON):**

Success:
```json
{
  "success": true,
  "issue_number": 1234,
  "title": "Plan: Add feature X",
  "url": "https://github.com/owner/repo/issues/1234",
  "plan_content": "## Plan\n\n...",
  "plan_comment_id": 5678,
  "plan_comment_url": "https://github.com/owner/repo/issues/1234#issuecomment-5678"
}
```

Error cases: `issue_not_found`, `missing_erk_plan_label`, `no_plan_content`

## Files to Create/Modify

### 1. Create Command: `src/erk/cli/commands/exec/scripts/plan_submit_for_review.py`

Following the established pattern from `get_plan_metadata.py`:

- Use `@click.pass_context` with `require_github_issues(ctx)` and `require_repo_root(ctx)`
- Frozen dataclasses for success/error responses
- JSON output via `json.dumps(asdict(result))`
- Exit code 1 for errors with JSON on stderr

**Implementation flow:**
1. Fetch issue using `github.get_issue(repo_root, issue_number)`
2. Validate `"erk-plan"` in `issue.labels`
3. Extract `plan_comment_id` from metadata using `extract_plan_header_comment_id(issue.body)`
4. Fetch comments using `github.get_issue_comments_with_urls(repo_root, issue_number)`
5. Extract plan content using `extract_plan_from_comment(first_comment.body)`
6. Return success JSON with all plan data

### 2. Register Command: `src/erk/cli/commands/exec/group.py`

Add import and registration (alphabetical order near other plan_ commands).

### 3. Create Tests: `tests/unit/cli/commands/exec/scripts/test_plan_submit_for_review.py`

**Test cases:**
- Success: Valid plan issue with content
- Success: Extracts plan from Schema v2 (plan-body block) format
- Success: Backward compat with old format (erk:plan-content markers)
- Error: Issue not found
- Error: Missing erk-plan label
- Error: No comments on issue
- Error: Comments exist but no plan markers

## Key Dependencies (already exist)

- `extract_plan_from_comment()` - handles both new and old format
- `extract_plan_header_comment_id()` - gets comment ID from metadata
- `FakeGitHubIssues` - for testing with `ErkContext.for_test()`
- `IssueComment` type - includes `id`, `body`, `url` fields

## Error Handling

| Scenario | Error Code | Exit Code |
|----------|------------|-----------|
| Issue not found | `issue_not_found` | 1 |
| Missing erk-plan label | `missing_erk_plan_label` | 1 |
| No comments | `no_plan_content` | 1 |
| No plan markers in comments | `no_plan_content` | 1 |

## Verification

1. Run unit tests: `pytest tests/unit/cli/commands/exec/scripts/test_plan_submit_for_review.py`
2. Run type checker: `ty check src/erk/cli/commands/exec/scripts/plan_submit_for_review.py`
3. Manual test: `erk exec plan-submit-for-review <existing-plan-issue-number>`

## Related Documentation

- Skills: `dignified-python`, `fake-driven-testing`
- Reference patterns: `get_plan_metadata.py`, `test_get_plan_metadata.py`