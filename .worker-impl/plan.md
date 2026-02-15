# Plan: Change audit-pr-docs.md to use Opus

## Context

The task is to change the model used by the "Audit PR Docs" review from `claude-haiku-4-5` to an Opus model. The Audit PR Docs review analyzes documentation in `docs/learned/` to detect verbatim code copies, inaccurate claims, duplicative sections, and drift risks.

### Why This Change

The Audit PR Docs review requires deep reasoning and careful analysis:
- Identifying verbatim code blocks requires comparing doc content against source files
- Detecting inaccurate claims requires understanding both doc assertions and source code behavior
- Classifying sections as DUPLICATIVE vs HIGH VALUE requires semantic understanding
- The review explicitly loads standards and applies multi-phase analysis methodology

According to `docs/learned/reviews/development.md:71`:
> Default to `claude-haiku-4-5` for cost efficiency. Only escalate to sonnet for reviews requiring deep reasoning

The audit-pr-docs review falls into the "deep reasoning" category, making it a candidate for a more capable model.

### Current Model References

From exploration of the codebase:
- `.github/workflows/plan-implement.yml` uses `claude-opus-4-6` as the default
- Other reviews use `claude-haiku-4-5` (test-coverage.md) or `claude-sonnet-4-5` (tripwires.md)
- The correct Opus model ID appears to be `claude-opus-4-6` based on current usage

## Changes

### File: `.github/reviews/audit-pr-docs.md`

**Location**: Line 6, the `model` field in the YAML frontmatter

**Current value**: `model: claude-haiku-4-5`

**New value**: `model: claude-opus-4-6`

This is a single-line change in the frontmatter that controls which Claude model the review uses.

## Implementation Details

### Review Spec Frontmatter Format

Review specs in `.github/reviews/` use YAML frontmatter with these fields (from `docs/learned/ci/convention-based-reviews.md`):
- `name`: Human-readable review name
- `paths`: Gitignore-style glob patterns
- `marker`: HTML comment marker for summary comments
- `model`: Claude model ID (e.g., `claude-opus-4-6`)
- `timeout_minutes`: Job timeout
- `allowed_tools`: Tool permission string
- `enabled`: Boolean flag

The `model` field is passed to the Claude Code CLI when running the review.

### Valid Model IDs

Based on exploration:
- Haiku: `claude-haiku-4-5`
- Sonnet: `claude-sonnet-4-5`
- Opus: `claude-opus-4-6`

The Opus model ID `claude-opus-4-6` is confirmed by `.github/workflows/plan-implement.yml:default: "claude-opus-4-6"`.

### No Other Changes Needed

- The review body (steps) remains unchanged — the analysis methodology is model-agnostic
- The `allowed_tools` constraint remains the same — Opus doesn't require additional tools
- The `timeout_minutes` remains 30 — Opus may be slower but should complete within the existing timeout
- No code changes needed in `src/erk/` — the review system reads the model field directly from frontmatter

## Files NOT Changing

- `.github/reviews/tripwires.md` — stays on `claude-sonnet-4-5`
- `.github/reviews/test-coverage.md` — stays on `claude-haiku-4-5`
- `.github/reviews/dignified-python.md` — unchanged
- `.github/reviews/dignified-code-simplifier.md` — unchanged
- `.github/workflows/code-reviews.yml` — the workflow doesn't hardcode model IDs
- `src/erk/review/` — no code changes needed

## Verification

After implementing this change:

1. **Syntax check**: The frontmatter should parse correctly
   - Run `erk exec discover-reviews --pr-number <any>` to verify parsing
   - The review should appear in the discovered reviews list

2. **Workflow integration**: The review should run with Opus on matching PRs
   - Push a PR that modifies a file in `docs/learned/`
   - Verify the review runs in CI
   - Check the GitHub Actions log to confirm `claude-opus-4-6` is used

3. **Behavior verification**: The review output should be more thorough
   - Compare review comments before/after the change
   - Opus should provide more detailed analysis and better detection of issues

## Edge Cases

- **Cost impact**: Opus is more expensive than Haiku. This is acceptable because the review only runs on PRs that touch `docs/learned/**/*.md` files, which is a small subset of all PRs.

- **Timeout**: Opus is slower than Haiku. The current 30-minute timeout should be sufficient, but if timeouts occur, this can be increased in a follow-up.

- **Model availability**: If `claude-opus-4-6` becomes unavailable, the review system will fail gracefully with a clear error message from Claude Code.

## Related Documentation

- `docs/learned/ci/convention-based-reviews.md` — Review frontmatter schema
- `docs/learned/ci/review-spec-format.md` — Design rationale for review specs
- `docs/learned/reviews/development.md` — Model selection guidance
- `.github/reviews/audit-pr-docs.md` — The file being modified