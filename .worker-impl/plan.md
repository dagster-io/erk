# Remove remaining `erk prepare` references

## Context

`erk prepare` was removed in v0.8.0 and replaced by `erk br create --for-plan` / `erk br co --for-plan`. Two cleanup commits already landed (fe03e628a, 655a124ad), but stale references remain in documentation, the web UI, and one source constant.

CHANGELOG.md is excluded — those are historical records and should not be modified.

## Changes

### 1. `RELEASING.md` (line 10)
Replace the old `erk prepare -d <plan-issue>` command with the current equivalent.

**Before:** `erk prepare -d <plan-issue>`
**After:** `erk br create --for-plan <plan-issue>` (or just remove the line if releasing no longer uses a plan issue)

### 2. `erkweb/src/client/components/PlanDetail.tsx` (lines 218-220)
Update the two `erk prepare` snippets to use `erk br co --for-plan`:

- Line 218: `erk prepare ${plan.issue_number}` → `erk br co --for-plan ${plan.issue_number}`
- Line 220: `source "$(erk prepare ${plan.issue_number} --script)" && erk implement --dangerous` → `source "$(erk br co --for-plan ${plan.issue_number} --script)" && erk implement --dangerous`

### 3. `packages/erk-shared/src/erk_shared/output/next_steps.py` (line 87)
Delete the `PREPARE_SLASH_COMMAND = "/erk:prepare"` constant. The doc says it's unused.

### 4. `docs/learned/cli/command-organization.md`
Remove `erk prepare` from all tables and examples. Replace with `erk br co --for-plan` where appropriate:

- Line 26: Remove `erk prepare` line from the code block
- Line 38: Remove `prepare` from the "highest-frequency" list
- Line 52: Remove the `prepare` row from the table
- Lines 148-154: Remove `prepare` from the decision framework diagram
- Line 225: Remove `erk prepare 42` from the "Good Patterns" example
- Line 235: Remove `prepare` from the explanation

### 5. `docs/learned/planning/next-steps-output.md` (line 68)
Remove or update the line about `PREPARE_SLASH_COMMAND` (it references the constant we're deleting).

### 6. `docs/learned/claude-code/agent-commands.md` (line 20)
Remove `/erk:prepare` from the list of commands using conversation-context extraction.

### 7. `docs/learned/architecture/command-boundaries.md` (line 86)
Remove the `/erk:prepare` row from the hybrid command examples table.

### 8. `.worker-impl/prompt.md`
Delete this file — it's a leftover from the previous cleanup task.

## Verification

- `grep -r "erk prepare" --include="*.md" --include="*.py" --include="*.tsx"` should return only CHANGELOG.md hits
- `grep -r "erk:prepare" --include="*.md" --include="*.py"` should return only CHANGELOG.md hits
- `grep -r "PREPARE_SLASH_COMMAND"` should return nothing
