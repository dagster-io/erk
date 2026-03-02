# Plan: Always Suggest Save in objective-plan

## Context

When `/erk:objective-plan` completes planning, the `exit-plan-mode-hook` fires and presents 3 options: "Create a plan PR", "Skip PR and implement here", and "View/Edit the plan". The user wants objective-plan to always direct toward saving the plan as a PR, not offering direct implementation. This makes sense because objective plans are multi-node workflows where each node becomes a tracked PR — implementing directly bypasses the tracking.

## Changes

### 1. `.claude/commands/erk/objective-plan.md`

Add a new section at the end (after "Important Notes") that overrides the hook's default behavior:

```markdown
## Post-Plan Behavior

**CRITICAL: Objective plans must ALWAYS be saved as PRs.** When the exit-plan-mode hook presents save-or-implement options, ALWAYS proceed with "Create a plan PR" by running `/erk:plan-save`. Do NOT offer to implement directly — objective node plans require PR tracking for the objective's roadmap status to work correctly.
```

Also update the Output Format section's "End" line to reinforce this.

### 2. `.claude/commands/erk/system/objective-plan-node.md`

Update **Step 8** to remove mention of the save-or-implement choice and instead say to always save:

- Current: "After the plan is approved in plan mode, the `exit-plan-mode-hook` will prompt to save or implement."
- New: Instruct to always save — when the hook fires, proceed directly with `/erk:plan-save`.

Also update the Output Format's "End" line.

## Files Modified

| File | Change |
|------|--------|
| `.claude/commands/erk/objective-plan.md` | Add "Post-Plan Behavior" section, update Output Format |
| `.claude/commands/erk/system/objective-plan-node.md` | Update Step 8 to always-save, update Output Format |

## Verification

1. Read both files after editing to confirm the instructions are clear
2. The exit-plan-mode hook itself is NOT modified — the command-level instructions override the agent's behavior when it sees the hook's options
