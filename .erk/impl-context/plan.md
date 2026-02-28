# Fix: Remove invalid `--pr` flag from pr-rewrite workflow

## Context

The `pr-rewrite` GitHub Actions workflow (added in commit 704bbe6ad) passes `--pr "$PR_NUMBER"` to `erk pr rewrite`, but the CLI command has never accepted a `--pr` option. It discovers the PR automatically from the current branch. This causes every rewrite workflow run to fail the rewrite step (silently, due to `|| true`).

## Change

**File:** `.github/workflows/pr-rewrite.yml` (line 107)

Replace:
```yaml
REWRITE_OUTPUT=$(erk pr rewrite --pr "$PR_NUMBER" 2>&1) || true
```

With:
```yaml
REWRITE_OUTPUT=$(erk pr rewrite 2>&1) || true
```

The workflow already checks out the target branch at line 74-79, so `erk pr rewrite` will discover the PR from the checked-out branch automatically.

## Verification

- Confirm `erk pr rewrite --help` shows no `--pr` option
- Trigger a rewrite workflow run and verify the rewrite step succeeds
