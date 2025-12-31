---
description: Address PR review comments on current branch
---

# /erk:pr-address

## Description

Fetches unresolved PR review comments AND PR discussion comments from the current branch's PR and addresses them using holistic analysis with smart batching. Comments are grouped by complexity and relationship, then processed batch-by-batch with incremental commits and resolution.

## Usage

```bash
/erk:pr-address
/erk:pr-address --all    # Include resolved threads (for reference)
```

## Agent Instructions

### Phase 1: Fetch & Analyze

#### Step 1.1: Fetch All Comments

Run both CLI commands to get review comments AND discussion comments:

```bash
erk exec get-pr-review-comments
erk exec get-pr-discussion-comments
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

#### Step 1.2: Handle No Comments Case

If both `threads` is empty AND `comments` is empty, display: "No unresolved review comments or discussion comments on PR #123."

#### Step 1.3: Holistic Analysis

Analyze ALL comments together to understand relationships and complexity. Classify each comment:

- **Local fix**: Single comment → single location change (e.g., "Fix typo", "Add type annotation")
- **Multi-location in same file**: Single comment → changes in multiple spots in one file
- **Cross-cutting**: Single comment → changes across multiple files
- **Related comments**: Multiple comments that inform a single unified change (e.g., two comments about the same refactor)

#### Step 1.4: Batch and Prioritize

Group comments into batches ordered by complexity (simplest first):

| Batch | Complexity                 | Description                         | Example                                                   |
| ----- | -------------------------- | ----------------------------------- | --------------------------------------------------------- |
| 1     | Local fixes                | One file, one location per comment  | "Use LBYL pattern at line 42"                             |
| 2     | Single-file multi-location | One file, multiple locations        | "Rename this variable everywhere in this file"            |
| 3     | Cross-cutting              | Multiple files affected             | "Update all callers of this function"                     |
| 4     | Complex/Related            | Multiple comments inform one change | "Fold validate into prepare" + "Use union types for this" |

**Note**: Discussion comments that require doc updates or non-code changes go in Batch 3 (cross-cutting) since they often affect multiple files.

### Phase 2: Display Batched Plan

Show the user the batched execution plan:

```
## Execution Plan

### Batch 1: Local Fixes (3 comments)
| # | Location | Summary |
|---|----------|---------|
| 1 | foo.py:42 | Use LBYL pattern |
| 2 | bar.py:15 | Add type annotation |
| 3 | baz.py:99 | Fix typo |

### Batch 2: Single-File Changes (1 comment)
| # | Location | Summary |
|---|----------|---------|
| 4 | impl.py (multiple) | Rename `old_name` to `new_name` throughout |

### Batch 3: Cross-Cutting Changes (2 comments)
| # | Location | Summary |
|---|----------|---------|
| 5 | Multiple files | Update all callers of deprecated function |
| 6 | docs/ | Update documentation per reviewer request |

### Batch 4: Complex Changes (2 comments → 1 unified change)
| # | Location | Summary |
|---|----------|---------|
| 7 | impl.py:50 | Fold validate into prepare with union types |
| 8 | cmd.py:100 | (related to #7 - same refactor) |
```

**User confirmation flow:**

- **Batch 1-2 (simple)**: Auto-proceed without confirmation
- **Batch 3-4 (complex)**: Show plan and wait for user approval before executing

### Phase 3: Execute by Batch

For each batch, execute this workflow:

#### Step 3.1: Address All Comments in the Batch

For each comment in the batch:

**For Review Threads:**

1. Read the file at the specified path and line to understand context
2. Make the fix following the reviewer's feedback
3. Track the change for the batch commit message

**For Discussion Comments:**

1. Determine if action is needed:
   - If it's a request (e.g., "Please update docs"), take the requested action
   - If it's a question, provide an answer or make clarifying changes
   - If it's architectural feedback/suggestion, investigate the codebase to understand implications
   - If it's just acknowledgment/thanks, note it and move on
2. **Investigate the codebase** when the comment requires understanding existing code:
   - Search for relevant patterns, existing implementations, or related code
   - Note any interesting findings that inform your decision
   - Record these findings - they become permanent documentation in the reply
3. Take action if needed

**For Outdated Review Threads** (`is_outdated: true`):

- The code has changed since the comment was made
- Check if the issue is already fixed in current code
- If fixed, resolve as "Already addressed by subsequent changes"
- If not fixed, apply the fix as normal

#### Step 3.2: Run CI Checks

After making all changes in the batch:

```bash
# Run relevant CI checks for changed files
# (This may vary by project - use project's test commands)
```

If CI fails, fix the issues before proceeding.

#### Step 3.3: Commit the Batch

Create a single commit for all changes in the batch:

```bash
git add <changed files>
git commit -m "Address PR review comments (batch N/M)

- <summary of comment 1>
- <summary of comment 2>
..."
```

#### Step 3.4: Resolve All Threads in the Batch

After committing, resolve each review thread and mark each discussion comment:

**For Review Threads:**

```bash
erk exec resolve-review-thread --thread-id "PRRT_abc123" --comment "Resolved via /erk:pr-address at $(date '+%Y-%m-%d %I:%M %p %Z')"
```

**For Discussion Comments:**

Post a substantive reply that quotes the original comment and explains what action was taken:

```bash
erk exec reply-to-discussion-comment --comment-id 12345 --reply "**Action taken:** <substantive summary>"
```

**Writing substantive replies:**

The `--reply` argument should include meaningful findings, not just generic acknowledgments:

❌ **Bad (too generic):**

```bash
--reply "**Action taken:** Noted for future consideration."
--reply "**Action taken:** Added to backlog."
```

✅ **Good (includes investigation findings):**

```bash
--reply "**Action taken:** Investigated the gateway pattern suggestion. The current artifact sync implementation uses direct function calls rather than a gateway ABC pattern. This is intentional - artifact operations are file-based and don't require the testability benefits of gateway injection that external APIs need. Filed as backlog consideration for if we add remote artifact fetching."
```

✅ **Good (explains why no code change):**

```bash
--reply "**Action taken:** Reviewed the suggestion to add caching here. After checking the call sites, this function is only called once per CLI invocation (in main.py:45), so caching wouldn't provide measurable benefit. The perceived slowness is actually from the subprocess call inside, not repeated invocations."
```

The reply becomes a permanent record in the PR - make it useful for future readers who wonder "what happened with this feedback?"

#### Step 3.5: Report Progress

After completing the batch, report:

```
## Batch N Complete

Addressed:
- ✅ foo.py:42 - Used LBYL pattern
- ✅ bar.py:15 - Added type annotation

Committed: abc1234 "Address PR review comments (batch 1/3)"

Resolved threads: 2
Remaining batches: 2
```

Then proceed to the next batch.

### Phase 4: Final Verification

After all batches complete:

#### Step 4.1: Verify All Threads Resolved

Re-fetch comments to confirm nothing was missed:

```bash
erk exec get-pr-review-comments
erk exec get-pr-discussion-comments
```

If any unresolved threads remain, report them.

#### Step 4.2: Report Summary

```
## All PR Comments Addressed

Total comments: 8
Batches: 4
Commits: 4

All review threads resolved.
All discussion comments marked with reaction.

Next steps:
1. Push changes: `git push`
2. Wait for CI to pass
3. Request re-review if needed
```

#### Step 4.3: Handle Any Skipped Comments

If the user explicitly skipped any comments during the process, list them:

```
## Skipped Comments (user choice)
- #5: src/legacy.py:100 - "Refactor this module" (user deferred)
```

### Error Handling

**No PR for branch:** Display error and suggest creating a PR with `gt create` or `gh pr create`

**GitHub API error:** Display error and suggest checking `gh auth status` and repository access

**CI failure during batch:** Stop, display the failure, and let the user decide whether to fix and continue or abort
