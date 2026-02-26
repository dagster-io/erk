# Plan: Re-add .impl to .gitignore

## Context

The `.impl/` directory (used for plan implementation context) was previously in `.gitignore` but was removed at some point. It should be ignored to prevent accidental commits of ephemeral implementation state.

## Change

Add `.impl` to `.gitignore` in the "Local implementation and configuration" section.

**File:** `/Users/schrockn/code/erk/.gitignore`

Add after line 20 (`.erk/impl-context/`):

```
.impl/
```

## Verification

Run `git status` after the change — any existing `.impl/` directory should no longer appear as untracked.
