# Plan: Remove PR description update from pr-address

## Context
The user wants to stop updating the PR description (title and body) as part of the pr-address workflow.

## Changes

**File:** `.claude/commands/erk/pr-address.md`

1. Remove Phase 5 ("Update PR Title and Body") entirely (lines 390-400)
2. Renumber Phase 6 → Phase 5 ("Upload Address Session")
3. Remove the `update-pr-description` skip mention in PF-6 (line 121): the line "Skip `update-pr-description` and `upload-impl-session`" should become just "Skip `upload-impl-session`"

## Verification
- Read the modified file to confirm Phase 5 (update-pr-description) is gone
- Confirm the remaining phases flow correctly (Phase 4 → Phase 5 upload session)
