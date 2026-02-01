# Fix `/erk:pr-address-remote` command syntax

## Problem

The skill references a nonexistent command `erk pr address remote <pr_number>`. The actual command is `erk launch pr-address --pr <pr_number>`.

## Change

**File:** `.claude/commands/erk/pr-address-remote.md`

Update all 3 references from `erk pr address remote` to `erk launch pr-address --pr`:

1. Line 9: Goal description → `erk launch pr-address`
2. Line 15: Step 3 description → `erk launch pr-address --pr <pr_number>`
3. Lines 32-33: Code block → `erk launch pr-address --pr <pr_number>`
4. Line 35: Prose reference → `erk launch pr-address`
5. Line 40: Error case reference → `erk launch pr-address`

## Verification

Run `/erk:pr-address-remote` after fixing and confirm it invokes `erk launch pr-address --pr <number>` correctly.