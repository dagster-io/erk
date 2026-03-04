# Plan: Make pr-address plan-mode aware

## Context

When `/erk:pr-address` is invoked in plan mode, it currently tells the user to exit plan mode first. Instead, it should work *within* plan mode — classifying feedback, planning the changes, and presenting that plan for approval before any edits are made.

## Change

**File**: `.claude/commands/erk/pr-address.md` (line 26)

Replace the current plan mode instruction:

```markdown
> **Plan mode**: If plan mode is active, exit it first (press `Escape`). This command manages its own execution flow and needs to make edits directly.
```

With a plan-mode-aware instruction:

```markdown
> **Plan mode**: If plan mode is active, run Phases 0-2 (mode detection, classify feedback, display batched plan) as normal — these are read-only. Then write the execution plan to the plan file and call ExitPlanMode. Do NOT execute Phases 3-6 (edits, commits, resolution) until plan mode is exited and the user approves. In Plan File Mode, the same applies: run PF-1 and PF-2, then write the plan and call ExitPlanMode before executing PF-3 through PF-6.
```

This is a single-line edit in one file. No other files need changes.

**Note**: The replacement text explicitly covers both Code Review Mode (Phases 3-6) and Plan File Mode (PF-3 through PF-6), since Phase 0 can route to either flow.

## Verification

1. Invoke `/erk:pr-address` while in plan mode on a branch with PR comments
2. Confirm it classifies feedback and writes a plan instead of refusing to run
3. Confirm it calls ExitPlanMode after presenting the plan
4. After approval, confirm it proceeds with the execution phases normally
