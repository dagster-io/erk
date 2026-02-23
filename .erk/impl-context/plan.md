# Fix plan-save.md checkout commands to use `--for-plan`

## Context

The `/erk:plan-save` command template (`plan-save.md`) tells Claude to output checkout commands using raw `<branch_name>`, but Claude substituted `erk-plan-7942` (the plan number formatted as a branch name) instead of the actual git branch. This caused `erk br co --new-slot erk-plan-7942` to fail with "Branch does not exist."

The Python code in `next_steps.py` already correctly uses `--for-plan <plan_number>`, which resolves the branch from plan metadata. The command template should match.

## Change

**File:** `.claude/commands/erk/plan-save.md`

Replace all `erk br co` checkout commands that use `<branch_name>` with `--for-plan <plan_number>`:

### Slot options block (lines 141-171)

- `erk br co --new-slot <branch_name>` → `erk br co --new-slot --for-plan <plan_number>`
- `erk br co --new-slot <branch_name> --script` → `erk br co --new-slot --for-plan <plan_number> --script`
- `erk br co <branch_name>` → `erk br co --for-plan <plan_number>`
- `erk br co <branch_name> --script` → `erk br co --for-plan <plan_number> --script`

### Draft PR section (lines 173-187)

- `erk br co <branch_name>` → `erk br co --for-plan <plan_number>`
- `erk br co <branch_name> --script` → `erk br co --for-plan <plan_number> --script`

### GitHub issue section (lines 189-204)

- `erk br co <branch_name>` → `erk br co --for-plan <plan_number>`
- `erk br co <branch_name> --script` → `erk br co --for-plan <plan_number> --script`

This matches the existing `next_steps.py` patterns (`DraftPRNextSteps.prepare`, `prepare_new_slot`, etc.).

## Verification

1. Run `/erk:plan-save` and confirm the output uses `--for-plan <number>` in all checkout commands
2. Run the outputted `erk br co --for-plan <number>` command and confirm it works
