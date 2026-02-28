# Plan: Fix CI check gap after markdown-fix auto-commits

## Context

PR #8464 has zero checks on its HEAD commit because the `markdown-fix` job auto-committed a formatting fix using `GITHUB_TOKEN`. GitHub Actions does not trigger new workflow runs from pushes made with `GITHUB_TOKEN` (to prevent infinite loops). This creates a "check gap" — the new HEAD has no associated checks, so the PR appears to have no CI results.

Additionally, the `ci-summarize` job (added in #8395) references a non-existent `prettier` job in its `needs` array, which silently prevents it from ever running.

## Changes

### 1. Use PAT in `markdown-fix` checkout to enable CI re-triggering

**File:** `.github/workflows/ci.yml` (lines 61-64)

Change the `markdown-fix` checkout step to use `ERK_QUEUE_GH_PAT`:

```yaml
# Before
- uses: actions/checkout@v4
  with:
    ref: ${{ github.head_ref || github.ref }}

# After
- uses: actions/checkout@v4
  with:
    ref: ${{ github.head_ref || github.ref }}
    token: ${{ secrets.ERK_QUEUE_GH_PAT }}
```

When `actions/checkout@v4` uses a PAT, `git push` uses PAT credentials. GitHub will then trigger a new `pull_request: synchronize` event, which re-queues `ci.yml` on the new HEAD.

**Loop safety:** On the re-triggered run, `prettier --write` and `make docs-fix` produce no changes (already fixed), so `git diff --quiet` exits 0 and no commit is made. The loop terminates after exactly one re-trigger.

**Concurrency behavior:** The `cancel-in-progress: true` concurrency setting will cancel the first CI run when the second triggers. This is correct — the first run was checking pre-fix code, and the second run checks the actual HEAD.

**Precedent:** This follows the established pattern used by `plan-implement.yml`, `pr-address.yml`, `pr-fix-conflicts.yml`, and other workflows that push commits and need CI re-triggering.

### 2. Fix stale `prettier` reference in `ci-summarize` job

**File:** `.github/workflows/ci.yml` (lines 449-465)

The `ci-summarize` job's `needs` array references a non-existent `prettier` job. This prevents `ci-summarize` from ever running, making the CI failure summarization feature (#8395) completely broken.

```yaml
# Before
ci-summarize:
  needs:
    [format, lint, prettier, docs-check, ty, unit-tests, integration-tests, erkdesk-tests, erkbot-tests]
  if: |
    ...
    needs.prettier.result == 'failure' ||
    ...

# After
ci-summarize:
  needs:
    [format, lint, markdown-fix, docs-check, ty, unit-tests, integration-tests, erkdesk-tests, erkbot-tests]
  if: |
    ...
    needs.markdown-fix.result == 'failure' ||
    ...
```

Replace `prettier` with `markdown-fix` in both the `needs` array and the `if` condition.

## Verification

1. Push a branch with a markdown formatting issue and confirm:
   - `markdown-fix` auto-commits the fix
   - A new CI run triggers on the auto-committed HEAD
   - All checks appear on the PR's latest commit
2. Push a branch with a deliberate CI failure (e.g., ruff format issue) and confirm `ci-summarize` runs and posts summaries
