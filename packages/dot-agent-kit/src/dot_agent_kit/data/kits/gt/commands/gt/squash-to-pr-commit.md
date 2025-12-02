---
description: Squash commits using PR body as commit message
---

# Squash to PR Commit

Squash all commits on the current branch into one, using the PR body (AI-generated summary) as the commit message.

## Use Case

After checking out a remote implementation PR with `erk pr co NNNN`, use this command to squash the multiple implementation commits into a single clean commit with the good AI-generated summary.

## Implementation

### Step 1: Extract Commit Message from PR Body

**Session ID extraction**: Look for the `SESSION_CONTEXT` reminder in your context (injected by hooks). It contains `session_id=<uuid>`. Extract this value.

Use the kit CLI command to fetch, parse, and write the message to scratch:

```bash
result=$(dot-agent run gt get-pr-commit-message --session-id "<session-id>" 2>&1)
```

Parse the JSON output:

- If `success` is `false`, display the error message and stop
- If `success` is `true`, the `message_file` field contains the path to the commit message

### Step 2: Run gt squash with the Message File

If message extraction succeeded, run:

```bash
gt squash -m "$(cat <message_file>)"
```

The message is read from the scratch file, avoiding shell escaping issues with multi-line content.

### Step 3: Report Results

On success:

```
✓ Commits squashed with PR summary as message

Next steps:
  gt submit    # Push the squashed commit
```

On failure (no PR, empty body, etc.):

```
❌ Could not squash: <error message>

This command requires an open PR with a body. Make sure:
1. You're on a branch with an open PR (check with `gh pr view`)
2. The PR has a body (not just a title)
```

## Error Handling

| Error Type      | Cause                    | Action                          |
| --------------- | ------------------------ | ------------------------------- |
| `no_pr`         | No PR for current branch | Tell user to check `gh pr view` |
| `empty_body`    | PR has no body content   | Tell user to add PR description |
| `no_summary`    | Only metadata in body    | Tell user PR body needs content |
| gt squash fails | Merge conflicts or other | Display gt error output         |

## Notes

- This command uses `gt squash -m` which is officially supported
- The PR body is parsed to strip the metadata footer (--- separator)
- Works with any PR, not just remote implementations
