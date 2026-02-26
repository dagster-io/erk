# Plan: Update ci.yml .impl dir check to .erk/impl-context (Objective #8365, Node 2.3)

## Context

Part of Objective #8365 (Eliminate .impl/ Folder — Unify on .erk/impl-context/).

The `ci.yml` workflow has two places that check for implementation context folders:

1. **`check-submission` job** (line 28-30): Already uses the `.github/actions/check-impl-context` composite action, which correctly checks for `.erk/impl-context`. No change needed.
2. **`autofix` job** (lines 255-264): Has an inline check that still references `.impl`. This is the only remaining `.impl` reference in `ci.yml` and needs updating.

## Changes

### File: `.github/workflows/ci.yml`

**Step: "Check for submission folder" (lines 255-264)**

Update the directory check from `.impl` to `.erk/impl-context` and rename the output variable for consistency:

- Line 259: `if [ -d ".impl" ]` → `if [ -d ".erk/impl-context" ]`
- Line 260: `echo "Found .impl folder, skipping autofix"` → `echo "Found .erk/impl-context folder, skipping autofix"`
- Line 261: `echo "has_impl_folder=true"` → `echo "has_impl_context=true"`
- Line 263: `echo "has_impl_folder=false"` → `echo "has_impl_context=false"`

**Step: "Determine if autofix should run" (line 272)**

Update the reference to the renamed output variable:

- Line 272: `steps.check.outputs.has_impl_folder` → `steps.check.outputs.has_impl_context`

**Total: 5 line changes in 1 file.**

## Verification

1. Run `make fast-ci` via devrun to confirm no CI-related tests break
2. Grep for any remaining `.impl` references in `ci.yml` to confirm none are left
3. Verify the output variable rename is consistent (only referenced in lines 261, 263, 272)
