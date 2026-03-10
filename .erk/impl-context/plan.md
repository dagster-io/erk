# Push Down: Review Activity Log Fetch

## Context

The review prompt template (`src/erk/review/prompt_assembly.py`) tells the Claude agent to run a raw `gh pr view --jq` command to fetch existing review comments by marker. In CI run 22893143652, Claude (sonnet) over-escaped the `!` in the HTML comment marker `<!-- audit-pr-docs -->` as `\!`, producing an invalid jq escape sequence and failing the review job.

This is a textbook push-down candidate: a mechanical shell pipeline with escaping hazards that can be replaced by a tested CLI command.

## Approach

Create a new `erk exec get-review-activity-log` command that fetches the existing review comment body and extracts the Activity Log section. Replace the fragile Step 2 in the prompt template with a single CLI invocation.

## Changes

### 1. Add `get_pr_comment_body_by_marker` to GitHub gateway (4-place pattern)

The existing `find_pr_comment_by_marker` returns only the comment ID. We need a sibling that returns the **body**.

**Files:**
- `packages/erk-shared/src/erk_shared/gateway/github/abc.py` - Add abstract method
- `packages/erk-shared/src/erk_shared/gateway/github/real.py` - Implement (reuse existing comment-fetching logic from `find_pr_comment_by_marker`, return body instead of ID)
- `packages/erk-shared/src/erk_shared/gateway/github/dry_run.py` - Delegate to wrapped
- `tests/fakes/gateway/github.py` - Implement in fake

**Signature:**
```python
def get_pr_comment_body_by_marker(
    self, repo_root: Path, pr_number: int, marker: str
) -> str | None:
    """Return body of first PR comment containing marker, or None."""
```

### 2. Create `erk exec get-review-activity-log` command

**File:** `src/erk/cli/commands/exec/scripts/get_review_activity_log.py`

Takes `--pr-number` and `--marker`. Returns JSON:
```json
{"success": true, "found": true, "activity_log": "- [2024-01-01] Found 2 violations\n- ..."}
```
or
```json
{"success": true, "found": false, "activity_log": ""}
```

Logic:
1. Call `github.get_pr_comment_body_by_marker(repo_root, pr_number, marker)`
2. If found, extract everything after `### Activity Log`
3. Return structured JSON

### 3. Register command in exec group

**File:** `src/erk/cli/commands/exec/group.py` - Add import and `add_command`

### 4. Update prompt template

**File:** `src/erk/review/prompt_assembly.py`

Replace Step 2 (lines 26-36):

**Before:**
```
## Step 2: Get Existing Review Comment

Fetch the existing review comment to preserve the activity log:

\```
gh pr view {pr_number} --json comments \
  --jq '.comments[] | select(.body | contains("{marker}")) | .body'
\```

If a comment exists, extract the Activity Log section (everything after
`### Activity Log`). You will append to this log.
```

**After:**
```
## Step 2: Get Existing Activity Log

Fetch the existing activity log to preserve prior entries:

\```
erk exec get-review-activity-log --pr-number {pr_number} --marker "{marker}"
\```

This returns JSON with `activity_log` (the text after `### Activity Log` from
any existing summary comment). If `found` is false, start a fresh log.
```

### 5. Update prompt assembly tests

**File:** `tests/unit/review/test_prompt_assembly.py` - Update assertions that check for the old `gh pr view --jq` text

### 6. Tests for new command

**File:** `tests/unit/cli/commands/exec/scripts/test_get_review_activity_log.py`

Cases:
- No existing comment (found=false)
- Existing comment with activity log section
- Existing comment without activity log section (found=true, empty log)
- Gateway error handling

### 7. Tests for new gateway method

**File:** `tests/unit/fakes/test_fake_github.py` - Add tests for `get_pr_comment_body_by_marker`

## Verification

1. Run unit tests for the new command: `pytest tests/unit/cli/commands/exec/scripts/test_get_review_activity_log.py`
2. Run prompt assembly tests: `pytest tests/unit/review/test_prompt_assembly.py`
3. Run fake tests: `pytest tests/unit/fakes/test_fake_github.py`
4. Run `erk exec run-review --name audit-pr-docs --pr-number <PR> --dry-run` and verify Step 2 shows the new CLI command instead of the raw jq pipeline
5. Run ty and ruff checks
