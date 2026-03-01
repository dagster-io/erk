# Plan: Unassign blocking slots and teach audit-branches to auto-unassign

## Context

Three erk slots (37, 54, 55) are occupied by branches with closed PRs, blocking `gt repo sync` cleanup. Currently, audit-branches *detects* blocking slot worktrees but only acts on them if the user manually selects that category in Phase 9. Slot worktrees with closed PRs are unambiguously stale — the slot should be freed automatically, just like AUTO-CLEANUP branches.

## Step 1: Unassign the 3 blocking slots

```bash
erk slot unassign erk-slot-37
erk slot unassign erk-slot-54
erk slot unassign erk-slot-55
```

If any fail due to uncommitted changes, discard changes first:
```bash
cd <worktree-path> && git checkout . && git clean -fd
erk slot unassign <slot>
```

## Step 2: Update audit-branches command

**File:** `.claude/commands/local/audit-branches.md`

**Change:** Move blocking slot worktrees from the interactive "ask user" flow to automatic execution. Specifically:

1. **Phase 7 (Categorization):** Split the current `BLOCKING WORKTREES` category into two:
   - **Blocking slot worktrees** (erk-slot-NN with closed PRs) → move to AUTO-CLEANUP, auto-unassign
   - **Blocking non-slot worktrees** (vanilla worktrees with closed PRs) → keep in BLOCKING WORKTREES for user confirmation

2. **Phase 10 (Execution):** In Step 0 (AUTO-CLEANUP), add slot unassignment before branch deletion. When a blocking slot worktree is encountered during auto-cleanup:
   - Run `erk slot unassign <slot>`
   - If fails, discard changes and retry
   - Then proceed with `gt repo sync` to clean up the freed branch

3. **Phase 8 (Present Findings):** Update the BLOCKING WORKTREES table to note that slot worktrees will be auto-unassigned, and only non-slot blocking worktrees require user decision.

## Verification

- Run `/local:audit-branches` on the current repo state and confirm:
  - Blocking slot worktrees are reported as auto-cleanup items
  - Non-slot blocking worktrees still appear in the interactive category
  - The execution phase unassigns slots without user prompt
