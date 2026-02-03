# Plan: Allow pr-feedback-classifier to target any PR

## Problem

The `/pr-feedback-classifier` skill and its consumers (`/erk:pr-address`, `/erk:pr-preview-address`) only work with the current branch's PR. Users cannot target a specific PR by number, even though the underlying exec commands already support `--pr <number>`.

## Approach

Add `--pr <number>` parameter support through the skill and command chain. This is a markdown-only change — no Python code modifications needed since the exec layer already handles `--pr`.

## Files to Modify

### 1. `.claude/skills/pr-feedback-classifier/SKILL.md`

- Update `argument-hint` from `"[--include-resolved]"` to `"[--pr <number>] [--include-resolved]"`
- Add `--pr <number>` to Arguments section
- Update Step 1 to handle two modes:
  - **If `--pr` specified**: Use `gh pr view <number> --json number,title,url` instead of bare `gh pr view`
  - **If `--pr` not specified**: Current behavior (use current branch)
- Update Step 2 to pass `--pr <number>` through to both exec commands when specified:
  - `erk exec get-pr-review-comments --pr <number>`
  - `erk exec get-pr-discussion-comments --pr <number>`

### 2. `.claude/commands/erk/pr-preview-address.md`

- Update Usage section to show `--pr <number>` option
- Update Phase 1 to parse `--pr` from arguments and pass through to classifier:
  ```
  /pr-feedback-classifier [--pr <number>] [--include-resolved if --all was specified]
  ```

### 3. `.claude/commands/erk/pr-address.md`

- Update Usage section to show `--pr <number>` option
- Update Phase 0 and Phase 1 to use `--pr` when specified
- Update `gh pr view` calls in Phase 0 to use `gh pr view <number>` when `--pr` is provided

## Verification

1. Run `/erk:pr-preview-address --pr 6631` from any branch — should fetch and display comments from PR #6631
2. Run `/erk:pr-preview-address` (no `--pr`) — should retain current behavior (use current branch's PR)