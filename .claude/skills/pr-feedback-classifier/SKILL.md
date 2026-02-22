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

## Steps

1. **Get current branch and PR info using REST API** (avoids GraphQL rate limits):
   - **If `--pr <number>` specified in `$ARGUMENTS`**:

     ```bash
     erk exec get-pr-view <number>
     ```

   - **If `--pr` not specified** (use current branch):
     ```bash
     erk exec get-pr-view
     ```

   Parse the JSON output to extract `number`, `title`, and `url`.

2. **Fetch all comments:**

   ```bash
   # If --include-resolved in $ARGUMENTS:
   erk exec get-pr-review-comments [--pr <number>] --include-resolved
   # Otherwise:
   erk exec get-pr-review-comments [--pr <number>]

   erk exec get-pr-discussion-comments [--pr <number>]
   ```

   Note: Pass `--pr <number>` to both exec commands when specified in `$ARGUMENTS`.

3. **Classify each comment** using the Comment Classification Model below.

4. **Group into batches** by complexity.

5. **Output structured JSON** (schema below).

## Comment Classification Model

For each comment, determine:

### Classification

Classification determines how the thread is presented to the user, not whether it appears.

- **Actionable**: Code changes requested, violations to fix, missing tests, documentation updates requested, bot suggestions to add tests, bot style/refactoring suggestions (optional/could)
- **Informational**: CI-generated style suggestions, acknowledgments on review threads

**Important:** Every unresolved review thread goes into `actionable_threads`, regardless of whether it's from a bot or human. The `classification` field distinguishes how the user should handle it.

Discussion comments that are purely informational (CI status updates, Graphite stack comments, PR description summaries) are still counted in `informational_count` and do NOT appear in `actionable_threads`.

### Complexity

- `local`: Single line change at specified location
- `single_file`: Multiple changes in one file
- `cross_cutting`: Changes across multiple files
- `complex`: Architectural changes or related refactoring needed

### Batch Ordering

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
      "thread_id": "PRRT_kwDOPxC3hc5q73Ne",
      "type": "review",
      "path": "src/api.py",
      "line": 42,
      "is_outdated": false,
      "classification": "actionable",
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
      "action_summary": "Bot suggestion: add unit tests for error handling paths",
      "complexity": "single_file",
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
      "name": "Local Fixes",
      "complexity": "local",
      "auto_proceed": true,
      "item_indices": [0]
    },
    {
      "name": "Single-File",
      "complexity": "single_file",
      "auto_proceed": true,
      "item_indices": [1]
    },
    {
      "name": "Cross-Cutting",
      "complexity": "cross_cutting",
      "auto_proceed": false,
      "item_indices": [0]
    }
  ],
  "error": null
}
```

**Field notes:**

- `thread_id`: The ID needed for `erk exec resolve-review-thread`
- `comment_id`: The ID needed for `erk exec reply-to-discussion-comment`
- `classification`: `"actionable"` or `"informational"` — determines how the user handles the thread
- `item_indices`: References into `actionable_threads` (type=review) or `discussion_actions` (type=discussion)
- `original_comment`: First 200 characters of the comment text
- `informational_count`: Count of informational **discussion** comments only (CI status, Graphite stack). Review threads always appear individually in `actionable_threads` with a `classification` field

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
