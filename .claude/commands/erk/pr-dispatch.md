---
description: Dispatch plans for remote AI implementation
---

# /erk:pr-dispatch

## Goal

Find the most recent plan created in this conversation and dispatch it for remote AI implementation via `erk pr dispatch`.

## What This Command Does

1. Search conversation for the last plan reference
2. Extract the plan number
3. Run `erk pr dispatch <plan_number>` to trigger remote implementation

## Finding the Plan

Search the conversation from bottom to top for these patterns (in priority order):

1. **Draft PR reference**: `saved as draft PR #<number>` or `draft PR #<number>`
2. **Pull request URL**: `https://github.com/<owner>/<repo>/pull/<number>`
3. **Plan URL**: `https://github.com/.../pull/<number>` (legacy: `https://github.com/.../issues/<number>`)

Extract the plan number from the most recent match.

## Execution

Once you have the plan number, run:

```bash
erk pr dispatch <plan_number>
```

If the command succeeds, clear the session marker to allow creating new plans in this session:

```bash
erk exec marker delete --session-id "${CLAUDE_SESSION_ID}" plan-saved-issue
```

Display the command output to the user. The `erk pr dispatch` command handles all validation (plan existence, labels, state).

## Error Cases

- **No plan found in conversation**: Report "No plan found in conversation. Run /erk:plan-save first to create a plan."
- **erk pr dispatch fails**: Display the error output from the command (erk pr dispatch validates the plan)
