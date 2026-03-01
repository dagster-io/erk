# Plan: Document mid-rebase behavior for `erk pr rebase`

## Context

`erk pr rebase` (and the underlying `/erk:rebase` slash command) works when invoked mid-rebase — i.e., when a `git rebase` is already in progress with unresolved merge conflicts. This behavior should be documented so users know they can use it as a recovery tool, not just as a start-from-scratch rebase command.

## Changes

### 1. Update `erk pr rebase` help string
**File:** `src/erk/cli/commands/pr/rebase_cmd.py`

Add a note to the docstring that the command works when a rebase is already in progress with conflicts. Add an example showing this usage.

### 2. Update `/erk:rebase` command description
**File:** `.claude/commands/erk/rebase.md`

Add a note at the top (before the steps) explaining that this command can be used both to start a fresh rebase and to resume/resolve a rebase already in progress.

### 3. Update rebase-conflict-patterns doc
**File:** `docs/learned/architecture/rebase-conflict-patterns.md`

Add a section noting that `erk pr rebase` can resolve conflicts mid-rebase, and update `read_when` to include "resuming a rebase with conflicts".

## Verification

- Read the updated files to confirm documentation is clear and accurate
- Run `erk pr rebase --help` to verify the help string renders correctly
