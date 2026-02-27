# Plan: Auto-fix markdown (docs-sync + Prettier) in CI

## Context

Remote AI implementations (via `plan-implement.yml`) frequently produce markdown files that aren't prettier-formatted, or modify code that puts docs out of sync. This causes the `prettier --check` or `docs-check` jobs in CI to fail, requiring manual intervention or re-runs. Recent examples: runs on `plnd/resilient-plan-header-reco` and `plnd/plans-as-draft-prs` both failed solely on the `prettier` job (e.g., `.claude/commands/erk/plan-implement.md` was the offending file).

The fix: replace the check-and-fail pattern with a fix-and-commit pattern for PRs. Run `erk docs sync` first (which may generate/update markdown), then `prettier --write` (which formats all markdown), then auto-commit if anything changed.

## Changes

### 1. Replace the `prettier` job with `markdown-fix` in `.github/workflows/ci.yml`

Replace the current check-only prettier job with a comprehensive markdown fix job that runs docs-sync then prettier, and auto-commits on PRs:

```yaml
markdown-fix:
  needs: check-submission
  if: github.event.pull_request.draft != true && needs.check-submission.outputs.skip == 'false'
  runs-on: ubuntu-latest
  timeout-minutes: 15
  steps:
    - uses: actions/checkout@v4
      with:
        # Checkout PR branch (not detached HEAD) so we can push fixes
        ref: ${{ github.head_ref || github.ref }}
    - uses: ./.github/actions/setup-python-uv
    - uses: ./.github/actions/setup-prettier
    - name: Sync documentation
      run: make docs-fix
    - name: Fix markdown formatting
      run: prettier --write '**/*.md' --ignore-path .gitignore
    - name: Commit and push if changes
      run: |
        if git diff --quiet; then
          echo "No formatting changes needed"
          exit 0
        fi

        # On push to master: fail instead of auto-committing
        if [ "${{ github.event_name }}" = "push" ]; then
          echo "::error::Markdown files need formatting or docs are out of sync"
          git diff --stat
          exit 1
        fi

        # On fork PRs: fail instead of auto-committing (can't push to fork)
        HEAD_REPO="${{ github.event.pull_request.head.repo.full_name }}"
        BASE_REPO="${{ github.event.pull_request.base.repo.full_name }}"
        if [ "$HEAD_REPO" != "$BASE_REPO" ]; then
          echo "::error::Markdown issues found (cannot auto-fix fork PRs)"
          exit 1
        fi

        # Auto-fix: commit and push
        git config user.name "github-actions[bot]"
        git config user.email "github-actions[bot]@users.noreply.github.com"
        git add '*.md'
        git commit -m "Auto-fix markdown formatting (docs-sync + Prettier)"
        git push
        echo "::notice::Auto-fixed markdown and pushed"
```

### 2. Update `autofix` job's `needs` list

Change `prettier` to `markdown-fix` in the autofix job's `needs` array (line ~161) and in the condition checks (line ~173).

### 3. Remove standalone `docs-check` job

Since `markdown-fix` now runs `docs-fix` (which is the fix for what `docs-check` validates), and `docs-check` runs `make md-check` + `make docs-check`, we have two options:

**Keep `docs-check` as-is.** It still serves as a validation that docs are correct. If `markdown-fix` fixed the issues, the concurrent `docs-check` may fail on this run, but the auto-committed push triggers a new run where it passes. No change needed.

### 4. No other file changes

The Makefile targets remain unchanged. The `plan-implement.yml` workflow is unaffected.

## Files to modify

- `.github/workflows/ci.yml` — replace `prettier` job, update autofix `needs`

## Design decisions

- **Job renamed to `markdown-fix`**: reflects broader scope (docs-sync + prettier)
- **Push to master**: keeps check-only behavior (fail, don't commit to master)
- **Fork PRs**: falls back to check-only (can't push to forks)
- **Same-repo PRs**: auto-fix and commit
- **Concurrency handling**: the push triggers a new CI run; `cancel-in-progress: true` cancels the current run, and the new run passes cleanly
- **docs-check kept**: still validates documentation correctness as a parallel check

## Verification

1. Create a branch with an intentionally unformatted `.md` file
2. Push and observe CI: the `markdown-fix` job should auto-fix and push a commit
3. The second CI run should pass with no changes needed
4. Verify push-to-master still fails on formatting issues (check-only behavior)
