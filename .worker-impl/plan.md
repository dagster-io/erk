# Plan: Auto-refresh status line at end of pr-submit

## Problem

After `/erk:pr-submit` completes, the status line doesn't automatically update to reflect the new git state (new commit, new PR). The user has to manually run `/local:statusline-refresh`.

## Solution

Add the status line refresh instruction at the end of the pr-submit skill file.

## Changes

**File:** `.claude/commands/erk/pr-submit.md`

Add a new section after "Report Results" that instructs the agent to output the status line refresh message:

```markdown
### Refresh Status Line

After reporting results, output the following to trigger a status line refresh:

```
🔄 Status line refreshed
```
```

This will cause Claude Code's automatic 300ms refresh mechanism to update the status line display.

## Verification

1. Run `/erk:pr-submit` on a branch with changes
2. Observe that the status line automatically updates after the command completes
3. Confirm the `🔄 Status line refreshed` message appears at the end of the output