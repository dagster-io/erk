# Plan: Address PR Review Comments on #8199

## Context

PR #8199 "Embed PlanDataTable in ObjectivePlansScreen modal" has open review comments that need to be addressed. This plan follows the `/erk:pr-address` workflow to classify, batch, and resolve all feedback.

## Steps

1. **Phase 1: Classify Feedback** — Run the `pr-feedback-classifier` via Task agent to fetch and classify all unresolved review and discussion comments on PR #8199

2. **Phase 2: Display Batched Plan** — Present the classified comments grouped by complexity (local fixes → cross-cutting → complex)

3. **Phase 3: Execute by Batch** — For each batch:
   - Read relevant files and make fixes per reviewer feedback
   - Run CI checks on changed files
   - Commit the batch
   - Resolve all threads using `erk exec resolve-review-threads` (batch) and `erk exec reply-to-discussion-comment`

4. **Phase 4: Final Verification** — Re-run classifier to confirm all threads resolved

5. **Phase 5: Update PR Description** — Run `erk exec update-pr-description --session-id <session-id>` to update title/body

## Verification

- All review threads resolved on PR #8199
- All discussion comments replied to
- CI passes after all changes
