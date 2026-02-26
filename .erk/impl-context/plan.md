# Documentation Plan: Fix CI: force-add gitignored impl-context directory

## Context

This plan captures learnings from PR #8328, which fixed a CI workflow failure introduced when PR #8308 added `.erk/impl-context/` to `.gitignore`. The `plan-implement.yml` workflow intentionally commits this directory to branches temporarily for rerun support, but after the gitignore change, `git add .erk/impl-context` failed because git refuses to add gitignored paths without the `-f` flag.

The fix was straightforward: change `git add .erk/impl-context` to `git add -f .erk/impl-context`. However, the broader lesson is about **cross-file impact analysis** when modifying `.gitignore` and understanding that **CI workflows may intentionally track gitignored files**. This is a valid pattern where local development safety (preventing accidental commits) coexists with CI workflow requirements (temporary tracking for transport).

Future agents working on CI workflows or modifying `.gitignore` need to understand this pattern to avoid similar failures. The agent that fixed this issue demonstrated excellent diagnostic skills and completed the fix without user intervention, showing that proper documentation of CI workflow patterns enables autonomous problem-solving.

## Raw Materials

PR #8328 session analysis and code diff analysis.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 3     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 1     |

## Documentation Items

### HIGH Priority

#### 1. Force-adding gitignored directories in CI workflows

**Location:** `docs/learned/ci/gitignored-directory-commit-patterns.md`
**Action:** CREATE
**Source:** [Impl], [PR #8328]

**Draft Content:**

```markdown
# Force-Adding Gitignored Directories in CI Workflows

read-when:
  - Using `git add` in CI workflows
  - Working with `.erk/impl-context/` in workflows
  - Adding paths to `.gitignore` that CI may reference

## Overview

CI workflows may need to temporarily track files that are gitignored locally. This is a valid pattern when the workflow requires git-based transport of files that should never be accidentally committed during local development.

## When This Pattern Applies

Use `git add -f` when:
- The path is gitignored to prevent accidental local commits
- A CI workflow must temporarily commit the path for transport (e.g., rerun support)
- The workflow includes a cleanup step that removes the path from tracking

## Implementation Pattern

See `.github/workflows/plan-implement.yml` for the canonical example:

1. Create the gitignored directory
2. Force-add despite gitignore using `-f` flag
3. Verify staging succeeded with `git status`
4. Commit and push
5. Later: remove from tracking with `git rm -rf`

## Key Principles

- The `-f` flag signals intentional override of gitignore rules
- Always pair force-add with a cleanup step
- Add comments explaining why the path is gitignored locally but tracked in CI
- Never use `git add -f` in local workflows; only in CI where tracking is intentional and temporary

## Related Documentation

- See `docs/learned/planning/impl-context.md` for impl-context lifecycle
- See `docs/learned/ci/plan-implement-workflow-patterns.md` for CI cleanup patterns
```

### MEDIUM Priority

#### 2. Temporary tracking pattern in plan-implement workflow

**Location:** `docs/learned/ci/plan-implement-workflow-patterns.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8328]

**Draft Content:**

```markdown
## Temporary Tracking of Gitignored Files

**Pattern**: CI workflows may need to track files that are gitignored locally.

**Use case**: The `plan-implement.yml` workflow tracks `.erk/impl-context/` temporarily for rerun support, then removes it before agent execution.

**Implementation**: See `.github/workflows/plan-implement.yml`, lines 146-223 for the complete pattern including force-add, verification, and cleanup steps.

**Rationale**: The `-f` flag signals intentional tracking and prevents failures when the path is gitignored. This allows local .gitignore rules to prevent accidental commits while CI workflows can still use git-based transport.
```

## Contradiction Resolutions

No contradictions detected. All existing documentation in `docs/learned/planning/impl-context.md`, `docs/learned/ci/plan-implement-workflow-patterns.md`, and related docs is consistent with the patterns discovered in this implementation.

## Stale Documentation Cleanup

No stale documentation detected. All file references in existing impl-context and CI workflow docs were verified as valid.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Gitignore-Workflow Mismatch

**What happened:** PR #8308 added `.erk/impl-context/` to `.gitignore` without checking if CI workflows referenced it. The `plan-implement.yml` workflow then failed with exit code 1 because `git add .erk/impl-context` refused to add the gitignored path.

**Root cause:** Cross-file impact analysis was not performed when modifying `.gitignore`. The change was correct for local development safety, but broke CI workflows that intentionally track the path.

**Prevention:** When adding paths to `.gitignore`, grep all `.github/workflows/` files for `git add` commands referencing the path. If found, update them to use `git add -f` or document why the workflow needs to track the gitignored file.

**Recommendation:** TRIPWIRE - This is a cross-cutting concern with silent failure that warrants a proactive warning.

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Workflow-gitignore mismatch detection

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before adding paths to `.gitignore`
**Warning:** Check if CI workflows reference the path with `git add`. If found, update to `git add -f` or document why the workflow needs to track the gitignored file.
**Target doc:** `docs/learned/ci/tripwires.md`

This tripwire addresses the root cause of PR #8328. The failure mode is particularly problematic because the error message ("paths are ignored by one of your .gitignore files") doesn't immediately indicate which workflow is affected or why. The cross-file impact is non-obvious: modifying `.gitignore` can break CI workflows in a completely different directory. Adding this tripwire will prompt agents to perform the necessary grep before submitting gitignore changes.

### 2. CI force-add intent signaling

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** Before using `git add -f` in CI workflows
**Warning:** Always add a comment explaining why the file is gitignored locally but must be tracked in CI. Document the cleanup step that removes it from tracking.
**Target doc:** `docs/learned/ci/tripwires.md`

The `-f` flag signals intentional override of gitignore rules, but its purpose is not self-documenting. A comment makes the intent explicit for future maintainers. This prevents confusion about whether the force-add is a workaround or an intentional design choice.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Verify force-add succeeded with git status

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** This is a verification step within the force-add pattern rather than a standalone cross-cutting concern. It could be promoted to tripwire if force-add failures become a recurring issue. Currently classified as content within the gitignored-directory-commit-patterns doc rather than a separate tripwire.
