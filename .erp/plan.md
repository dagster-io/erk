# Add Workflow URL Output to `erk plan retry`

## Goal

Make `erk plan retry` output the GitHub Actions workflow URL immediately after requeuing, matching the behavior in `erk submit`.

## Context & Understanding

### API Behavior - GitHub Workflow Triggering
- Recent commit f2fbff91 fixed `trigger_workflow()` to use a two-step process
- `gh workflow run` does NOT support `--json` flag (was causing failures)
- Current implementation: (1) trigger workflow, (2) query for run ID with `gh run list --workflow X --json databaseId --limit 1`
- The `trigger_workflow()` method in `src/erk/core/github/real.py` already implements this correctly

### Architectural Pattern - Dual Trigger Strategy
- **`erk submit`**: API-only trigger with fail-fast behavior
- **`erk plan retry`**: Should use BOTH label manipulation (webhook) AND API trigger
- Why both? Label manipulation is already happening (lines 126-133), providing webhook fallback
- API trigger adds immediate user feedback via workflow URL

### Error Handling Philosophy
- **`erk submit`**: Fails fast if API trigger fails (user must know immediately)
- **`erk plan retry`**: DO NOT fail-fast if API trigger fails
- Rationale: Retry has already manipulated labels, so webhook trigger is guaranteed
- Show warning if API fails, but don't abort (workflow will still run via webhook)

### Code Location References
- Implementation file: `src/erk/cli/commands/plan/retry_cmd.py`
- URL construction logic: `src/erk/cli/commands/submit.py` lines 111-120
- Workflow trigger method: `src/erk/core/github/real.py` lines 458-523
- Insert point: After line 133 (after label manipulation), before line 135 (metadata comment)

## Current State

**What `erk plan retry` does now:**
1. Validates issue has `erk-queue` label and is OPEN
2. Parses comments to find retry count
3. Removes and re-adds `erk-queue` label (triggers workflow via webhook)
4. Posts metadata comment with retry info
5. Shows success message with issue URL only

**What `erk submit` does:**
1. Adds `erk-queue` label to issue
2. Triggers workflow via API (`ctx.github.trigger_workflow()`)
3. Gets run ID back from API
4. Constructs workflow URL from run ID
5. Displays workflow URL to user
6. Fails fast if API trigger fails

**Gap:** Retry doesn't call API or show workflow URL, making it harder to monitor execution.

## Implementation Steps

### 1. Add workflow API trigger after label manipulation

**Location:** After line 133 in `src/erk/cli/commands/plan/retry_cmd.py`

**What to do:**
- Get trunk branch from `ctx.trunk_branch` (check for None)
- Call `ctx.github.trigger_workflow()` with:
  - `repo_root=repo_root` (already in scope)
  - `workflow="dispatch-erk-queue.yml"`
  - `inputs={"issue_number": str(issue_number)}`
  - `ref=trunk_branch`
- Store returned `run_id` string

**Reference:** See `submit.py` lines 94-109 for pattern

### 2. Extract owner/repo from issue URL

**What to do:**
- Parse `issue.url` (format: `https://github.com/owner/repo/issues/123`)
- Split by `/` and extract owner (index 3) and repo_name (index 4)
- Validate URL has expected structure (check length >= 5 and domain is github.com)
- Fallback: If parsing fails, use `(Run ID: {run_id})` format

**Reference:** Exact logic in `submit.py` lines 111-120

### 3. Construct and display workflow URL

**What to do:**
- Format URL: `https://github.com/{owner}/{repo}/actions/runs/{run_id}`
- Display after existing success messages (after line 163)
- Use click.style with `fg='cyan'` for URL
- Message format:
  ```
  Workflow started:
    {cyan_workflow_url}
  ```

**Reference:** See `submit.py` lines 122-125 for output format

### 4. Error handling

**What to do:**
- Wrap entire workflow trigger block (steps 1-3) in try/except
- Catch any Exception during workflow triggering
- If exception occurs:
  - Show warning message: "Note: Could not trigger workflow via API"
  - Show error details
  - Note that webhook fallback will still trigger the workflow
  - **DO NOT** call `raise SystemExit(1)` or abort execution
- Continue to post metadata comment regardless

**Why different from submit:**
- Submit fails fast because it's the only trigger attempt
- Retry keeps running because label manipulation already succeeded (webhook will fire)

**Reference:** See `submit.py` lines 126-139 for error message format (but DO NOT fail-fast)

## Key Design Decisions

1. **Dual trigger approach**: Keep label manipulation AND add API trigger
   - Provides redundancy if API fails
   - Maintains backward compatibility with webhook-based triggering
   - Gives immediate user feedback when API works

2. **Non-fail-fast error handling**: Show warnings but continue execution
   - Differs from `erk submit` which fails fast
   - Rationale: Label manipulation already succeeded, webhook is guaranteed

3. **URL as supplementary info**: Workflow URL is "nice to have" not critical path
   - Primary success indicator is still the retry count and issue URL
   - Workflow URL is additional convenience for monitoring

## Files to Modify

- `src/erk/cli/commands/plan/retry_cmd.py` (insert after line 133, update output around line 163)

## Success Criteria

- `erk plan retry 123` shows workflow URL after success message
- URL format matches submit: `https://github.com/owner/repo/actions/runs/{run_id}`
- URL is clickable and cyan-colored
- If API trigger fails, shows warning but continues (doesn't abort)
- Label manipulation still works as before (webhook fallback preserved)
- Metadata comment still posted correctly

## Testing Notes

- Test with valid issue that has `erk-queue` label
- Test error case by temporarily breaking GitHub API access
- Verify workflow URL is correct and navigates to actual run
- Confirm webhook still triggers even if API trigger added
