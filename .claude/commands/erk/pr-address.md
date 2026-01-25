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

### Phase 1: Fetch & Analyze via Task

Use the Task tool to fetch and classify PR feedback with context isolation. The Task returns **prose + structured JSON** so you can act on specific thread IDs.

**Determine flags**: If `--all` was specified in the command, include `--include-resolved` in the fetch command.

````
Task(
  subagent_type: "general-purpose",
  model: "sonnet",
  description: "Fetch PR review feedback",
  prompt: |
    Fetch and classify PR review feedback for the current branch's PR.

    ## Steps
    1. Get the current branch: `git rev-parse --abbrev-ref HEAD`
    2. Get the PR number for this branch: `gh pr view --json number,title -q '{number: .number, title: .title}'`
    3. Run: `erk exec get-pr-review-comments [--include-resolved if --all flag]`
    4. Run: `erk exec get-pr-discussion-comments`
    5. Parse and classify the JSON outputs

    ## Classification

    > See `pr-operations` skill for the **Comment Classification Model**.

    For each comment, determine:
    - **Actionable**: Code changes requested, violations to fix, missing tests
    - **Informational**: Bot status updates, CI results, Graphite stack comments
    - **Resolved**: Threads with clarifying follow-up (e.g., "Clarification: this is compliant")

    Group actionable items by complexity:
    - **Local Fix**: Single line change
    - **Single-File**: Multiple changes in one file
    - **Cross-Cutting**: Changes across multiple files
    - **Complex**: Architectural changes or related refactoring

    ## Output Format

    ### Summary
    PR #NNNN "Title": N actionable items, N informational comments skipped.

    ### Actionable Items
    | # | Thread ID | Type | Path | Line | Issue | Complexity |
    |---|-----------|------|------|------|-------|------------|
    | 1 | PRRT_xxx | review | abc.py | 8 | Missing integration tests | Local |
    | 2 | 12345678 | discussion | - | - | Update docs | Cross-cutting |

    ### Batched Execution Plan
    **Batch 1: Local Fixes (auto-proceed)**
    - Item #1: abc.py:8 - Missing tests

    **Batch 2: Cross-Cutting (user confirmation)**
    - Item #2: Update docs

    ### Structured Data
    ```json
    {
      "pr_number": 5944,
      "pr_title": "BeadsGateway ABC with list_issues Method",
      "actionable_threads": [
        {"thread_id": "PRRT_kwDOPxC3hc5q73Ne", "type": "review", "path": "abc.py", "line": 8, "action": "Add integration tests", "complexity": "local", "is_outdated": false}
      ],
      "discussion_actions": [
        {"comment_id": 12345678, "action": "Update documentation"}
      ],
      "informational_count": 12,
      "batches": [
        {"name": "Local Fixes", "auto_proceed": true, "items": [1]},
        {"name": "Cross-Cutting", "auto_proceed": false, "items": [2]}
      ]
    }
    ```

    If no comments found, output:
    ```json
    {
      "pr_number": NNNN,
      "pr_title": "...",
      "actionable_threads": [],
      "discussion_actions": [],
      "informational_count": 0,
      "batches": []
    }
    ```
)
````

**Parse the structured JSON** from the Task output. Extract:

- `pr_number`, `pr_title` for reference
- `actionable_threads` array with thread IDs
- `discussion_actions` array with comment IDs
- `batches` array for execution order

**Handle No Comments Case**: If both `actionable_threads` and `discussion_actions` are empty, display: "No unresolved review comments or discussion comments on PR #NNN." and exit.

### Phase 2: Display Batched Plan

Show the user the batched execution plan from the Task output:

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

For each batch, execute this workflow using the thread IDs from the structured JSON:

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

**This step is NOT optional.** Every thread must be resolved using the thread IDs from the structured JSON.

After committing, resolve each review thread and mark each discussion comment.

**For Review Threads** - use `erk exec resolve-review-thread` with the `thread_id` from the JSON (see `pr-operations` skill for examples).

**For Discussion Comments** - use `erk exec reply-to-discussion-comment` with the `comment_id` from the JSON, with a substantive reply that quotes the original comment and explains what action was taken.

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

### Phase 4: Final Verification via Task

After all batches complete, use a Task to verify all threads are resolved:

```
Task(
  subagent_type: "general-purpose",
  model: "haiku",
  description: "Verify PR threads resolved",
  prompt: |
    Verify all PR review threads have been resolved.

    ## Steps
    1. Run: `erk exec get-pr-review-comments`
    2. Run: `erk exec get-pr-discussion-comments`
    3. Count any remaining unresolved items

    ## Output Format

    ### Verification Summary
    [One paragraph: total addressed, any remaining unresolved]

    If all resolved: "All N review threads and M discussion comments have been addressed."
    If any remain: "Warning: N threads remain unresolved: [list thread IDs]"
)
```

Display the verification summary.

#### Report Final Summary

```
## All PR Comments Addressed

Total comments: 8
Batches: 4
Commits: 4

All review threads resolved.
All discussion comments marked with reaction.

Next steps:
1. Push changes: `git push`
   - If push is rejected (non-fast-forward): Run `/erk:sync-divergence` to resolve. Do NOT use `git pull --rebase`.
2. Wait for CI to pass
3. Request re-review if needed
```

#### Handle Any Skipped Comments

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
