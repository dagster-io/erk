# Plan: Skip autofix on plan-review PRs (including push events)

## Problem

The autofix job in `.github/workflows/ci.yml` has a `plan-review` label check on line 135, but it only works for `pull_request` events. For `push` events, the condition `github.event_name != 'pull_request'` short-circuits to `true`, bypassing the label check entirely. This means autofix can still trigger when pushing to a branch that has a plan-review PR.

## Approach

Add a label check step after the "Discover PR" and "Get PR info" steps that queries the PR's labels via the GitHub API and skips autofix if `plan-review` is found. This handles both event types uniformly.

## File to modify

`/Users/schrockn/code/erk/.github/workflows/ci.yml`

## Changes

1. **Add a "Check plan-review label" step** after the "Get PR info" step (~line 192), before checkout:

```yaml
- name: Check plan-review label
  id: check-label
  if: steps.discover-pr.outputs.has_pr == 'true' && steps.pr.outputs.skip != 'true'
  env:
    GH_TOKEN: ${{ github.token }}
  run: |
    labels=$(gh api repos/${{ github.repository }}/pulls/${{ steps.discover-pr.outputs.pr_number }} --jq '[.labels[].name] | join(",")')
    if echo "$labels" | grep -q "plan-review"; then
      echo "PR has plan-review label, skipping autofix"
      echo "skip=true" >> $GITHUB_OUTPUT
    else
      echo "skip=false" >> $GITHUB_OUTPUT
    fi
```

2. **Add `steps.check-label.outputs.skip != 'true'` condition** to all downstream steps that currently check `steps.pr.outputs.skip != 'true'` (checkout, check-submission-folder, setup-python, install-uv, install-erk, and all subsequent steps).

3. **Optionally simplify the job-level `if`** by removing the now-redundant plan-review label check on line 135 (since the step-level check handles both event types). However, keeping it is fine as defense-in-depth — it avoids unnecessary job startup for PR events.

## Verification

- Push to a branch with a plan-review PR where a lint check fails → autofix should be skipped
- Push to a normal branch where a lint check fails → autofix should still run
- PR event on a plan-review PR → autofix already skipped by job-level condition (unchanged)