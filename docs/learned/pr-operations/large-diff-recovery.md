---
title: Large Diff PR Submission Recovery
read_when:
  - "debugging PR submission failures with large diffs"
  - "modifying diff extraction for PR descriptions"
  - "understanding why local git diff is used instead of GitHub API"
tripwires:
  - action: "using GitHub API to fetch PR diffs"
    warning: "GitHub returns HTTP 406 for diffs exceeding ~20k lines. Use local git diff instead via get_diff_to_branch() for reliable extraction."
---

# Large Diff PR Submission Recovery

PR submission extracts diffs for description generation. GitHub's API has size limits that cause failures on large PRs. The recovery pattern uses local git diff as the primary extraction method.

## The Problem

<!-- Source: packages/erk-shared/src/erk_shared/gateway/pr/diff_extraction.py:96-97 -->

GitHub's diff API returns HTTP 406 (Not Acceptable) for diffs exceeding approximately 20,000 lines. This means `gh pr diff` and the REST API endpoint both fail silently or with unhelpful errors for large PRs.

## The Solution: Local Git Diff

Instead of calling the GitHub API, diff extraction uses local git operations:

```
git diff <base-branch>...HEAD
```

This bypasses GitHub's size limits entirely since the operation happens locally. The `execute_diff_extraction()` function in `diff_extraction.py` implements this as a streaming pipeline with progress events.

## Truncation Strategy

<!-- Source: packages/erk-shared/src/erk_shared/gateway/gt/prompts.py:1-44 -->

Even local diffs can be too large for LLM context windows. The `truncate_diff()` function handles this:

- **Max size**: `MAX_DIFF_CHARS = 1_000_000` (~300K tokens)
- **Strategy**: Keep 70% from the start, 30% from the end
- **Return**: `(truncated_diff, was_truncated)` tuple — the boolean flag allows callers to note truncation in the PR description

## File Filtering

<!-- Source: packages/erk-shared/src/erk_shared/gateway/pr/diff_extraction.py -->

Before truncation, `filter_diff_excluded_files()` removes noise:

- Lock files (`pnpm-lock.yaml`, `uv.lock`, etc.)
- Other large generated files

This filtering happens before truncation, maximizing the useful content within the size budget.

## Submit Pipeline Integration

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py:448-470 -->

The PR submit pipeline chains these steps:

1. Extract diff via `ctx.git.analysis.get_diff_to_branch()`
2. Filter excluded files via `filter_diff_excluded_files()`
3. Truncate via `truncate_diff()` → `(diff_content, was_truncated)`
4. Write to scratch file with session isolation

## Related Documentation

- [PR Submit Phases](pr-submit-phases.md) — Full PR submission pipeline
- [GitHub CLI Limits](../architecture/github-cli-limits.md) — Other GitHub API size limits
