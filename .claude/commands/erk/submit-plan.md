---
description: Submit the last created issue for remote implementation
---

# /erk:submit-plan

## Goal

Find the most recent GitHub issue created in this conversation and submit it for remote AI implementation via `erk submit`.

## What This Command Does

1. Search conversation for the last GitHub issue reference
2. Extract the issue number
3. Run `erk submit <issue_number>` to trigger remote implementation

## Finding the Issue

Search the conversation from bottom to top for these patterns (in priority order):

1. **save-plan/save-raw-plan output**: Look for `**Issue:** https://github.com/.../issues/<number>`
2. **Issue URL**: `https://github.com/<owner>/<repo>/issues/<number>`

Extract the issue number from the most recent match.

## Execution

Once you have the issue number, run:

```bash
erk submit <issue_number>
```

Display the command output to the user. The `erk submit` command handles all validation (issue existence, labels, state).

## Error Cases

- **No issue found in conversation**: Report "No GitHub issue found in conversation. Run /erk:save-plan first to create an issue."
- **erk submit fails**: Display the error output from the command (erk submit validates the issue)
