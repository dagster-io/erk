# Plan: Fix Autofix Race Condition When Reporting Commit Status

## Problem

After autofix pushes a new commit, it immediately tries to report commit status via `gh api repos/.../statuses/$current_sha`. GitHub's API sometimes returns HTTP 422 "No commit found for SHA" because the commit hasn't been fully indexed yet.

## Solution

Add a retry mechanism to the `report_status` function with exponential backoff. If the API returns 422, wait and retry.

## Changes

### `.github/workflows/ci.yml`

Modify the `report_status` function (around line 357-365) to add retry logic:

**Current:**
```bash
report_status() {
  local name="$1"
  local state="$2"
  local desc="$3"
  gh api repos/${{ github.repository }}/statuses/$current_sha \
    -f state="$state" \
    -f context="ci / $name (autofix-verified)" \
    -f description="$desc"
}
```

**New:**
```bash
report_status() {
  local name="$1"
  local state="$2"
  local desc="$3"
  local max_retries=5
  local retry_delay=2

  for i in $(seq 1 $max_retries); do
    if gh api repos/${{ github.repository }}/statuses/$current_sha \
      -f state="$state" \
      -f context="ci / $name (autofix-verified)" \
      -f description="$desc" 2>/dev/null; then
      return 0
    fi

    if [ $i -lt $max_retries ]; then
      echo "Status report failed (attempt $i/$max_retries), retrying in ${retry_delay}s..."
      sleep $retry_delay
      retry_delay=$((retry_delay * 2))
    fi
  done

  echo "Warning: Failed to report status for $name after $max_retries attempts"
  return 0  # Don't fail the workflow for status reporting issues
}
```

## Verification

1. The change is in workflow YAML - test by pushing a commit that triggers autofix
2. Verify the retry logic works by checking workflow logs