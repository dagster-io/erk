# Skip CI on Draft PRs

## Problem

CI workflows run on draft PRs, wasting compute resources. Only `test.yml` has the correct configuration to skip drafts; the other 5 CI workflows run on all PR events.

## Solution

Add explicit `pull_request` event types to the 5 workflows that are missing them, matching the pattern already used in `test.yml`.

## Implementation

### Pattern to Apply

```yaml
on:
  push:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
  workflow_dispatch:
```

This configuration:
- Runs CI on PR creation (`opened`)
- Runs CI on new commits (`synchronize`)
- Runs CI when PR is reopened (`reopened`)
- Runs CI when draft is marked ready (`ready_for_review`)
- **Does NOT run** on draft PRs or when a PR is converted to draft

### Files to Modify

1. `.github/workflows/lint.yml` - lines 3-6
2. `.github/workflows/pyright.yml` - lines 3-6
3. `.github/workflows/prettier.yml` - lines 3-6
4. `.github/workflows/check-sync.yml` - lines 3-6
5. `.github/workflows/md-check.yml` - lines 3-6

### Change for Each File

Replace:
```yaml
on:
  push:
  pull_request:
  workflow_dispatch:
```

With:
```yaml
on:
  push:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
  workflow_dispatch:
```

## Verification

After implementation, verify by:
1. Creating a draft PR - CI should NOT run
2. Marking PR ready for review - CI should run
3. Pushing commits to ready PR - CI should run