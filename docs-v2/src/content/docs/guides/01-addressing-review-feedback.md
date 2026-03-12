---
title: Addressing review feedback
description: Resolve PR review comments using the pr-address workflow
---

After CI reviews post comments on your PR, use `/erk:pr-address` to classify, batch, and resolve them. The workflow handles everything from one-line fixes to cross-cutting refactors, committing changes and resolving threads as it goes.

## Running pr-address

```bash
/erk:pr-address                  # Address comments on current branch's PR
/erk:pr-address --pr 6631        # Target a specific PR
/erk:pr-preview-address           # Preview what pr-address would do (read-only)
```

The preview command shows the classified comments and execution plan without making changes. Use it to see what you're about to address before committing to the full workflow.

## How classification works

A Haiku subagent fetches every unresolved comment — both inline review threads and PR discussion comments — and classifies each one:

- **Actionable**: Code changes needed (style violations, missing tests, requested refactors).
- **Informational**: Optional suggestions the reviewer flagged but left to your judgment.
- **Pre-existing**: Issues in code that was moved or restructured, not newly introduced. Detected by cross-referencing bot comments against `git diff --stat -M -C` rename/copy data.

Each comment also gets a complexity rating: `local` (single line), `single_file` (multiple locations in one file), `cross_cutting` (spans files), or `complex` (architectural changes).

## The batching model

Comments are grouped into ordered batches by complexity:

| Batch | Type | Behavior |
|-------|------|----------|
| 0 | Pre-existing | Auto-resolved with a standard reply. No code changes. |
| 1 | Local fixes | Auto-proceeds. Single-line changes at specified locations. |
| 2 | Single-file | Auto-proceeds. Multiple changes within one file. |
| 3 | Cross-cutting | Pauses for user approval. Changes span multiple files. |
| 4 | Complex | Pauses for user approval. Architectural or related refactors. |
| 5 | Informational | User decides per thread: act on the suggestion or dismiss it. |

Batches 0-2 execute without interruption. Batches 3-4 show you the plan and wait for confirmation. Batch 5 presents each informational thread individually.

## What happens in each batch

For each batch, the workflow:

1. **Addresses every comment** — reads the relevant code, makes the fix, tracks what changed.
2. **Runs CI checks** — catches regressions before committing.
3. **Commits the batch** — one commit per batch with a summary of addressed comments.
4. **Resolves threads** — marks each review thread as resolved via `erk exec resolve-review-threads` and replies to discussion comments.
5. **Reports progress** — shows what was fixed and how many batches remain.

If a comment turns out to be a false positive (the bot misread the code or the pattern already exists), the workflow replies with an explanation referencing the specific lines and resolves the thread without code changes.

## After all batches complete

The workflow re-runs the classifier to verify all threads are resolved, then:

1. Updates the PR title and description to reflect the full scope of changes.
2. Uploads the session for cross-machine learning.
3. Prints push instructions — `gt submit` for Graphite repos or `git push` for plain git.

If any threads remain unresolved, you get a warning listing the stragglers.

## Related

- [Code reviews](/concepts/01-code-reviews/) — how the two-phase review system works
- [Creating a review](/guides/02-creating-a-review/) — add a new automated review
