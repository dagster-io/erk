# Plan: Promote objective-reevaluate → objective-reconcile and integrate into planning

## Context

Objective reconciliation currently only happens at land-time via `system:objective-update-with-landed-pr`. This means if someone doesn't use the erk land workflow, or if changes happen between the last land and the next plan step, the objective drifts. By running reconciliation at plan-creation time, we catch drift automatically — the planner always works from an accurate objective.

The command also needs to move from local-only to shipped, and "reevaluate" should become "reconcile."

## Changes

### 1. Rename and promote the command

- **Delete**: `.claude/commands/local/objective-reevaluate.md`
- **Create**: `.claude/commands/erk/objective-reconcile.md`
  - Same content, updated name/title references
  - Update description to match new name
  - Keep all 6 phases intact

### 2. Update skill registry references

- Update skill listing entries: `local:objective-reevaluate` → `erk:objective-reconcile` in any files that reference it (CLAUDE.md, skill lists, etc.)

### 3. Integrate into `/erk:objective-plan` (outer skill)

Insert a new **Step 2.5** between Step 2 (Fetch and Set Up Objective Context) and Step 3 (Load Objective Skill):

```
### Step 2.5: Reconcile Objective

Invoke `/erk:objective-reconcile <objective-number>` via the Skill tool.

This audits the objective against the current codebase, identifies stale references
and nodes completed outside the erk land workflow, and applies updates with user
confirmation before proceeding to node selection.

If reconciliation finds no issues, it reports "all references current" and continues.
If it finds and fixes issues, the roadmap displayed in Step 4 will reflect the
updated state.
```

For the **fast path** (Step 0), add reconcile before delegating to inner skill:

```
### Step 0: Check for Known Node (Fast Path)

Parse $ARGUMENTS for --node <node-id>. If --node is present along with an issue number:

1. Run `/erk:objective-reconcile <objective-number>` via the Skill tool.
2. Then invoke `/erk:system:objective-plan-node <objective-number> --node <node-id>`.
```

### 4. Update `allowed-tools` in objective-plan.md

Add `Skill` to the allowed-tools list (already present — confirmed). The reconcile skill invocation uses `Skill` which is already allowed.

## Files to modify

| File | Action |
|------|--------|
| `.claude/commands/local/objective-reevaluate.md` | Delete |
| `.claude/commands/erk/objective-reconcile.md` | Create (renamed content) |
| `.claude/commands/erk/objective-plan.md` | Add Step 2.5, update Step 0 |

## What NOT to change

- `objective-plan-node.md` (inner skill) — no changes needed; reconciliation happens before it's invoked
- No CLI code changes — this is purely skill/command level
- No exec script changes

## Verification

1. Run `/erk:objective-reconcile <number>` standalone — should work identically to the old local command
2. Run `/erk:objective-plan <number>` — should trigger reconciliation before showing the roadmap
3. Run `/erk:objective-plan <number> --node 1.1` (fast path) — should reconcile before delegating to inner skill
4. Confirm `/local:objective-reevaluate` no longer exists
