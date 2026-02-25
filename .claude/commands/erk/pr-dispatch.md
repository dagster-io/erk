---
description: Dispatch plans for remote AI implementation
---

# /erk:pr-dispatch

## Goal

Find the most recent GitHub issue created in this conversation and dispatch it for remote AI implementation via `erk pr dispatch`.

## What This Command Does

1. Search conversation for the last GitHub issue reference
2. Extract the issue number
3. Run `erk pr dispatch <issue_number>` to trigger remote implementation

## Finding the Issue

Search the conversation from bottom to top for these patterns (in priority order):

1. **Draft PR reference**: `saved as draft PR #<number>` or `draft PR #<number>`
2. **Pull request URL**: `https://github.com/<owner>/<repo>/pull/<number>`
3. **plan-save/save-raw-plan output**: Look for `**Issue:** https://github.com/.../issues/<number>`
4. **Issue URL**: `https://github.com/<owner>/<repo>/issues/<number>`

Extract the issue number from the most recent match.

## Execution

Once you have the issue number, run:

```bash
erk pr dispatch <issue_number>
```

If the command succeeds, clear the session marker to allow creating new plans in this session:

```bash
erk exec marker delete --session-id "${CLAUDE_SESSION_ID}" plan-saved-issue
```

Display the command output to the user. The `erk pr dispatch` command handles all validation (issue existence, labels, state).

## Error Cases

- **No issue found in conversation**: Report "No GitHub issue found in conversation. Run /erk:plan-save first to create an issue."
- **erk pr dispatch fails**: Display the error output from the command (erk pr dispatch validates the issue)
