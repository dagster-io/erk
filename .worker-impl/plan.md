# Skip CI for Draft PRs

## Summary
Add draft PR detection to all CI workflows so jobs don't run when a PR is in draft mode.

## Workflows to Modify (7 files)

All files are in `.github/workflows/`:

1. **test.yml** - unit-tests, integration-tests
2. **pyright.yml** - type checking
3. **lint.yml** - ruff linting
4. **prettier.yml** - markdown formatting
5. **md-check.yml** - AGENTS.md compliance
6. **check-sync.yml** - kit artifact sync
7. **claude-code-review.yml** - automated PR review

## Implementation

Add the draft check to each job's `if` condition. Since jobs already have conditions checking `check-submission.outputs.skip`, we combine both:

```yaml
if: github.event.pull_request.draft != true && needs.check-submission.outputs.skip == 'false'
```

For push events (not PR), `github.event.pull_request.draft` is `null`, so `!= true` evaluates to `true` (allowing push builds to run).

### Note on check-submission job
The `check-submission` job itself should also skip on drafts to avoid unnecessary checkout/compute:

```yaml
check-submission:
  if: github.event.pull_request.draft != true
  runs-on: ubuntu-latest
```

## Workflows NOT Modified

- **claude.yml** - Comment-triggered, not affected by draft state
- **dispatch-erk-queue-git.yml** - Manual dispatch only, manages draft state itself

## CodeQL

CodeQL is **not configured via workflow files** in this repo. If you're seeing CodeQL runs, it's enabled at the repository level:
- Settings → Code security → Code scanning → CodeQL analysis
- You can disable it there, or add a `.github/workflows/codeql.yml` with draft exclusion

## Files to Edit

1. `.github/workflows/test.yml`
2. `.github/workflows/pyright.yml`
3. `.github/workflows/lint.yml`
4. `.github/workflows/prettier.yml`
5. `.github/workflows/md-check.yml`
6. `.github/workflows/check-sync.yml`
7. `.github/workflows/claude-code-review.yml`