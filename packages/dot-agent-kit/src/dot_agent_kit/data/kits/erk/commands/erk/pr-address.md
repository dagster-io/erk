---
description: Address PR review comments on current branch
---

# /erk:pr-address

## Description

Fetches unresolved PR review comments AND PR discussion comments from the current branch's PR and guides you through addressing each one. Review threads are resolved via GitHub API; discussion comments are marked as addressed with a reaction.

## Usage

```bash
/erk:pr-address
/erk:pr-address --all    # Include resolved threads (for reference)
```

## Agent Instructions

### Step 1: Fetch All Comments

Run both kit CLI commands to get review comments AND discussion comments:

```bash
dot-agent run erk get-pr-review-comments
dot-agent run erk get-pr-discussion-comments
```

**Review Comments JSON:**

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

**Discussion Comments JSON:**

```json
{
  "success": true,
  "pr_number": 123,
  "pr_url": "https://github.com/owner/repo/pull/123",
  "pr_title": "Feature: Add new capability",
  "comments": [
    {
      "id": 12345,
      "author": "reviewer",
      "body": "Please also update the docs",
      "url": "https://github.com/owner/repo/pull/123#issuecomment-12345"
    }
  ]
}
```

### Step 2: Handle No Comments Case

If both `threads` is empty AND `comments` is empty, display: "No unresolved review comments or discussion comments on PR #123."

### Step 3: Display Summary

Show the user what needs to be addressed in a markdown table with columns: #, Type, Location, Author, Summary

- **Type**: "Review" for review threads, "Discussion" for discussion comments
- **Location**: "src/foo.py:42" for review threads, "PR Discussion" for discussion comments

Example:

| #   | Type       | Location      | Author   | Summary                         |
| --- | ---------- | ------------- | -------- | ------------------------------- |
| 1   | Review     | src/foo.py:42 | reviewer | This should use LBYL pattern... |
| 2   | Discussion | PR Discussion | reviewer | Please also update the docs     |

### Step 4: Address Each Comment

Process all comments (both types) in the order shown in the summary table.

#### For Review Threads:

1. **Read the file** at the specified path and line to understand context
2. **Show the comment** with context showing thread number, file:line, author, comment body, and current code
3. **Make the fix** following the reviewer's feedback
4. **Explain what you changed** to the user
5. **Mark resolved** (see Step 5)

#### For Discussion Comments:

1. **Show the comment** with author and body
2. **Determine if action is needed**:
   - If it's a request (e.g., "Please update docs"), take the requested action
   - If it's a question, provide an answer or make clarifying changes
   - If it's just acknowledgment/thanks, note it and move on
3. **Take action if needed** (update docs, add tests, etc.)
4. **Explain what you did** to the user
5. **Mark addressed** (see Step 6)

### Step 5: Mark Review Thread Resolved

After addressing a review thread, resolve it with a resolution comment:

```bash
dot-agent run erk resolve-review-thread --thread-id "PRRT_abc123" --comment "Resolved via /erk:pr-address at $(date '+%Y-%m-%d %I:%M %p %Z')"
```

Report: "Resolved review thread on src/foo.py:42"

### Step 6: Mark Discussion Comment Addressed

After addressing a discussion comment, add a reaction:

```bash
dot-agent run erk add-reaction-to-comment --comment-id 12345
```

Report: "Added reaction to discussion comment from reviewer"

### Step 7: Continue or Complete

After resolving/addressing a comment:

- If more comments remain, continue to the next one
- If all comments addressed, display completion message with summary of changes and next steps (run tests, commit, push)

### Step 8: Handle Outdated Review Threads

If a review thread has `is_outdated: true`:

- The code has changed since the comment was made
- Show the user the comment but note it may no longer apply
- Ask if they want to: (1) Check if already fixed, (2) Resolve as outdated, or (3) Skip for now

### Error Handling

**No PR for branch:** Display error and suggest creating a PR with `gt create` or `gh pr create`

**GitHub API error:** Display error and suggest checking `gh auth status` and repository access
