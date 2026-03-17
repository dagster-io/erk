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

Fetch and classify all PR review feedback for the current branch's PR.

## Arguments

- `--pr <number>`: Target a specific PR by number (default: current branch's PR)
- `--include-resolved`: Include resolved threads (for reference)

Check `$ARGUMENTS` for flags.

## Critical Constraints

**DO NOT write Python scripts or any code files.** Classify the data using direct AI reasoning only. Writing code to process JSON is unnecessary and pollutes the filesystem.

## Steps

1. **Fetch PR info and all comments in a single call:**

   ```bash
   erk exec get-pr-feedback [--pr <number>] [--include-resolved]
   ```

   Pass `--pr <number>` if specified in `$ARGUMENTS`. Pass `--include-resolved` if specified in `$ARGUMENTS`.

   This returns JSON with `pr_number`, `pr_title`, `pr_url`, `reviews`, `review_threads`, and `discussion_comments`.

   **Also fetch file-level restructuring context:**

   ```bash
   TRUNK=$(erk exec detect-trunk-branch | jq -r '.trunk_branch')
   git diff --stat -M -C "$TRUNK"...HEAD
   ```

   This reveals renames, copies, and splits. Use this to inform pre-existing detection in step 2.

2. **Classify each comment** using the Comment Classification Model below.

3. **Group into batches** by complexity.

4. **Output structured JSON** (schema below).

## Comment Classification Model

For each comment, determine:

### PR-Level Reviews (`reviews` field)

The `reviews` array contains PR-level review submissions (not inline threads). Each has a `state` field:

- **CHANGES_REQUESTED** with non-empty `body`: Always actionable — add to `actionable_threads` with `type: "review_submission"` and `classification: "actionable"`. The reviewer explicitly requested changes.
- **CHANGES_REQUESTED** with empty `body`: Actionable (reviewer blocked the PR without comment) — add with `classification: "actionable"`.
- **APPROVED**: Informational only — increment `informational_count`, do NOT add to `actionable_threads`.
- **COMMENTED** with non-empty `body` containing a request/question: Actionable — add to `actionable_threads` with `type: "review_submission"`.
- **COMMENTED** with purely informational body (acknowledgment, FYI): Informational — increment `informational_count` only.

For `review_submission` items in `actionable_threads`, use `path: null` and `line: null` (PR-level, not inline). Use the review `id` as `thread_id`.

### Classification

Classification determines how the thread is presented to the user, not whether it appears.

- **Actionable**: Code changes requested, violations to fix, missing tests, documentation updates requested, bot suggestions to add tests, bot style/refactoring suggestions (optional/could)
- **Informational**: CI-generated style suggestions, acknowledgments on review threads

**Important:** Every unresolved review thread goes into `actionable_threads`, regardless of whether it's from a bot or human. The `classification` field distinguishes how the user should handle it.

Discussion comments that are purely informational (CI status updates, Graphite stack comments, PR description summaries) are still counted in `informational_count` and do NOT appear in `actionable_threads`.

### Pre-Existing Detection

For each thread in `actionable_threads`, determine the `pre_existing` field:

- **`pre_existing: true`** when ALL of:
  1. Author is a bot (`[bot]` suffix)
  2. PR involves file restructuring (renames, splits, moves visible in `git diff --stat -M -C`)
  3. The flagged pattern would have been equally flaggable in the original file location (generic code quality issue, not specific to the restructuring)

- **`pre_existing: false`** when ANY of:
  - Author is human
  - The issue is specifically caused by the restructuring (e.g., `__all__` in a new `__init__.py`, new import paths)
  - No restructuring detected in the PR

### Complexity

- `local`: Single line change at specified location
- `single_file`: Multiple changes in one file
- `cross_cutting`: Changes across multiple files
- `complex`: Architectural changes or related refactoring needed

### Batch Ordering

0. **Pre-Existing (Auto-Resolve)** (auto_proceed: true): Pre-existing issues in moved/restructured code (`pre_existing: true`)
1. **Local Fixes** (auto_proceed: true): Single-line changes
2. **Single-File** (auto_proceed: true): Multi-location in one file
3. **Cross-Cutting** (auto_proceed: false): Multiple files
4. **Complex** (auto_proceed: false): Architectural changes
5. **Informational** (auto_proceed: false): Threads classified as `informational` — user decides to act or dismiss

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
- `informational_count`: Count of informational items — discussion comments (CI status, Graphite stack) plus APPROVED reviews and informational COMMENTED reviews. Review threads and CHANGES_REQUESTED reviews always appear individually in `actionable_threads`

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
