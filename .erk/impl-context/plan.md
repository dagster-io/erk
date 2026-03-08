# Block .erk/impl-context/ from merging to master

## Context

`.erk/impl-context/` is intentionally committed on plan branches during `plan-save`, then removed during implementation cleanup. If cleanup is missed, these files can leak into master via PR merge. Currently `.gitignore` prevents accidental local adds, and `check-submission` skips CI when impl-context exists — but nothing **blocks the merge**.

## Approach

Add a new CI job to `ci.yml` that fails if `.erk/impl-context/` exists in the checkout. This job runs independently of `check-submission` (which skips CI) — it's specifically a merge gate.

## Changes

### 1. Add `no-impl-context` job to `.github/workflows/ci.yml`

Insert a new job after `check-submission` (around line 29):

```yaml
no-impl-context:
  if: github.event.pull_request.draft != true && !contains(github.event.pull_request.labels.*.name, 'erk-plan-review')
  runs-on: ubuntu-latest
  timeout-minutes: 5
  steps:
    - uses: actions/checkout@v4
    - name: Ensure .erk/impl-context/ is not in tree
      run: |
        if [ -d ".erk/impl-context" ]; then
          echo "::error::.erk/impl-context/ must be removed before merging. Run: git rm -rf .erk/impl-context/ && git commit && git push"
          exit 1
        fi
```

Key design decisions:
- **No dependency on `check-submission`** — runs independently so it can't be skipped
- **Skips plan PRs** (`erk-plan-review` label) — plan branches intentionally contain impl-context
- **Skips draft PRs** — work-in-progress shouldn't be blocked
- **Actionable error message** — tells the developer exactly what to run

### 2. Add to branch protection (manual step)

After merging, add `no-impl-context` as a required status check in GitHub branch protection settings for master.

## Files Modified

- `.github/workflows/ci.yml` — add `no-impl-context` job

## Verification

1. Push a test branch with `.erk/impl-context/` committed → CI should fail on `no-impl-context`
2. Push a branch without it → CI should pass
3. Create a draft PR with impl-context → job should be skipped
4. Create a PR with `erk-plan-review` label → job should be skipped
