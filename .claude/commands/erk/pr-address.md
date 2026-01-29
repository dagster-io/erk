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

### Phase 0: Plan Review Detection

Before classifying feedback, determine if this is a plan review PR:

1. Get the current PR number: `gh pr view --json number -q .number`
2. Check if the PR has the `plan-review` label: `gh pr view --json labels -q '.labels[].name'` and check for `plan-review` in the output
3. If YES: extract the plan issue number from the PR body (which contains `**Plan Issue:** #NNN`): `gh pr view --json body -q .body` and parse the issue number from the `**Plan Issue:** #NNN` line. Enter **Plan Review Mode** (see [Plan Review Mode](#plan-review-mode) below). Skip normal Phases 1-4.
4. If NO: proceed with standard code review flow (Phase 1)

### Phase 1: Classify Feedback

Invoke the pr-feedback-classifier skill to fetch and classify all PR feedback with context isolation:

```
/pr-feedback-classifier [--include-resolved if --all was specified]
```

Parse the JSON response. The skill returns:

- `success`: Whether the operation succeeded
- `pr_number`, `pr_title`, `pr_url`: PR metadata
- `actionable_threads`: Array with `thread_id`, `path`, `line`, `action_summary`, `complexity`
- `discussion_actions`: Array with `comment_id`, `action_summary`, `complexity`
- `batches`: Execution order with `item_indices` referencing the arrays above
- `error`: Error message if `success` is false

**Handle errors**: If `success` is false, display the error and exit.

**Handle no comments**: If both `actionable_threads` and `discussion_actions` are empty, display: "No unresolved review comments or discussion comments on PR #NNN." and exit.

### Phase 2: Display Batched Plan

Show the user the batched execution plan from the classifier output:

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

### Batch 4: Complex Changes (2 comments -> 1 unified change)
| # | Location | Summary |
|---|----------|---------|
| 7 | impl.py:50 | Fold validate into prepare with union types |
| 8 | cmd.py:100 | (related to #7 - same refactor) |
```

**User confirmation flow:**

- **Batch 1-2 (simple)**: Auto-proceed without confirmation
- **Batch 3-4 (complex)**: Show plan and wait for user approval before executing

### Phase 3: Execute by Batch

For each batch, execute this workflow using the thread IDs from the classifier JSON:

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
   - If already fixed -> Proceed directly to Step 4 to resolve the thread
   - If not fixed -> Apply the fix, then proceed to Step 4

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

**This step is NOT optional.** Every thread must be resolved using the thread IDs from the classifier JSON.

After committing, resolve each review thread and mark each discussion comment.

**For Review Threads** - use `erk exec resolve-review-thread` with the `thread_id` from the JSON (see `pr-operations` skill for examples).

**For Discussion Comments** - use `erk exec reply-to-discussion-comment` with the `comment_id` from the JSON, with a substantive reply that quotes the original comment and explains what action was taken.

#### Step 5: Report Progress

After completing the batch, report:

```
## Batch N Complete

Addressed:
- foo.py:42 - Used LBYL pattern
- bar.py:15 - Added type annotation

Committed: abc1234 "Address PR review comments (batch 1/3)"

Resolved threads: 2
Remaining batches: 2
```

Then proceed to the next batch.

### Phase 4: Final Verification

After all batches complete, re-invoke the classifier to verify all threads are resolved:

```
/pr-feedback-classifier
```

If `actionable_threads` or `discussion_actions` are non-empty, warn about remaining unresolved items.

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

---

## Plan Review Mode

When Phase 0 detects the `plan-review` label on the current PR, the entire flow switches to plan review mode. This mode edits plan text instead of source code.

### Key Differences: Plan Mode vs Code Mode

| Aspect            | Code Mode                    | Plan Mode                              |
| ----------------- | ---------------------------- | -------------------------------------- |
| File edited       | Source code files            | `PLAN-REVIEW-{issue}.md`               |
| What changes      | Code implementation          | Plan text/structure                    |
| CI checks         | Run tests                    | Skip (no code to test)                 |
| Extra step        | None                         | `plan-update-issue` to sync plan issue |
| Commit message    | "Address PR review comments" | "Incorporate review feedback"          |
| Thread resolution | What code change was made    | How plan was updated                   |

### Plan Review Phase 0.5: Save Current Branch

Before processing feedback, record the current branch so we can return to it later:

```bash
git branch --show-current
```

Store the result as `ORIGINAL_BRANCH`.

### Plan Review Phase 1: Classify Feedback

Same as standard Phase 1 — invoke `/pr-feedback-classifier` to fetch and classify all PR feedback.

### Plan Review Phase 2: Display Batched Plan

Same as standard Phase 2, but note at the top of the display:

```
**Plan Review Mode** — changes apply to plan text, not source code.
```

### Plan Review Phase 3: Execute by Batch (Plan Mode)

For each batch:

#### Step 1: Edit the Plan

1. Read `PLAN-REVIEW-{issue}.md` from the repo root
2. For each comment in the batch, incorporate reviewer feedback by editing the plan markdown text
   - Restructure sections, add detail, clarify language, update design decisions as requested
   - If feedback applies to implementation (not the plan itself), add a note to the relevant plan section rather than making structural changes
3. Write the updated `PLAN-REVIEW-{issue}.md`

#### Step 2: Commit and Push

```bash
git add PLAN-REVIEW-{issue}.md
git commit -m "Incorporate review feedback (batch N/M)

- <summary of change 1>
- <summary of change 2>
..."
git push
```

#### Step 3: Sync Plan to GitHub Issue

```bash
erk exec plan-update-issue --issue-number {issue} --plan-path PLAN-REVIEW-{issue}.md
```

#### Step 4: Resolve Threads

Resolve each thread using the appropriate command (see `pr-operations` skill):

**For review threads** (`resolve-review-thread`):

Use a message like:

```
Incorporated feedback into plan. Updated the relevant section in PLAN-REVIEW-{issue}.md.

Summary of change: {brief description of how the plan text was modified}
```

**For discussion comments** (`reply-to-discussion-comment`):

Use a message like:

```
Addressed in plan update. {description of how feedback was incorporated or why it was noted for implementation phase}
```

**For feedback that applies to implementation, not the plan itself:**

Use a message like:

```
Noted for implementation phase. This feedback applies to the code implementation rather than the plan structure — it will be addressed when implementing the plan.
```

#### Step 5: Report Progress

Same as standard Phase 3 Step 5 — report what was addressed and what remains.

### Plan Review Phase 4: Final Verification

Same as standard Phase 4 — re-invoke the classifier to verify all threads are resolved. Report final summary.

### Return to Original Branch

After all batches are complete and pushed:

1. Switch back to the branch saved in Phase 0.5: `git checkout <ORIGINAL_BRANCH>`
2. The plan-review branch work is complete — the user should not remain on it.
