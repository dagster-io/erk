# Documentation Plan: Skip CI for plan-only and one-shot branches

## Context

This plan captures learnings from implementing `paths-ignore` patterns in GitHub Actions CI to skip workflow runs for plan-only branches. The implementation was straightforward (a single configuration file edit), but the session revealed important patterns around CI gating strategy and Git/Graphite integration that benefit future development.

The key insight is that `paths-ignore` is more deterministic than `branches-ignore` for branches that contain both metadata and code (like `planned/` branches). Branch naming conventions are fuzzy, but file paths are precise. When a push contains only `.erk/impl-context/` files, CI should skip; when it contains source code, CI should run. This distinction is impossible with `branches-ignore` alone.

The session also surfaced a common but non-obvious error pattern: running Git commands outside of Graphite (like `git pull --rebase`) breaks Graphite's tracking and requires manual remediation. This is a cross-cutting concern that affects any developer using Graphite with erk.

## Raw Materials

PR #7781 - Skip CI for plan-only and one-shot branches

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 6     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 2     |

## Stale Documentation Cleanup

Existing docs with phantom references requiring action. These cleanups are HIGH priority and should be addressed before creating new content.

### 1. Phantom branch pattern in workflow-gating-patterns.md

**Location:** `docs/learned/ci/workflow-gating-patterns.md` (lines 160-177)
**Action:** UPDATE_REFERENCES
**Phantom References:** `plan-review-*` branch pattern
**Cleanup Instructions:** The documentation describes using `branches-ignore` for `plan-review-*` branches, but this branch pattern does not exist in the current codebase. Search of `.github/workflows/` shows zero matches for `plan-review-`. The `erk-plan-review` LABEL exists and is real, but the branch naming convention is phantom. Replace `plan-review-*` references with the actual patterns in use: `planned/*` (draft-PR plans) and `oneshot-*` (legacy one-shot tasks). The architecture and guidance remain sound; only the specific branch pattern names need updating.

### 2. Incorrect path to land_cmd.py

**Location:** `docs/learned/planning/draft-pr-learn-pipeline.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `src/erk/cli/commands/pr/land_cmd.py`
**Cleanup Instructions:** The document references an incorrect file path with an extra `pr/` subdirectory. The actual path is `src/erk/cli/commands/land_cmd.py`. Update the reference in the "Affected Files" section.

### 3. Incorrect "gist URL" terminology

**Location:** `docs/learned/planning/draft-pr-learn-pipeline.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** "gist URL" stored as comment fallback
**Cleanup Instructions:** The section "Metadata Fallback for Gist URL" uses incorrect terminology. The code actually stores "learn materials branch name", not "gist URL". Rename the section to "Metadata Fallback for Learn Materials Branch" and update the description to accurately reflect that a branch name (not a gist URL) is stored in the PR comment.

## Documentation Items

### HIGH Priority

#### 1. Add paths-ignore pattern to workflow-gating-patterns.md

**Location:** `docs/learned/ci/workflow-gating-patterns.md`
**Action:** UPDATE
**Source:** [Impl], [PR #7781]

**Draft Content:**

````markdown
## Path-Based Filtering with paths-ignore

<!-- Source: .github/workflows/ci.yml:3-6 -->

When a branch type contains both metadata files and source code, `branches-ignore` cannot distinguish between plan-only pushes and code pushes. The `paths-ignore` pattern solves this:

```yaml
on:
  push:
    paths-ignore:
      - ".erk/impl-context/**"
      - ".worker-impl/**"
```
````

**How paths-ignore works:** When all changed files match a `paths-ignore` pattern, GitHub prevents the workflow from being queued entirely (zero cost). When any file doesn't match the ignore patterns (e.g., `src/`, `tests/`), the workflow runs normally.

**Why this exists:** planned/ branches contain BOTH plan metadata (`.erk/impl-context/`) AND implementation code. A simple `branches-ignore: ["planned/*"]` would skip CI for all pushes to these branches, including code changes that need testing. With `paths-ignore`, the CI decision is based on actual file changes, not branch naming conventions.

**Note on empty commits:** Empty commits bypass `paths-ignore` because there are no changed files to evaluate. This is rarely an issue in practice.

### When to Use paths-ignore vs branches-ignore

| Scenario                                                   | Use               | Rationale                                 |
| ---------------------------------------------------------- | ----------------- | ----------------------------------------- |
| Branch contains ONLY metadata (e.g., `plan-review-*`)      | `branches-ignore` | All pushes should skip CI                 |
| Branch contains BOTH metadata AND code (e.g., `planned/*`) | `paths-ignore`    | Need to distinguish based on file content |
| Branch is ephemeral and always skippable                   | `branches-ignore` | Simpler configuration                     |

````

---

### MEDIUM Priority

#### 2. CI skip behavior for learn branches

**Location:** `docs/learned/ci/workflow-gating-patterns.md` (add as subsection)
**Action:** UPDATE
**Source:** [Impl], [PR #7781]

**Draft Content:**

```markdown
### Learn Branch CI Behavior

Learn branches (e.g., `learn/7781`) that only modify `.erk/impl-context/` files will skip CI due to the `paths-ignore` configuration. This is expected behavior:

- Learn branches store documentation and session materials, not code
- There's nothing to lint, test, or type-check
- Skipping CI saves resources and reduces dashboard noise

**If you need CI on a learn branch:** Push a code change (any file outside the ignored paths). The presence of a non-ignored file will trigger the workflow normally.
````

#### 3. PR submission metadata timing

**Location:** `docs/learned/planning/draft-pr-lifecycle.md` or create critical ordering section
**Action:** UPDATE
**Source:** [PR #7781] (automated review finding)

**Draft Content:**

```markdown
### Critical Ordering: Dispatch Metadata Before PR Body Updates

When submitting a PR that triggers downstream CI workflows, dispatch metadata must be written BEFORE the PR body is updated. This prevents a race condition where CI reads stale metadata from the PR body.

The defensive pattern in the codebase writes metadata comments first, then updates the PR body. When implementing PR submission pipelines, maintain this ordering to avoid intermittent CI failures.
```

#### 4. paths-ignore vs branches-ignore decision rationale

**Location:** `docs/learned/ci/workflow-gating-patterns.md` (update decision table)
**Action:** UPDATE
**Source:** [Impl] (user correction during implementation)

**Draft Content:**

Update the existing decision table in workflow-gating-patterns.md to add:

```markdown
| Branch contains both metadata and code | `paths-ignore` | `branches-ignore` can't distinguish plan-only vs code pushes |
```

And add prose explaining: "When a branch naming convention encompasses multiple content types (like `planned/` branches which contain both `.erk/impl-context/` plans AND implementation source code), prefer `paths-ignore` to gate based on actual file changes rather than branch name."

---

### LOW Priority

None identified.

## Contradiction Resolutions

**ZERO contradictions found.**

The existing-docs-checker identified what appeared to be a contradiction in `docs/learned/ci/workflow-gating-patterns.md`, but adversarial verification reveals this is NOT a contradiction. The documentation describes the RIGHT PATTERN (skip CI for plan-only branches using branches-ignore) but references a branch naming convention (`plan-review-*`) that was either never implemented or was replaced.

This is classified as STALE_NOT_CONTRADICTION: one phantom reference plus one real architecture equals delete the ghost. The architecture and guidance are sound; only the specific branch pattern names are outdated.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Git Rebase Breaks Graphite Tracking

**What happened:** After running `git pull --rebase` to sync with remote, `gt submit` failed with a "diverged branch" error. The git operations succeeded, but Graphite's internal tracking became invalid.

**Root cause:** Graphite tracks commit SHAs internally. When `git pull --rebase` rewrites history, the commits Graphite knows about no longer exist. Git operations complete successfully, but Graphite's tracking state is now stale.

**Prevention:** After running any git command that modifies history outside of Graphite (`git pull --rebase`, `git merge`, `git cherry-pick`, `git reset`), check for Graphite tracking divergence warnings. If diverged, run `gt track --no-interactive <branch>` to remediate. Prefer using Graphite commands (`gt submit`, `gt sync`) when they can accomplish the same task.

**Recommendation:** TRIPWIRE (score 5) - This is a non-obvious, cross-cutting error with silent failure characteristics.

### 2. Cleanup Push Fails When Branch Behind Remote

**What happened:** The `.erk/impl-context/` cleanup step committed and tried to push, but failed with "non-fast-forward rejection" because the local branch was behind remote.

**Root cause:** The cleanup script committed without first checking if the branch was behind remote. After another process pushed to the same branch, the local push failed.

**Prevention:** Before pushing cleanup commits, check `git status` for "Your branch is behind" or use `git pull --rebase` first to sync with remote.

**Recommendation:** ADD_TO_DOC (score 3) - Medium severity issue specific to planning cleanup scripts; not broad enough for a tripwire.

### 3. branches-ignore Doesn't Work for Mixed-Content Branches

**What happened:** Initial implementation proposed `branches-ignore: ["planned/review-*"]` to skip CI for plan-only branches. User correctly identified this as too imprecise.

**Root cause:** `planned/` branches contain BOTH plan metadata AND implementation code. `branches-ignore` would skip CI for ALL pushes to these branches, including code changes that need testing.

**Prevention:** When designing CI gating for branches, identify what content types the branch contains. If a branch type contains multiple content types, use `paths-ignore` instead of `branches-ignore`.

**Recommendation:** TRIPWIRE (score 4) - Non-obvious design decision that affects all CI workflow modifications.

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Git Operations Outside Graphite Cause Tracking Divergence

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +1)
**Trigger:** Before running git commands outside Graphite (like `git pull --rebase`, `git merge`, `git cherry-pick`, `git reset`)
**Warning:** External git operations change commit history and can cause Graphite tracking divergence. After running git commands, check for tracking divergence warnings and run `gt track --no-interactive <branch>` if needed. Prefer using Graphite commands (gt submit, gt sync) when available.
**Target doc:** `docs/learned/universal-tripwires.md` or `docs/learned/erk/tripwires.md`

This tripwire warrants consideration for promotion to universal-tripwires.md because it crosses multiple areas: planning workflows, erk workflows, and any git operations. The error is silent (git operations succeed but Graphite tracking becomes invalid) and non-obvious (requires understanding Graphite's internal tracking mechanism). The remediation is simple once you know it (`gt track --no-interactive <branch>`), but discovering it requires reading Graphite error messages carefully.

### 2. branches-ignore Cannot Distinguish Mixed-Content Branches

**Score:** 4/10 (criteria: Non-obvious +2, Cross-cutting +2)
**Trigger:** Before using `branches-ignore` to skip CI for `planned/` branches
**Warning:** planned/ branches contain both plans AND implementation code. Use paths-ignore to distinguish plan-only pushes from code pushes. See workflow-gating-patterns.md.
**Target doc:** `docs/learned/ci/tripwires.md`

This tripwire is CI-specific and belongs in the ci category. It captures a design decision that isn't obvious from the branch naming convention alone. Without this warning, a developer might add `branches-ignore: ["planned/*"]` and accidentally skip CI for implementation code.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Cleanup Step Push Failures

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** This is specific to `.erk/impl-context/` cleanup workflow, not a cross-cutting concern. The resolution is straightforward (git pull --rebase first). Document in planning docs as a pattern, but it doesn't meet the tripwire threshold because it's narrow in scope and has an obvious resolution once you see the error message.

### 2. Learn Branches Skip CI with Only Metadata Changes

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** This is intentional behavior from this PR, not an error pattern to prevent. It might be surprising to developers who expect CI to run on all branch pushes, but it's by design. Documentation should explain the behavior, but it's not a "gotcha" requiring a tripwire warning. The behavior is correct and desired.

## Implementation Notes

### Session Flow Characteristics

- **Implementation type:** Simple (one-file config change)
- **CI outcome:** All 5556 tests passed on first try
- **Iteration count:** 1 (user requested more deterministic approach after initial proposal)
- **Key learning:** File-based CI filtering (paths-ignore) is more robust than branch-based filtering (branches-ignore) when a branch type contains multiple file types

### One-Shot Workflow Duplicate Detection

During analysis, two docs covering "One-Shot Workflow" were detected:

1. `docs/learned/planning/one-shot-workflow.md` (176 lines, audited 2026-02-16)
2. `docs/learned/workflows/one-shot-workflow.md` (not fully analyzed)

Both reference real code (`.github/workflows/one-shot.yml` exists). Recommend checking if consolidation is needed during documentation updates. This is not blocking for the current learn plan but should be addressed in a future cleanup pass.

### Attribution

Pattern implemented in PR #7781. Session: d191e54a-5b3f-48a0-88e1-32a55f909747.
