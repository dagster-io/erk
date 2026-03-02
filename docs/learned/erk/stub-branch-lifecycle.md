---
title: Stub Branch Lifecycle
read_when:
  - "working with slot pool or branch cleanup"
  - "debugging Graphite branch tracking"
tripwires:
  - action: "deleting stub branches without untracking from Graphite first"
    warning: "Stub branches tracked by Graphite pollute gt log output. Untrack with gt branch untrack before deletion."
---

# Stub Branch Lifecycle

## What Are Stub Branches?

`__erk-slot-N-br-stub__` branches are internal placeholders created during slot pool operations. They are implementation details of erk's worktree management and should not be visible to users.

## Problem

These branches get tracked by Graphite and pollute `gt log` output, cluttering the stack view with internal branches.

## Solution

Auto-untrack during `audit-branches` Phase 1, Step 8:

```bash
gt log short --no-interactive 2>&1 | grep -oE '__erk-slot-[0-9]+-br-stub__' | while read stub; do
  gt branch untrack "$stub" --no-interactive --force
done
```

## Location

`.claude/commands/local/audit-branches.md` Phase 1, Step 8 handles stub branch cleanup.

The audit-branches command also skips stub branches during branch analysis (Phase 2) and worktree analysis (Phase 3) using `[[ "$branch" == "__erk-slot-"* ]] && continue` guards.

## Note

The original plan (#8530) also proposed blocking slot auto-unassignment, but only stub untracking was implemented.
