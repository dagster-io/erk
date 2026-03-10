# Fix missing GH_TOKEN in consolidate-learn-plans ci-address job

## Context

The `ci-address` job in `.github/workflows/consolidate-learn-plans.yml` fails at the "Checkout PR branch" step because `gh pr checkout` requires `GH_TOKEN` for authentication, but the step doesn't set it. The subsequent steps in the same job already have `GH_TOKEN` set correctly — this is just an oversight on line 218-225.

## Change

**File:** `.github/workflows/consolidate-learn-plans.yml` (line 219)

Add `GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }}` to the env block of the "Checkout PR branch" step, matching the pattern used in `pr-address.yml` and the other steps in this same job.

## Verification

Grep the workflow for any other `gh ` commands missing `GH_TOKEN` in their step env — none found, this is the only one.
