---
description: Address PR review comments on current branch
---

# /erk:pr-address

## Description

Fetches unresolved PR review comments from the current branch's PR and guides you through addressing each one. After you address a comment, marks the thread as resolved.

## Usage

```bash
/erk:pr-address
/erk:pr-address --all    # Include resolved threads (for reference)
```

## Agent Instructions

### Step 1: Fetch Review Comments

Run the kit CLI command to get unresolved review comments:

```bash
dot-agent run erk get-pr-review-comments
```

Parse the JSON output:

```json
{
  "success": true,
  "pr_number": 123,
  "pr_url": "https://github.com/owner/repo/pull/123",
  "pr_title": "Feature: Add new capability",
  "threads": [
    {
      "id": "PRRT_abc123",
      "path": "src/foo.py",
      "line": 42,
      "is_outdated": false,
      "comments": [
        {
          "author": "reviewer",
          "body": "This should use LBYL pattern instead of try/except",
          "created_at": "2024-01-01T10:00:00Z"
        }
      ]
    }
  ]
}
```

### Step 2: Handle No Comments Case

If `threads` is empty, display: "No unresolved review comments on PR #123."

### Step 3: Display Summary

Show the user what needs to be addressed in a markdown table with columns: #, File, Line, Reviewer, Summary

### Step 4: Address Each Comment

For each unresolved thread:

1. **Read the file** at the specified path and line to understand context
2. **Show the comment** with context showing thread number, file:line, author, comment body, and current code
3. **Make the fix** following the reviewer's feedback
4. **Explain what you changed** to the user
5. **Mark resolved** (see Step 5)

### Step 5: Mark Thread Resolved

After addressing each comment, resolve the thread:

```bash
dot-agent run erk resolve-review-thread --thread-id "PRRT_abc123"
```

Report: "Resolved thread on src/foo.py:42"

### Step 6: Continue or Complete

After resolving a thread:

- If more threads remain, continue to the next one
- If all threads resolved, display completion message with summary of changes and next steps (run tests, commit, push)

### Step 7: Handle Outdated Threads

If a thread has `is_outdated: true`:

- The code has changed since the comment was made
- Show the user the comment but note it may no longer apply
- Ask if they want to: (1) Check if already fixed, (2) Resolve as outdated, or (3) Skip for now

### Error Handling

**No PR for branch:** Display error and suggest creating a PR with `gt create` or `gh pr create`

**GitHub API error:** Display error and suggest checking `gh auth status` and repository access
