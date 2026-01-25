# Plan: Improve Remote Rebase Agent PR Comments

## Problem

The remote rebase agent leaves terse PR comments that don't provide enough context:
```
✅ Remote rebase completed successfully.

[View workflow run](URL)
```

When the agent runs but finds nothing to do (branch already up-to-date), users can't tell if:
- The agent actually ran
- Whether commits were added or not
- Whether there was an error

## Solution

Capture the JSON output from `erk exec rebase-with-conflict-resolution` and include relevant details in the PR comment.

The command already outputs detailed JSON:
```json
{
  "success": true,
  "action": "rebased",           // or "already-up-to-date"
  "commits_behind": 3
}
```

## Implementation

### File to Modify
- `.github/workflows/erk-rebase.yml`

### Changes

1. **Capture rebase command output** (lines 140-144):
   - Save JSON output to a file
   - Set output variables for use in comment step

2. **Generate contextual PR comments** (lines 146-159):
   - **If rebased**: "Rebased branch onto {base_branch}, resolving {N} commits behind"
   - **If already up-to-date**: "Branch already up-to-date with {base_branch} (0 commits behind)"
   - **If failed**: Include error type and message from JSON

### Comment Format Examples

**Rebased successfully:**
```
✅ Remote rebase completed

Rebased `feature-branch` onto `master`, resolving 3 commits behind.

[View workflow run](URL)
```

**Already up-to-date:**
```
✅ Remote rebase completed

Branch `feature-branch` is already up-to-date with `master` (no rebase needed).

[View workflow run](URL)
```

**Failed:**
```
❌ Remote rebase failed

Error: Failed to resolve conflicts after 5 attempts

[View workflow run](URL)
```

## Verification

1. Trigger a rebase on a PR that's already up-to-date and verify comment shows "already up-to-date"
2. Trigger a rebase on a PR that's behind and verify comment shows commit count
3. (If possible) Test failure case shows error details