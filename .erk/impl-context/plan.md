# Documentation Plan: Clean up documentation for deleted legacy branch-naming code

## Context

PR #8289 represents Phase 4 of objective #7911, completing the removal of legacy issue-based plan backend code by cleaning up documentation references. This is purely a documentation maintenance PR that deletes stale content and updates cross-references to reflect the already-deleted code.

The PR demonstrates excellent documentation hygiene: it removed `submit-branch-reuse.md` (which documented deleted code), updated seven related documentation files to remove references to deleted functions like `generate_issue_branch_name()` and the `P{issue}-` branch prefix pattern, and simplified documentation to reflect the single remaining backend (`plnd/` format).

No new features, functions, classes, or CLI commands were added. The changes are entirely self-documenting because they update existing documentation to match the current state of the codebase. Creating new documentation from this PR would be redundant.

## Raw Materials

N/A

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 0     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 0     |
| Potential tripwires (score2-3) | 0     |

## Documentation Items

### HIGH Priority

**None.** This PR is a documentation cleanup that removes stale documentation. All cleanup actions were completed in the PR itself.

### MEDIUM Priority

**None directly from this PR.**

The automated audit bot identified two pre-existing issues in files NOT modified by this PR. These should be tracked separately for future maintenance:

1. **Pre-existing P{issue}- reference** — `docs/learned/planning/remote-implementation-idempotency.md` still describes the deleted `P{issue}-` detection pattern in its "Detection Pattern" section
2. **Pre-existing verbatim code blocks** — `docs/learned/tui/status-indicators.md` (lines 28-38, 44-51) contains verbatim Python function signatures that should be converted to source pointers

These are not outputs of this learn plan since they were not introduced by PR #8289.

### LOW Priority

**None.**

## Contradiction Resolutions

**No contradictions found.** The existing documentation checker found no conflicts between existing docs and the changes in this PR. All documentation consistently describes the current state (`plnd/` prefix) and legacy state (`P{issue}-` prefix marked as deleted) without contradiction.

## Stale Documentation Cleanup

**Already completed in PR #8289.** The PR itself performed the stale documentation cleanup:

1. Deleted `docs/learned/planning/submit-branch-reuse.md` (documented deleted code)
2. Removed phantom references to `generate_issue_branch_name()` from `planned-pr-branch-sync.md`
3. Updated cross-references in six additional documentation files
4. Simplified tripwire warnings to reference only `plnd/` prefix

No additional cleanup actions are required.

## Prevention Insights

No errors or failed approaches were discovered during implementation. The session completed cleanly without user corrections.

The learn workflow itself exhibited expected behavior: when running on a learn branch, it found only the current learn session (not the original implementation session). This is correct behavior — the implementation occurred in a different worktree/session.

## Tripwire Candidates

**No tripwire candidates identified.** This PR removed code and documentation without introducing new cross-cutting concerns. The changes are self-documenting and do not establish patterns that future agents need warnings about.

## Potential Tripwires

**None.**

## Analysis Summary

This PR validates the learned-docs core principle: **"Delete stale before adding new."**

The PR:
1. Identified stale documentation (`submit-branch-reuse.md` describing deleted code)
2. Removed the stale doc entirely
3. Updated all cross-references to reflect deletion
4. Validated via automated checks (`grep`, `make fast-ci`)
5. Did NOT create new redundant documentation

This is the correct pattern for documentation maintenance. No new documentation is warranted because:

- The current system behavior is already documented in `docs/learned/erk/branch-naming.md` (audited 2026-02-24)
- The legacy system is already marked as deleted in `docs/learned/planning/branch-name-inference.md`
- This PR updates docs to match reality, which is self-documenting

## Recommendations

**PRIMARY: Generate NO new documentation from this PR.** The cleanup is complete and self-documenting.

**SECONDARY: Track the two pre-existing audit findings separately.** The `remote-implementation-idempotency.md` P{issue}- reference and `status-indicators.md` verbatim code blocks should be addressed in future documentation maintenance work, not as part of this PR's learning output.
