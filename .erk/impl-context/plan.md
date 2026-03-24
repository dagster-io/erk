# Fix: Blank line breaks ci-update-pr-body invocation in plan-implement workflow

## Context

PR #9403 lost its run-id association in `erk dash` because the `plan-header` metadata block (containing `last_dispatched_node_id`) was stripped from the PR body during the workflow's "Update PR body" step.

**Root cause:** A blank line at `.github/workflows/plan-implement.yml:462` breaks bash line continuation, causing `ci-update-pr-body` to run without `--planned-pr`, `--run-id`, and `--run-url` flags. Without `--planned-pr`, the script replaces the entire PR body without preserving the metadata block.

**Introduced in:** Commit `e842dcf3e` (PR #9282), which accidentally added a blank line during a rename.

## Changes

### 1. Remove blank line in workflow (`.github/workflows/plan-implement.yml:462`)

```yaml
# Before (broken):
          erk exec ci-update-pr-body \
            --pr-number "${{ inputs.pr_number }}" \

            --run-id "${{ github.run_id }}" \

# After (fixed):
          erk exec ci-update-pr-body \
            --pr-number "${{ inputs.pr_number }}" \
            --run-id "${{ github.run_id }}" \
```

### 2. Manually re-associate PR #9403 with its run

After fix is merged, re-write the dispatch metadata for #9403:

```bash
erk exec update-pr-header 9403 \
  "last_dispatched_run_id=23512098333" \
  "last_dispatched_node_id=WFR_kwLOPxC3hc8AAAAFeW4mHQ" \
  "last_dispatched_at=2026-03-24T21:03:01+00:00"
```

## Verification

1. Check the PR body for #9403 has the plan-header metadata block after manual fix
2. `erk dash` shows run-id `23512098333` for PR #9403
3. Future dispatches preserve metadata through implementation completion
