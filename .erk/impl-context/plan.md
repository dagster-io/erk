# Use `github.token` for comment-posting steps in one-shot workflow

## Context

Erk's CI workflows use `ERK_QUEUE_GH_PAT` (schrockn's personal PAT) as `GH_TOKEN` for all GitHub API operations. This causes automated comments (like "Queued for Implementation") and PR title changes to appear as authored by schrockn rather than a bot. The fix is to use `${{ github.token }}` for steps that post comments, so they appear from `github-actions[bot]`.

The workflow already declares `permissions: { contents: write, pull-requests: write, issues: write }`, so `github.token` has sufficient scopes. Git push operations still use the PAT configured by `actions/checkout`, independent of `GH_TOKEN`.

## Changes

### `.github/workflows/one-shot.yml`

Two steps post visible comments and should switch to `github.token`:

1. **Line 220: "Register one-shot plan"** — posts "Queued for Implementation" comment via `erk exec register-one-shot-plan` → `issues.add_comment()`
   - Change `GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }}` → `GH_TOKEN: ${{ github.token }}`

2. **Line 187: "Update plan on rejection"** — posts rejection comment via `gh issue close --comment`
   - Change `GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }}` → `GH_TOKEN: ${{ github.token }}`

### Not changing

- **Line 133: "Run one-shot planning"** — Claude Code runs here with the PAT. During planning, Claude creates the plan PR and may rename the original PR title (also visible as schrockn). Switching this step's token is a larger change since Claude Code uses `GH_TOKEN` for all `gh` operations during the planning session. Could be a follow-up.
- **Steps that `git push`** — must keep PAT so pushes trigger downstream workflows.
- **Other workflows** (`plan-implement.yml`, `pr-address.yml`, etc.) — already use `github.token` for their comment-posting steps.

## Verification

- Dispatch a one-shot plan and check that the "Queued for Implementation" comment appears from `github-actions[bot]`
- Test plan rejection flow to verify rejection comment also appears from bot
