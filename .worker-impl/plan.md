# Plan: Commit plan to branch after plan-only one-shot

## Context

When `erk one-shot --plan-only` runs, the CI plan job creates `.impl/plan.md` (gitignored, local to the container) and saves the plan to a GitHub issue/PR body. But the plan is never committed back to the branch. The PR diff only shows the prompt file, making it impossible to:

- Do inline PR review of the plan (comment on specific sections)
- Run `pr-address` to revise the plan based on review comments

PR #7917 demonstrates this: the only file in the diff is `.erk/impl-context/prompt.md`.

## Changes

### 1. Add "commit plan to branch" step in `one-shot.yml`

**File:** `.github/workflows/one-shot.yml`

Add a new step after "Register one-shot plan with issue and PR" (after line ~203) that runs only in plan-only mode:

- Condition: `inputs.plan_only && steps.plan.outputs.plan_success == 'true' && steps.read_result.outputs.plan_id != ''`
- Copy `.impl/plan.md` to `.erk/impl-context/plan.md`
- Create `.erk/impl-context/ref.json` with plan metadata (following `plan_save.py` pattern at lines 184-200)
- `git rm` prompt files (both `.worker-impl/prompt.md` and `.erk/impl-context/prompt.md`, whichever exists)
- Commit with message like `"Add plan for #$PLAN_ID (plan-only)"` and push

This runs after the plan is already saved to GitHub, so even if the commit/push fails, the plan is not lost.

### 2. Preserve `.erk/impl-context/plan.md` in `pr-address.yml` cleanup

**File:** `.github/workflows/pr-address.yml` (lines 72-86)

The cleanup step currently does `git rm -rf .erk/impl-context/`. For plan-only PRs, `plan.md` IS the PR content and must be preserved.

Change: if `.erk/impl-context/plan.md` is tracked, skip the entire `.erk/impl-context/` cleanup. Rationale:

- For plan-only PRs: all files in `.erk/impl-context/` are meaningful
- For implementation PRs: `plan-implement.yml` already handles its own cleanup of `.erk/impl-context/` before implementation runs
- `pr-address` doesn't need to clean up what `plan-implement` already cleaned

### 3. Update prompt-reading step to also check `.erk/impl-context/prompt.md`

**File:** `.github/workflows/one-shot.yml` (lines 107-119)

Currently only checks for `.worker-impl/prompt.md`. Add an `elif` branch to also check `.erk/impl-context/prompt.md`, so the workflow reads the prompt regardless of which dispatch path wrote it.

## Files

| File                               | Change                                                            |
| ---------------------------------- | ----------------------------------------------------------------- |
| `.github/workflows/one-shot.yml`   | Add plan commit step (change 1), update prompt reading (change 3) |
| `.github/workflows/pr-address.yml` | Preserve plan.md in cleanup (change 2)                            |

## Not Changing

- `one_shot_dispatch.py` — dispatch prompt path stays as `.worker-impl/prompt.md` for now
- `plan-implement.yml` — already handles its own `.erk/impl-context/` cleanup; implement job is skipped in plan-only mode
- `ci.yml` — already excludes `.erk/impl-context/**` from triggers

## Verification

1. Run `erk one-shot "test prompt" --plan-only --dry-run` to verify dispatch still works
2. Manually check a plan-only workflow run to confirm:
   - PR diff shows `.erk/impl-context/plan.md` (not just the prompt)
   - Prompt file is removed from the branch
3. Run `pr-address` on a plan-only PR and verify `.erk/impl-context/plan.md` survives cleanup
