# Plan: Add Secret Validation to erk-impl.yml

## Problem

When `ERK_QUEUE_GH_PAT` secret is missing or expired, the workflow fails with the cryptic error:
```
Error: Input required and not supplied: token
```

This provides no context about which secret is missing or how to fix it.

## Solution

Add a validation step before `actions/checkout@v4` that checks if the secret exists and fails with a clear, actionable error message.

## Changes

### File: `/Users/schrockn/code/dagster-compass/.github/workflows/erk-impl.yml`

Insert new step at line 54 (before the existing checkout step):

```yaml
      - name: Validate required secrets
        env:
          ERK_PAT: ${{ secrets.ERK_QUEUE_GH_PAT }}
        run: |
          if [ -z "$ERK_PAT" ]; then
            echo "::error title=Missing Secret::ERK_QUEUE_GH_PAT secret is not configured or has expired. Add a PAT with 'repo' scope at: Settings → Secrets and variables → Actions"
            exit 1
          fi
```

## Verification

1. Trigger the workflow manually with the secret temporarily removed/renamed
2. Verify the error message is clear and actionable
3. Restore the secret and verify the workflow runs normally