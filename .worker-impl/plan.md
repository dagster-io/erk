# Plan: Add slot options to plan-save next-steps copy

## Context

The `--new-slot` flag was just added to `erk br create` (this branch). After saving a plan via `/erk:plan-save`, the skill renders "next steps" copy with `erk br create --for-plan <N>` commands. Currently these commands don't mention slot allocation at all. The user wants both options (new slot vs. stack in place) always shown, with the default/recommended option varying by context:

- **On trunk**: recommend `--new-slot` (user is in root worktree, needs a slot)
- **Not on trunk**: recommend no flag / stack in place (user is likely already in a slot)

## File to modify

`.claude/commands/erk/plan-save.md` — the Claude Code skill instructions

## Changes

### 1. Add trunk detection to Step 4

Insert a trunk detection sub-step at the beginning of Step 4 (before the display logic):

> Run `git branch --show-current` to get the current branch name.
> - If the result is `main`, `master`, or empty (detached HEAD): **on trunk**
> - Otherwise: **not on trunk**

### 2. Replace the "OR exit Claude Code first" blocks

Both backend sections (draft-PR and github) have identical `erk br create` commands. Replace the current 3-line block in each with a trunk-aware version that shows both slot options.

**Structure for both backends:**

```
OR exit Claude Code first, then run one of:

  <RECOMMENDED GROUP — shown first>:
    Local: erk br create [--new-slot] --for-plan <issue_number>
    Prepare+Implement: source "$(erk br create [--new-slot] --for-plan <issue_number> --script)" && erk implement --dangerous

  <ALTERNATIVE GROUP — shown second>:
    Local: erk br create [--new-slot] --for-plan <issue_number>
    Prepare+Implement: source "$(erk br create [--new-slot] --for-plan <issue_number> --script)" && erk implement --dangerous

  Submit to Queue: erk plan submit <issue_number>
```

**On trunk — recommended = new slot:**
```
  New slot (recommended — you're on trunk):
    Local: erk br create --new-slot --for-plan <issue_number>
    Prepare+Implement: source "$(erk br create --new-slot --for-plan <issue_number> --script)" && erk implement --dangerous

  Same slot:
    Local: erk br create --for-plan <issue_number>
    Prepare+Implement: source "$(erk br create --for-plan <issue_number> --script)" && erk implement --dangerous
```

**Not on trunk — recommended = same slot:**
```
  Same slot (recommended — you're in a slot):
    Local: erk br create --for-plan <issue_number>
    Prepare+Implement: source "$(erk br create --for-plan <issue_number> --script)" && erk implement --dangerous

  New slot:
    Local: erk br create --new-slot --for-plan <issue_number>
    Prepare+Implement: source "$(erk br create --new-slot --for-plan <issue_number> --script)" && erk implement --dangerous
```

### 3. Factor the slot options block

Since both backend sections (draft-PR and github) need identical slot option blocks, define the "slot options block" once in the instructions and reference it from both backend sections to keep the skill DRY.

## Out of scope

- `next_steps.py` (Python CLI output) — the dataclasses don't have trunk context and the user's request is about the Claude Code skill experience
- `IssueNextSteps`/`DraftPRNextSteps` dataclass changes — can be done in a follow-up

## Verification

1. Run `/erk:plan-save` from a trunk branch (master) — verify the "New slot" option appears first with "(recommended — you're on trunk)"
2. Run `/erk:plan-save` from a feature branch in a slot — verify the "Same slot" option appears first with "(recommended — you're in a slot)"
3. Verify both backend variants (draft-PR and github) show the correct conditional copy
