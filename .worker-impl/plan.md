# Plan: Add -f/--force hint to delete-current error message

## Problem

When `erk down --delete-current` fails because a PR is still open, the error message doesn't inform users they can use `-f/--force` to override:

```
Error: Pull request for branch '...' is still open.
https://github.com/...
Only closed or merged branches can be deleted with --delete-current.
```

## Solution

Add a hint about `-f/--force` to the error message.

## Changes

**File:** `src/erk/cli/commands/navigation_helpers.py` (line ~105)

Update the error message from:
```
"Only closed or merged branches can be deleted with --delete-current."
```

To:
```
"Only closed or merged branches can be deleted with --delete-current.\n"
"Use -f/--force to delete anyway."
```

## Result

```
Error: Pull request for branch '...' is still open.
https://github.com/...
Only closed or merged branches can be deleted with --delete-current.
Use -f/--force to delete anyway.
```