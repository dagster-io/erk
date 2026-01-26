---
description: Trigger remote PR addressing for the last PR mentioned in conversation
---

# /erk:pr-address-remote

## Goal

Find the most recent PR reference in this conversation and trigger remote PR review comment addressing via `erk pr address remote`.

## What This Command Does

1. Search conversation for the last PR reference
2. Extract the PR number
3. Run `erk pr address remote <pr_number>` to trigger remote addressing

## Finding the PR

Search the conversation from bottom to top for these patterns (in priority order):

1. **PR URL**: `https://github.com/<owner>/<repo>/pull/<number>`
2. **PR creation output**: `PR: https://github.com/.../pull/<number>` or `Draft PR #<number> created`
3. **PR reference with context**: `PR #<number>` (e.g., "PR #5846", "submitted PR #5846")

Extract the PR number from the most recent match.

## Execution

Once you have the PR number, run:

```bash
erk pr address remote <pr_number>
```

Display the command output to the user. The `erk pr address remote` command handles all validation (PR existence, open state, workflow dispatch).

## Error Cases

- **No PR found in conversation**: Report "No PR reference found in conversation. Mention a PR URL or number first."
- **erk pr address remote fails**: Display the error output from the command
