# Plan: Fix `/erk:land` Command Documentation

## Problem

The `/erk:land` command documentation incorrectly references `erk pr land` but the actual CLI command is `erk land` (a top-level command).

From the interaction:
- `erk pr land 5089 --force` → "No such command 'land'"
- `erk branch land 5089 --force` → "No such command 'land'"
- `erk land 5089 --force` → **Works correctly**

## Changes

**File:** `.claude/commands/erk/land.md`

### Change 1: Fix command name in header (line 6)
- From: `# /erk:pr-land`
- To: `# /erk:land`

### Change 2: Fix description (line 8)
- From: `Objective-aware wrapper for \`erk pr land\``
- To: `Objective-aware wrapper for \`erk land\``

### Change 3: Fix Step 6 command (lines 106-111)
- From: `erk pr land <PR_NUMBER> --force`
- To: `erk land <PR_NUMBER> --force`

## Verification

After the fix, the command documentation will match actual CLI behavior where `land` is a top-level command.