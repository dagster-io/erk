# Plan: Update CHANGELOG.md Unreleased section

## Context

57 new commits have landed on master since the last CHANGELOG sync (`f24b02de7`). This plan captures the approved changelog entries to add.

## Changes to CHANGELOG.md

### 1. Update as-of marker

```
- <!-- as-of: f24b02de7 -->
+ <!-- as-of: 3a4c03bed -->
```

### 2. Append to Major Changes

- Stack-in-place branch creation and `prepare` command removal: `erk br create` in assigned worktree slots now updates the assignment tip in place, enabling stacked branches to share a single worktree. `erk prepare` removed; use `erk br create --for-plan` instead (fe03e628a)

### 3. Append to Added

- Add `erk wt create-from` command for allocating worktree slots to existing branches with automatic remote branch fetching and `--force` flag (4ccff29e2)
- Add branch column to TUI dashboard between "title" and "created" (7b4d8e190)
- Add remote divergence pre-check before `gt submit` with actionable error messages (4a9b06e24)

### 4. Append to Changed

- Migrate session and learn material storage from GitHub Gists to git branches (3a4c03bed, c7f936340, 12f964cb5)
- Rename "instruction" to "prompt" throughout `erk one-shot` feature (279873ac5)
- Replace "issue" with "plan" in implement command output for backend-agnostic messaging (d17948889)
- Infer "implementing" lifecycle stage when plan has active workflow run (bb5e3ca6f)
- Auto-force push for plan implementation branches in `erk pr submit` (3c0ee7fcf)
- Restore PR status indicators (merge conflicts, review decisions) in dashboard (03e09b0a7)
- Fix shell activation in draft PR next steps to use `source "$(erk br co ...)"` pattern (a78bb01ba)
- Use branch name instead of PR number in draft PR checkout next steps (433beb649)
- Publish draft PRs during `erk pr submit` with mutation-safe tracking (5a545a9f4)

### 5. Append to Fixed

- Fix draft PR plan list label duplication causing `erk plan list` to return "No plans found" (fe5d2a6d8)
- Fix `erk one-shot` dispatch metadata writing for draft_pr backend (8622d1854)
- Fix learn pipeline for draft-PR plans with direct PR lookup and metadata fallback (fb8280e2b)
- Fix non-fast-forward push in draft-PR plan submission by adding rebase sync (d683f3b0b)
- Fix `submit` command crashing when `.worker-impl/` already exists (670c3bbb9)
- Fix `extract_metadata_prefix` falsely matching footer separator in PR bodies (fa37bb0b8)
- Fix `.erk/impl-context/` cleanup by deferring git removal to plan-implement (d16b20077)
- Implement lazy tip sync for worktree pool to fix stale assignment state (a5683ff04)

### 6. Add new Removed section (after Fixed)

- Remove `erk prepare` command — use `erk br create --for-plan` instead (fe03e628a)

## File

- `CHANGELOG.md` — single file edit

## Verification

- Read the updated Unreleased section to confirm entry order and formatting
- Confirm as-of marker updated to `3a4c03bed`
