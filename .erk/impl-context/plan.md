# Fix `--plan` → `--pr` in one-shot.yml

## Context

Commit `3be1ad48e` (#8128) simplified `update-objective-node` to a PR-only reference model, removing the `--plan` flag and keeping only `--pr`. The `one-shot.yml` workflow was not updated, so the "Update objective roadmap node" step fails every time it runs.

## Change

**File:** `.github/workflows/one-shot.yml`, line 218

Replace `--plan "$PLAN_NUMBER"` with `--pr "$PLAN_NUMBER"`.

## Verification

- Confirm `erk exec update-objective-node -h` shows `--pr` (not `--plan`)
- Confirm no other references to `--plan` exist in workflow files for this command
