# Plan: Eliminate .impl/ from one-shot workflow

**Part of Objective #8365, Node 2.2**

## Context

The one-shot workflow currently uses `.impl/` as a temporary working directory during planning, then copies outputs to `.erk/impl-context/` for commit. This indirection is unnecessary — Claude can read/write directly from `.erk/impl-context/`, eliminating the copy step entirely.

Node 2.1 (sibling, in PR #8366) handles the same migration for `plan-implement.yml`. This plan covers `one-shot.yml` and its Claude command `one-shot-plan.md`.

## Changes

### 1. `.github/workflows/one-shot.yml`

**Step: "Write prompt to .impl/prompt.md" (lines 107-119)**
- Rename step to "Write prompt to .erk/impl-context/prompt.md"
- Write directly to `.erk/impl-context/prompt.md` instead of `.impl/prompt.md`
- If `.erk/impl-context/prompt.md` already exists (from prior CLI execution), skip — no copy needed
- If not, `mkdir -p .erk/impl-context` and write prompt there directly
- Remove all `mkdir -p .impl` and `.impl/` references

**Step: "Verify plan outputs exist" (lines 162-173)**
- Check `.erk/impl-context/plan.md` instead of `.impl/plan.md`
- Check `.erk/impl-context/plan-result.json` instead of `.impl/plan-result.json`

**Step: "Read plan result" (lines 175-183)**
- Parse `.erk/impl-context/plan-result.json` instead of `.impl/plan-result.json`

**Step: "Commit plan to branch (plan-only mode)" (lines 222-259)**
- Remove the `cp .impl/plan.md .erk/impl-context/plan.md` copy (plan is already there)
- Keep the `ref.json` creation (still needed, writes to `.erk/impl-context/ref.json`)
- Keep the prompt cleanup (still removes `.erk/impl-context/prompt.md` from git)
- Keep the `.worker-impl/` legacy cleanup
- Keep the staging and commit logic

### 2. `.claude/commands/erk/one-shot-plan.md`

**Description (line 3)**
- Change "write results to .impl/" to "write results to .erk/impl-context/"

**Step 1: Read the Prompt (line 13)**
- Read from `.erk/impl-context/prompt.md` instead of `.impl/prompt.md`

**Step 5: Write the Plan (line 34)**
- Write to `.erk/impl-context/plan.md` instead of `.impl/plan.md`

**Step 6: Save Plan to GitHub Issue**
- Line 53: Update `--plan-path .impl/plan.md` → `--plan-path .erk/impl-context/plan.md`
- Line 69: Update `--plan-file .impl/plan.md` → `--plan-file .erk/impl-context/plan.md`

**Step 7: Write Plan Result (lines 78-84)**
- Write to `.erk/impl-context/plan-result.json` instead of `.impl/plan-result.json`

**Important Notes (lines 88-92)**
- Update "Your outputs are `.impl/plan.md` and `.impl/plan-result.json`" to reference `.erk/impl-context/`

## Files NOT Changing

- `.github/workflows/plan-implement.yml` — covered by node 2.1
- `.github/workflows/ci.yml` — covered by node 2.3
- Python source files (impl_folder.py, impl_context.py) — covered by Phase 1 nodes
- docs/learned/ files — covered by Phase 3/4 nodes

## Verification

1. Read both modified files and confirm no `.impl/` references remain (except in comments about the migration or in the legacy `.worker-impl/` cleanup which is unrelated)
2. Trace the data flow end-to-end:
   - Prompt: workflow input → `.erk/impl-context/prompt.md` → Claude reads it
   - Plan: Claude writes `.erk/impl-context/plan.md` → workflow verifies → commits to branch
   - Result: Claude writes `.erk/impl-context/plan-result.json` → workflow reads plan_id/title
3. Confirm the plan-only commit step no longer has a copy operation
