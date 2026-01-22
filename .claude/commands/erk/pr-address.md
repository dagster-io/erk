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

## Prerequisite

**Load the `pr-operations` skill first** for complete command reference and common mistake patterns.

## Agent Instructions

> **Prerequisite**: Load `pr-operations` skill first for command reference.

> **CRITICAL: Use ONLY `erk exec` Commands**
>
> See `pr-operations` skill for the complete command reference. Never use raw `gh api` calls for thread operations.

### Phase 1: Fetch & Analyze

#### Step 1: Fetch All Comments

Run both CLI commands to get review comments AND discussion comments:

```bash
erk exec get-pr-review-comments
erk exec get-pr-discussion-comments
```

#### Step 2: Handle No Comments Case

If both `threads` is empty AND `comments` is empty, display: "No unresolved review comments or discussion comments on PR #123."

#### Step 3: Holistic Analysis

Analyze ALL comments together to understand relationships and complexity.

> See `pr-operations` skill for the **Comment Classification Model** (complexity categories and batch ordering).

#### Step 4: Batch and Prioritize

Group comments into batches ordered by complexity (simplest first). See `pr-operations` skill for the batch ordering table.

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

#### Step 1: Address All Comments in the Batch

For each comment in the batch:

**For Review Threads:**

1. Read the file to understand context:
   - If `line` is specified: Read around that line number
   - If `line` is null (outdated thread): Read the entire file or search for relevant code mentioned in the comment
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

**Handling False Positives from Automated Reviewers:**

Automated review bots (like `dignified-python-review`, linters, or security scanners) can flag false positives. Before making code changes:

1. **Read the flagged code carefully** - understand what the bot is complaining about
2. **Verify if it's a false positive** by checking:
   - Is the pattern the bot wants already implemented nearby? (e.g., LBYL check already exists on a preceding line)
   - Is the bot misunderstanding the code structure?
   - Is the bot applying a rule that doesn't fit this specific context?
3. **If it's a false positive**, do NOT make unnecessary code changes. Instead:
   - Reply to the comment explaining why it's a false positive
   - Reference specific line numbers where the correct pattern already exists
   - Resolve the thread

**For Outdated Review Threads** (`is_outdated: true`):

Outdated threads have `line: null` because the code has changed since the comment was made.

1. **Read the file** at the path (ignore line number - search for relevant code)
2. **Check if the issue is already fixed** in the current code
3. **Take action:**
   - If already fixed → Proceed directly to Step 4 to resolve the thread
   - If not fixed → Apply the fix, then proceed to Step 4

**IMPORTANT**: Outdated threads MUST still be resolved via `erk exec resolve-review-thread`.
Do not skip resolution just because no code change was needed.

#### Step 2: Run CI Checks

After making all changes in the batch:

```bash
# Run relevant CI checks for changed files
# (This may vary by project - use project's test commands)
```

If CI fails, fix the issues before proceeding.

#### Step 3: Commit the Batch

Create a single commit for all changes in the batch:

```bash
git add <changed files>
git commit -m "Address PR review comments (batch N/M)

- <summary of comment 1>
- <summary of comment 2>
..."
```

#### Step 4: Resolve All Threads in the Batch (MANDATORY)

**This step is NOT optional.** Every thread must be resolved using `erk exec resolve-review-thread`.

After committing, resolve each review thread and mark each discussion comment.

**For Review Threads** - use `erk exec resolve-review-thread` (see `pr-operations` skill for examples).

**For Discussion Comments** - use `erk exec reply-to-discussion-comment` with a substantive reply that quotes the original comment and explains what action was taken.

#### Step 5: Report Progress

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

#### Step 1: Verify All Threads Resolved

Re-fetch comments to confirm nothing was missed:

```bash
erk exec get-pr-review-comments
erk exec get-pr-discussion-comments
```

If any unresolved threads remain, report them.

#### Step 2: Report Summary

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

#### Step 3: Handle Any Skipped Comments

If the user explicitly skipped any comments during the process, list them:

```
## Skipped Comments (user choice)
- #5: src/legacy.py:100 - "Refactor this module" (user deferred)
```

### Common Mistakes

See `pr-operations` skill for the complete table of common mistakes and correct approaches.

### Error Handling

**No PR for branch:** Display error and suggest creating a PR with `gt create` or `gh pr create`

**GitHub API error:** Display error and suggest checking `gh auth status` and repository access

**CI failure during batch:** Stop, display the failure, and let the user decide whether to fix and continue or abort
