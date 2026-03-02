---
title: Pre-Existing Bot Comment Detection
read_when:
  - "handling bot review comments on code-move PRs"
  - "understanding auto-resolution of pre-existing issues"
  - "working with pr-feedback-classifier pre_existing field"
tripwires:
  - action: "manually resolving bot comments on restructured code without checking pre_existing"
    warning: "Use the pre_existing classification from pr-feedback-classifier. Pre-existing issues in moved code are auto-resolved in Batch 0 with no code changes."
---

# Pre-Existing Bot Comment Detection

Code-move PRs (file renames, splits, restructuring) trigger bot review comments on patterns that existed before the restructuring. The `pr-feedback-classifier` skill detects these pre-existing issues and the `pr-address` command auto-resolves them without code changes.

## Problem

When files are renamed, split, or moved, CI bots re-scan the "new" files and flag patterns (missing type annotations, style violations) that were present in the original location. These comments are noise — the PR author didn't introduce the issues.

## Detection Logic

A thread is marked `pre_existing: true` when ALL three conditions hold:

1. **Bot author**: Comment author has `[bot]` suffix
2. **File restructuring in diff**: `git diff --stat -M -C main...HEAD` shows renames, copies, or splits
3. **Pattern was flaggable in original location**: The issue is a generic code quality concern (not specific to the restructuring itself)

A thread is `pre_existing: false` when ANY of:

- Author is human
- The issue is specifically caused by the restructuring (e.g., `__all__` in a new `__init__.py`, new import paths)
- No restructuring detected in the PR

<!-- Source: .claude/skills/pr-feedback-classifier/SKILL.md, Pre-Existing Detection section -->

## Batch 0: Auto-Resolution

Pre-existing threads are grouped into Batch 0 with `complexity: "pre_existing"` and `auto_proceed: true`. The `pr-address` command handles them with no code changes:

1. Resolves all threads via `erk exec resolve-review-threads` with a standard comment: "Pre-existing issue — this code was moved/restructured, not newly introduced."
2. Reports progress and continues to the next batch
3. Skips the normal implement-test-commit cycle entirely

<!-- Source: .claude/commands/erk/pr-address.md, Pre-Existing Batch section -->

## Preview Display

The `pr-preview-address` command shows pre-existing items in a dedicated section:

```
### Pre-Existing Items (Auto-Resolve) (N total)

| # | Type | Location | Summary |
|---|------|----------|---------|
| 1 | review | old_module.py:30 | Bot: use LBYL pattern (pre-existing in moved code) |
```

Statistics include a separate count: "Pre-existing items (auto-resolve): N"

## Batch Ordering

| Batch | Name                        | auto_proceed | Code Changes   |
| ----- | --------------------------- | ------------ | -------------- |
| 0     | Pre-Existing (Auto-Resolve) | true         | None           |
| 1     | Local Fixes                 | true         | Single-line    |
| 2     | Single-File                 | true         | Multi-location |
| 3     | Cross-Cutting               | false        | Multiple files |
| 4     | Complex                     | false        | Architectural  |
| 5     | Informational               | false        | User decides   |

## Related Documentation

- [PR Feedback Classification](feedback-classification.md) — Category taxonomy for all PR comments
- [Automated Review Handling](automated-review-handling.md) — Broader review automation patterns
