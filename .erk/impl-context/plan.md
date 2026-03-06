# Fix CI race condition: fix-formatting push vs tier 3 jobs

## Context

When `fix-formatting` pushes an autofix commit, `cancel-in-progress: true` is supposed to cancel the current run (since the push triggers a new one). In practice, there's a race: tier 3 jobs (lint, format, ty, etc.) start before GitHub Actions processes the cancellation, so they run against the old (unformatted) code and fail. The new run then passes, but the failed checks create noise and delay.

Evidence from run 22752638097: fix-formatting finished at 06:53:41, lint started at 06:53:44 and failed at 06:53:55 — lint ran against the pre-fix commit before cancellation arrived.

## Approach

Add an output to `fix-formatting` indicating whether it pushed changes. All tier 3 jobs skip when `pushed == 'true'` since a new CI run is incoming with the fixed code.

## Files to modify

- `.github/workflows/ci.yml` — add output + skip conditions
- `docs/learned/ci/job-ordering-strategy.md` — update documentation

## Steps

### 1. Add `pushed` output to fix-formatting job

```yaml
fix-formatting:
  needs: check-submission
  # ... existing if
  runs-on: ubuntu-latest
  timeout-minutes: 15
  outputs:
    pushed: ${{ steps.commit.outputs.pushed }}
  steps:
    # ... existing steps ...
    - name: Commit and push if changes
      id: commit          # <-- add id
      run: |
        if git diff --quiet; then
          echo "No formatting changes needed"
          echo "pushed=false" >> $GITHUB_OUTPUT    # <-- add
          exit 0
        fi
        # ... existing push logic ...
        echo "pushed=true" >> $GITHUB_OUTPUT       # <-- add at end
```

### 2. Add skip condition to all tier 3 jobs

Add `&& needs.fix-formatting.outputs.pushed != 'true'` to the `if:` condition of every tier 3 job:

- `format`
- `lint`
- `docs-check`
- `ty`
- `unit-tests`
- `integration-tests`
- `erk-mcp-tests`
- `discover-reviews`

### 3. Update documentation

Update `docs/learned/ci/job-ordering-strategy.md` to document the skip-on-push mechanism replacing the old "cancellation handles it" claim.

## Verification

1. Read the modified workflow and confirm all tier 3 jobs have the skip condition
2. Verify the output is correctly wired (`steps.commit.outputs.pushed` → job output `pushed`)
3. Push to the PR branch and confirm CI runs correctly (if no formatting changes needed, all jobs run normally)
