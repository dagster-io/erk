---
name: pr-feedback-classifier
description: >
  Fetches and classifies PR review feedback with context isolation.
  Returns structured JSON with thread IDs for deterministic resolution.
  Use when analyzing PR comments before addressing them.
argument-hint: "[--pr <number>] [--include-resolved]"
context: fork
agent: general-purpose
model: sonnet
---

# PR Feedback Classifier

Classify PR review feedback by filling in semantic fields from mechanical CLI output.

## Steps

1. **Run mechanical classification:**

   ```bash
   erk exec classify-pr-feedback [--pr <number>] [--include-resolved]
   ```

   Pass `--pr <number>` if specified in `$ARGUMENTS`. Pass `--include-resolved` if specified in `$ARGUMENTS`.

   This returns JSON with mechanically pre-classified items:
   - **review_submissions**: PR-level reviews (classification: "actionable" | "informational" | "needs_llm")
   - **review_threads**: Inline review threads (pre_existing_candidate flag set for bot + restructured)
   - **discussion_comments**: Discussion comments (classification: "informational" | "needs_llm")
   - **restructured_files**: Renamed/moved files detected by git diff
   - **mechanical_informational_count**: Items already filtered as informational by CLI

2. **Fill in semantic fields for items that need LLM judgment:**

   For each item:
   - **review_submissions with classification "needs_llm"**: Determine if actionable or informational
   - **All actionable items** (review_submissions, review_threads, discussion_comments): Write `action_summary` (brief description of requested change)
   - **All actionable items**: Assign `complexity` (local/single_file/cross_cutting/complex)
   - **Threads with pre_existing_candidate=true**: Confirm if truly pre-existing (generic code quality issue, not specific to restructuring). If confirmed, set complexity to "pre_existing"

3. **Construct final JSON output with batches grouped by complexity.**

## Complexity Levels

- **local**: Single line change at specified location
- **single_file**: Multiple changes in one file
- **cross_cutting**: Changes across multiple files
- **complex**: Architectural changes
- **pre_existing**: Bot comment on moved/restructured code (auto-resolve candidate)

## Batch Ordering

0. Pre-Existing (Auto-Resolve) (auto_proceed: true)
1. Local Fixes (auto_proceed: true)
2. Single-File (auto_proceed: true)
3. Cross-Cutting (auto_proceed: false)
4. Complex (auto_proceed: false)
5. Informational (auto_proceed: false)

## Output Format

Output ONLY the following JSON (no prose, no markdown, no code fences):

```json
{
  "success": true,
  "pr_number": 5944,
  "pr_title": "Feature: Add new API endpoint",
  "pr_url": "https://github.com/owner/repo/pull/5944",
  "actionable_threads": [
    {
      "thread_id": "PRR_kwDOPxC3hc5q73Nd",
      "type": "review_submission",
      "path": null,
      "line": null,
      "is_outdated": false,
      "classification": "actionable",
      "pre_existing": false,
      "action_summary": "Reviewer requested changes: fix the authentication flow",
      "complexity": "cross_cutting",
      "original_comment": "The authentication flow is broken for edge cases..."
    },
    {
      "thread_id": "PRRT_kwDOPxC3hc5q73Ne",
      "type": "review",
      "path": "src/api.py",
      "line": 42,
      "is_outdated": false,
      "classification": "actionable",
      "pre_existing": false,
      "action_summary": "Add integration tests for new endpoint",
      "complexity": "local",
      "original_comment": "This needs integration tests"
    },
    {
      "thread_id": "PRRT_kwDOPxC3hc5q73Nf",
      "type": "review",
      "path": "src/api.py",
      "line": 55,
      "is_outdated": false,
      "classification": "actionable",
      "pre_existing": true,
      "action_summary": "Bot suggestion: add unit tests for error handling paths",
      "complexity": "pre_existing",
      "original_comment": "Consider adding unit tests for the error handling paths in this endpoint"
    }
  ],
  "discussion_actions": [
    {
      "comment_id": 12345678,
      "action_summary": "Update API documentation",
      "complexity": "cross_cutting",
      "original_comment": "Please update the docs to reflect..."
    }
  ],
  "informational_count": 12,
  "batches": [
    {
      "name": "Pre-Existing (Auto-Resolve)",
      "complexity": "pre_existing",
      "auto_proceed": true,
      "item_indices": [1]
    },
    {
      "name": "Local Fixes",
      "complexity": "local",
      "auto_proceed": true,
      "item_indices": [0]
    },
    {
      "name": "Single-File",
      "complexity": "single_file",
      "auto_proceed": true,
      "item_indices": []
    },
    {
      "name": "Cross-Cutting",
      "complexity": "cross_cutting",
      "auto_proceed": false,
      "item_indices": []
    }
  ],
  "error": null
}
```

**Field notes:**

- `thread_id`: The ID needed for `erk exec resolve-review-thread`
- `comment_id`: The ID needed for `erk exec reply-to-discussion-comment`
- `type`: `"review"` for inline thread comments, `"review_submission"` for PR-level review submissions, `"discussion"` for discussion actions
- `classification`: `"actionable"` or `"informational"` — determines how the user handles the thread
- `pre_existing`: `true` if the issue existed before this PR (bot comment on moved/restructured code). Pre-existing threads use `complexity: "pre_existing"` and are placed in the first batch for auto-resolution
- `item_indices`: References into `actionable_threads` (type=review or review_submission) or `discussion_actions` (type=discussion)
- `original_comment`: First 200 characters of the comment text
- `informational_count`: Count of informational items — includes items filtered by CLI plus any you classify as informational

## Error Case

If no PR exists for the branch or API fails:

```json
{
  "success": false,
  "pr_number": null,
  "pr_title": null,
  "pr_url": null,
  "actionable_threads": [],
  "discussion_actions": [],
  "informational_count": 0,
  "batches": [],
  "error": "No PR found for branch feature-xyz"
}
```

## No Comments Case

If PR exists but has no unresolved comments:

```json
{
  "success": true,
  "pr_number": 5944,
  "pr_title": "Feature: Add new API endpoint",
  "pr_url": "https://github.com/owner/repo/pull/5944",
  "actionable_threads": [],
  "discussion_actions": [],
  "informational_count": 0,
  "batches": [],
  "error": null
}
```
