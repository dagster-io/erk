---
description: Debug failing CI checks on current branch's PR
---

# Debug CI

Fetch and analyze failing CI logs for the current branch's PR.

## Usage

```bash
/debug-ci
```

## Implementation

### Step 1: Get Current Branch

```bash
git branch --show-current
```

### Step 2: Check PR Status

Get PR checks and identify failures:

```bash
gh pr view --json statusCheckRollup --jq '.statusCheckRollup[] | select(.conclusion == "FAILURE") | "\(.name): \(.conclusion)"'
```

If no failures found, report "All CI checks are passing" and stop.

### Step 3: Get Failed Run IDs

Find the most recent failed workflow runs for this branch:

```bash
gh run list --branch <branch> --json conclusion,name,databaseId,status --jq '.[] | select(.conclusion == "failure") | "\(.databaseId) \(.name)"' | head -5
```

### Step 4: Fetch Failed Logs

For each failed run, fetch the logs:

```bash
gh run view <run_id> --log-failed | head -100
```

### Step 5: Analyze and Report

Present the failure information clearly:

```markdown
## CI Failure Analysis

**Branch**: <branch>
**PR**: #<number>

### Failed Checks

1. **<check_name>**
   - Run ID: <id>
   - Error: <error_summary>

### Failure Logs

<relevant log output>

### Suggested Fix

<based on the error, suggest what to do>
```

## Common Failures and Fixes

### docs-check / docs-sync-check

**Error**: "Files out of sync: N change(s) needed"
**Fix**: Run `uv run dot-agent docs sync` then commit

### lint

**Error**: Ruff linting errors
**Fix**: Run `make fix` then commit

### format-check

**Error**: Files need reformatting
**Fix**: Run `make format` then commit

### prettier-check

**Error**: Markdown files need formatting
**Fix**: Run `make prettier` then commit

### pyright

**Error**: Type checking failures
**Fix**: Read the file and fix type annotations

### unit-tests / integration-tests

**Error**: Test failures
**Fix**: Analyze test output and fix code or tests

## Notes

- This command only fetches and analyzes logs - it does NOT automatically fix issues
- Use `/fast-ci` or `/all-ci` to run CI locally and fix issues iteratively
- After fixing, use `/quick-submit` or `/gt:pr-submit` to push changes
