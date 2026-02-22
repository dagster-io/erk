# Plan: Add `.worker-impl/` cleanup to `pr-address` workflow

## Context

`.worker-impl/` folders are leaking into PRs when the `pr-address` workflow runs. The `plan-implement` workflow has two cleanup phases (pre- and post-implementation), but `pr-address` has **no cleanup logic at all**. When `.worker-impl/` or `.erk/impl-context/` exist on a branch — from re-submissions, failed cleanups, or any other source — `pr-address` propagates them, causing Prettier CI failures and PR noise.

## Fix

### File: `.github/workflows/pr-address.yml`

Insert a cleanup step between "Address PR review comments" (line 57-70) and "Push changes" (line 72-81). This way the cleanup commit gets pushed by the existing push step — no duplicate push needed.

```yaml
    - name: Clean up plan staging dirs if present
      run: |
        NEEDS_CLEANUP=false
        if [ -d .worker-impl/ ]; then
          git rm -rf .worker-impl/
          NEEDS_CLEANUP=true
        fi
        if [ -d .erk/impl-context/ ]; then
          git rm -rf .erk/impl-context/
          NEEDS_CLEANUP=true
        fi
        if [ "$NEEDS_CLEANUP" = true ]; then
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git commit -m "Remove plan staging dirs"
          echo "Cleaned up plan staging dirs"
        fi
```

**Why this placement:** The existing "Push changes" step (line 72) checks `git log --oneline @{upstream}..HEAD` and pushes all unpushed commits. By inserting cleanup before push, the cleanup commit is included automatically.

**Pattern match:** Uses the same `[ -d ] → git rm -rf → commit` pattern as `plan-implement.yml` (lines 207-227). Simpler than the post-implementation cleanup because there's no `git reset --hard` concern — pr-address doesn't reset.

**Git config:** Explicitly sets committer identity for the cleanup commit. Claude Code sets its own config for its commits, but the cleanup step runs outside Claude.

### File: `docs/learned/planning/worktree-cleanup.md`

Add a note that `pr-address` now also has cleanup logic. Insert after the existing "See the 'Clean up .worker-impl/' step in plan-implement.yml" paragraph (line 77):

> The `pr-address.yml` workflow also includes a cleanup step, removing `.worker-impl/` and `.erk/impl-context/` before pushing. This covers the case where these folders exist on a branch from prior workflows or re-submissions.

## Verification

1. Read the modified workflow to confirm step ordering: Address → Cleanup → Push → Summary
2. Confirm the `[ -d ]` guard prevents errors when directories don't exist
3. Run `/local:fast-ci` to ensure no test impacts
