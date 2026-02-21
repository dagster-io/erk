# Documentation Plan: Fix draft PR plan list label duplication

## Context

This PR (#7762) fixed a bug where `erk plan list` was returning "No plans found" when using the draft PR backend. The root cause was an inconsistency between two implementations of the `PlanListService` interface: `DraftPRPlanListService` was prepending `"erk-plan"` to the caller-provided labels, while `RealPlanListService` used labels directly. When the CLI code (which already passes `["erk-plan"]`) called the draft PR backend, the resulting duplicate labels `["erk-plan", "erk-plan"]` caused GitHub's GraphQL filter to return zero results.

The fix itself was simple (3 lines removed from source, test interface corrections), but the implementation session surfaced valuable workflow patterns. Specifically, the agent encountered git rebase conflicts when cleaning up the `.erk/impl-context/` staging directory on a draft PR plan branch that had received remote updates. The resolution pattern for "deleted by them" conflicts in rebase context is non-obvious and worth documenting as a tripwire.

The primary value of this learn extraction is not the bug fix documentation (the fix prevents recurrence), but rather two cross-cutting patterns: (1) git rebase conflict resolution for staging directory cleanup, and (2) dual backend service consistency requirements. Both are tripwire-worthy because they affect future implementations and have non-obvious resolution patterns.

## Raw Materials

PR #7762: https://github.com/schrockn-dagster/erk/pull/7762

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 3     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Git rebase modify/delete conflict on staging directories

**Location:** `docs/learned/ci/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] session d5933e2d parts 1 and 2

**Draft Content:**

```markdown
## Git Rebase Conflict on .erk/impl-context/ Cleanup

**CRITICAL:** When cleaning up `.erk/impl-context/` during implementation setup on draft PR plan branches, you may encounter rebase conflicts if the remote branch has updates.

**Symptom:** After committing cleanup of `.erk/impl-context/` and attempting to push, you get "fetch first" error. After `git pull --rebase`, you see `CONFLICT (modify/delete): .erk/impl-context/plan.md deleted by them`.

**Resolution pattern:**
1. Use `git status` to identify which files are in conflict vs already staged
2. For each conflicted file: `git rm <file>` (NOT `git rm -f` on already-staged files)
3. `git rebase --continue`

**Key insight:** In rebase context, "them" = upstream/remote branch. This is opposite to merge semantics. The remote modified `.erk/impl-context/` files while your cleanup commit deleted them. Using `git rm` explicitly marks the deletion as the intended resolution.

**Source:** PR #7762 implementation session
```

---

#### 2. Dual backend service consistency requirement

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7762], [Impl]

**Draft Content:**

```markdown
## PlanListService Dual Backend Consistency

**CRITICAL:** When modifying either `RealPlanListService` (issue backend) or `DraftPRPlanListService` (draft PR backend), ALWAYS verify both implementations remain consistent in their handling of parameters.

**Requirement:** Both service implementations MUST handle the `labels` parameter identically:
- Use caller-provided labels directly
- NEVER prepend, append, or modify the labels list
- Caller (CLI command) is responsible for constructing complete labels list

**Verification checklist:**
1. Check both implementations in `src/erk/core/services/plan_list_service.py`
2. Verify test fixtures in `tests/unit/services/test_plan_list_service.py` use identical parameters for both backends
3. Confirm CLI code provides complete labels list

**Bug history:** PR #7762 fixed a bug where `DraftPRPlanListService` prepended `"erk-plan"` to caller-provided labels, causing duplicate labels sent to GitHub's GraphQL filter. This resulted in zero results returned, breaking `erk plan list` for draft PR backend.

**Cross-reference:** See `docs/learned/testing/dual-backend-testing.md` for testing patterns across both backends.

**Source:** PR #7762
```

---

### MEDIUM Priority

#### 1. Implementation setup and .erk/impl-context/ cleanup documentation

**Location:** `docs/learned/planning/draft-pr-plan-backend.md`
**Action:** UPDATE
**Source:** [Impl] session d5933e2d part 1

**Draft Content:**

Add new section "Implementation Setup and .erk/impl-context/ Cleanup" after existing architecture content:

```markdown
## Implementation Setup and .erk/impl-context/ Cleanup

When implementing from a draft PR plan, the implementation setup includes cleaning up the `.erk/impl-context/` staging directory that was created during plan save.

**Cleanup pattern:**
- Check for `.erk/impl-context/` existence
- Remove directory: `git rm -rf .erk/impl-context/`
- Commit: "Clean up impl-context staging directory"
- Push to remote

**Rebase conflicts:** If the remote branch has updates since plan save, you may encounter modify/delete conflicts during `git pull --rebase` after the cleanup commit. See `docs/learned/ci/tripwires.md` for the resolution pattern.

**Idempotency:** The cleanup step uses shell conditionals (`if [ -d .erk/impl-context/ ]`) making it safe to run multiple times.

**Source:** PR #7762 implementation session
```

---

### LOW Priority

No low priority items.

## Contradiction Resolutions

No contradictions detected between existing documentation and the insights from this PR.

**Analysis:**
- The existing documentation correctly describes the draft PR backend architecture
- The bug fix (removing label duplication) is a correction to unintended behavior, not a change in documented patterns
- All referenced code artifacts exist and are current
- The fix brings implementation in line with the documented interface (caller provides full labels list)

## Stale Documentation Cleanup

No stale documentation detected. All referenced files in existing documentation were verified to exist.

| Existing Doc | Phantom References | Action | Rationale |
|---|---|---|---|
| docs/learned/planning/draft-pr-plan-backend.md | None | CURRENT | All referenced files exist |
| docs/learned/testing/dual-backend-testing.md | None | CURRENT | All referenced files exist |
| docs/learned/architecture/github-graphql.md | None | CURRENT | All referenced files exist |

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Label duplication causing GitHub API to return zero results

**What happened:** `DraftPRPlanListService` prepended `"erk-plan"` to the labels list, but the CLI code already passed `["erk-plan"]`. The duplicate labels `["erk-plan", "erk-plan"]` caused GitHub's GraphQL filter to return zero results.

**Root cause:** Interface contract inconsistency between two service implementations. The test suite used different parameters (`labels=[]` for draft PR, `labels=["erk-plan"]` for issue backend), masking the architectural inconsistency.

**Prevention:** When implementing service interfaces with multiple backends, verify test fixtures use identical parameters as production callers. A test fixture discrepancy is often a symptom of architectural inconsistency, not a test design choice.

**Recommendation:** TRIPWIRE - see Tripwire #2 (Dual backend service consistency)

### 2. Git push rejected after cleanup commit

**What happened:** After committing `.erk/impl-context/` cleanup and attempting to push, the push was rejected because the remote branch had newer commits.

**Root cause:** Draft PR plan branches are "living branches" that can receive updates between plan save and implementation start. The cleanup commit was based on a stale local branch.

**Prevention:** Always run `git pull --rebase` before pushing on shared draft PR branches. The implementation setup workflow handles this, but the rebase can create conflicts (see Tripwire #1).

**Recommendation:** ADD_TO_DOC - covered by the .erk/impl-context/ cleanup documentation update

### 3. Rebase conflict resolution on already-staged files

**What happened:** During rebase conflict resolution, the agent attempted `git rm -f .erk/impl-context/plan.md .erk/impl-context/ref.json`, but `ref.json` was already staged as deleted, causing `fatal: pathspec did not match any files`.

**Root cause:** During rebase, some files may already be staged for deletion while others remain in conflict state. Running `git rm` on already-staged files fails.

**Prevention:** Always run `git status` before resolving rebase conflicts to understand which files are in conflict vs already staged. Only run `git rm` on files shown as unmerged.

**Recommendation:** TRIPWIRE - incorporated into Tripwire #1 (Git rebase modify/delete conflict)

### 4. Import sorting error after constant removal

**What happened:** Removing the `_PLAN_LABEL` constant triggered a ruff import sorting violation (I001).

**Root cause:** Removing a module-level constant can change the structure of the file in ways that trigger import reorganization rules.

**Prevention:** Run `make fix` immediately after removing constants, imports, or changing file structure. This is expected ruff behavior.

**Recommendation:** CONTEXT_ONLY - standard workflow, auto-fixable, not worth documenting

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Git Rebase Conflict Resolution for Staging Directory Cleanup

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, External tool quirk +1)
**Trigger:** Before cleaning up `.erk/impl-context/` during implementation setup on draft PR plans, OR when git rebase shows 'deleted by them' conflict
**Warning:** In rebase context, "them" = upstream/remote (opposite to merge). Use `git status` to check file states, then `git rm <conflicted-file>` followed by `git rebase --continue`. Do NOT use `git rm -f` on already-staged files.
**Target doc:** `docs/learned/ci/tripwires.md`

This is tripwire-worthy because the "them" semantics in rebase are counterintuitive - they are the opposite of merge semantics. Agents unfamiliar with this distinction may incorrectly resolve conflicts. The harm is wasted time debugging git state and potentially corrupted commit history if rebase is aborted incorrectly.

### 2. Dual Backend Service Consistency

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before modifying PlanListService (either Real or DraftPR variant)
**Warning:** Both service implementations MUST handle parameters identically. Verify test fixtures use identical parameters for both backends. Interface contracts are not enforced by the type system.
**Target doc:** `docs/learned/planning/tripwires.md`

This is tripwire-worthy because interface contract violations cause silent failures (zero results returned instead of an error). The bug in PR #7762 was only discovered because users saw "No plans found" - there was no error message indicating label duplication. Future implementations that modify either service without checking consistency could introduce similar silent failures.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Import sort after constant removal

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** This is auto-fixable via `make fix` and is common enough to be expected behavior. The workflow already includes running `make fix` after edits, so this doesn't warrant a tripwire. If agents frequently miss this step, it could be promoted.

### 2. .erk/impl-context/ cleanup rebase conflicts

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)
**Notes:** This is a specific instance of the general git rebase conflict pattern covered by Tripwire #1. It doesn't need a separate entry since the resolution pattern is identical. The specific context (staging directory cleanup) is documented in the .erk/impl-context/ cleanup update.
