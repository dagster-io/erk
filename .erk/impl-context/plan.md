# Rename "In plan br" to "In current wt" in plan-save output

## Context

The plan-save command's Step 7 output displays slot options with the label "In plan br" for the option that checks out the plan's branch in the current worktree. This label is confusing — "In current wt" better describes what actually happens (you stay in your current worktree and switch to the plan branch).

## Change

**File:** `.claude/commands/erk/plan-save.md`

Replace all 5 occurrences of `In plan br` with `In current wt` in the Step 7 display templates (lines 183, 198, 201, 205, 208).

The corresponding `erk br co --for-plan` commands remain unchanged — only the display label changes.

## Verification

- Read the modified file and confirm all 5 instances were replaced
- Confirm no other files reference "In plan br"
