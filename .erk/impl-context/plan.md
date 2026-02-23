# Documentation Plan: Fix: _cleanup_no_worktree crashes when branch is checked out in another worktree

## Context

This PR addresses a bug in the `erk land` cleanup pipeline where `_cleanup_no_worktree()` crashed when attempting to delete a branch that was still checked out in another worktree (typically an implementation worktree). The root cause was a missing defensive check: three out of four cleanup paths called `_ensure_branch_not_checked_out()` before branch deletion, but the `NO_WORKTREE` path did not.

The fix is small (3 lines of production code) but reveals an important architectural insight: when multiple code paths perform the same destructive operation, they ALL must include the same defensive checks. The `NO_WORKTREE` classification means the current session is not running inside the branch's worktree, but the branch could still be checked out somewhere else. Pool state (recorded in pool.json) can become stale, so defensive checks must search for actual worktree locations rather than trusting recorded state.

Future agents would benefit from knowing this consistency requirement for cleanup paths, the specific test patterns for simulating `NO_WORKTREE` scenarios, and the general principle that stale pool state requires defensive searches rather than state-based lookups.

## Raw Materials

PR #7949

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 10 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 2 |
| Potential tripwires (score 2-3) | 2 |

## Stale Documentation Cleanup

**No stale references found.** The gap analysis flagged `_cleanup_non_slot_worktree` as a potential phantom reference, but verification confirms both `_cleanup_non_slot_worktree` (line 802) and `_cleanup_no_worktree` (line 748) exist as separate functions in `src/erk/cli/commands/land_cmd.py`. The existing documentation reference is correct.

## Documentation Items

### HIGH Priority

#### 1. Defensive branch deletion in ALL cleanup paths

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7949], [Impl]

**Draft Content:**

```markdown
**calling delete_branch in any land cleanup path** → Read [Multi-Worktree State Handling](../architecture/multi-worktree-state.md) first. Always call `_ensure_branch_not_checked_out()` before `delete_branch()`. Git refuses to delete branches checked out elsewhere, and pool state can be stale. All four cleanup paths (SLOT_ASSIGNED, SLOT_UNASSIGNED, NON_SLOT, NO_WORKTREE) require this defensive pattern.
```

---

#### 2. Stale pool state defensive pattern

**Location:** `docs/learned/architecture/multi-worktree-state.md`
**Action:** UPDATE
**Source:** [Impl], [PR #7949]

**Draft Content:**

Add a new section after "Defensive Branch Deletion" (around line 119):

```markdown
## Stale Pool State

Pool state recorded in `pool.json` can become stale when worktree paths are moved, removed externally, or when parallel operations update the filesystem without synchronizing pool metadata. This staleness affects all cleanup operations:

**Never trust `worktree_path` from pool state alone.** Always use defensive checks that search for actual worktree locations:

- Query `git.worktree.find_worktree_for_branch()` to find where a branch is actually checked out
- Don't assume `worktree_path=None` means the branch isn't checked out anywhere
- Use `_ensure_branch_not_checked_out()` before any branch deletion, regardless of what pool state says

<!-- Source: src/erk/cli/commands/land_cmd.py, _cleanup_no_worktree -->

This pattern is applied across all four cleanup paths in the land command. See `_cleanup_no_worktree()`, `_cleanup_non_slot_worktree()`, and related functions.
```

---

#### 3. Land cleanup pipeline four-path architecture

**Location:** `docs/learned/erk/branch-cleanup.md`
**Action:** UPDATE
**Source:** [PR #7949], [Impl]

**Draft Content:**

Add a new section after "Worktree State After Landing PRs" (around line 160):

```markdown
## Land Cleanup Pipeline Architecture

The `erk land` command classifies worktrees into four paths, each requiring specific cleanup behavior:

| Classification | Condition | Defensive Requirement |
|----------------|-----------|----------------------|
| SLOT_ASSIGNED | Worktree is a slot with the branch assigned | `_ensure_branch_not_checked_out()` before deletion |
| SLOT_UNASSIGNED | Worktree is a slot but branch not assigned | `_ensure_branch_not_checked_out()` before deletion |
| NON_SLOT | Worktree exists but is not a slot | `_ensure_branch_not_checked_out()` before deletion |
| NO_WORKTREE | No worktree exists for current session | `_ensure_branch_not_checked_out()` before deletion |

**Critical:** ALL four paths must call `_ensure_branch_not_checked_out()` before branch deletion. The `NO_WORKTREE` path was missing this check until PR #7949, causing crashes when the branch was checked out in a different worktree (e.g., an implementation worktree).

<!-- Source: src/erk/cli/commands/land_cmd.py -->

See `_cleanup_and_navigate()` and the four cleanup functions for implementation.
```

---

### MEDIUM Priority

#### 4. NO_WORKTREE test pattern

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
**testing NO_WORKTREE cleanup scenarios** → Read [Erk Test Reference](testing.md) first. Set `worktree_path=None` in `_cleanup_and_navigate()` while configuring `FakeGit.worktrees` to show the branch checked out elsewhere. This simulates the NO_WORKTREE classification with an active worktree for the branch.
```

---

#### 5. Sequential cleanup verification in tests

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add to an existing "Test Patterns" section or create one:

```markdown
## Sequential Cleanup Verification

When testing multi-step cleanup operations, verify both intermediate and final states:

1. **Intermediate state:** Verify detached HEAD is checked out (branch released)
2. **Final state:** Verify branch is deleted, worktree removed if applicable

Example from land cleanup tests:
- Assert `FakeGit.detached_checkouts` contains the worktree path (defensive checkout happened)
- Assert `FakeGit.deleted_branches` contains the branch name (branch was deleted)

<!-- Source: tests/unit/cli/commands/land/test_cleanup_and_navigate.py -->

This pattern ensures each step of the sequence executed correctly, not just the final outcome.
```

---

#### 6. Post-PR validation workflow

**Location:** `docs/learned/workflows/` (new file: `pr-validation.md`)
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Post-PR Validation Workflow
read_when:
  - "validating a PR before marking ready for review"
  - "running pre-merge checks"
  - "debugging CI failures on a PR"
---

# Post-PR Validation Workflow

After submitting a PR, run this three-step validation sequence before marking ready for review:

1. **`erk pr check`** - Verify PR metadata and linked issues
2. **`/debug-ci`** (or `/local:debug-ci`) - Check CI status and analyze failures
3. **`/local:review`** - Run local code reviews (dignified-python, tripwires, coverage)

This workflow catches issues early and prevents round-trips with reviewers.

## Interpreting Results

- **CI failures:** Check for infrastructure keywords ("timeout", "download", "CDN") to distinguish transient failures from code issues
- **Review findings:** Filter actionable violations from false positives (look for "established pattern", "test scaffolding" notes)
```

---

#### 7. Transient CI failure detection

**Location:** `docs/learned/ci/` (new file: `transient-failure-detection.md`)
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Transient CI Failure Detection
read_when:
  - "debugging CI failures"
  - "CI fails with network or timeout errors"
  - "determining if CI failure is infrastructure-related"
---

# Transient CI Failure Detection

Not all CI failures indicate code problems. Infrastructure failures can appear similar to test failures.

## Transient Failure Keywords

Look for these keywords in failure logs to identify infrastructure issues:

- `timeout` / `timed out`
- `Failed to download`
- `operation timed out`
- `CDN`
- `retry` (especially with multiple retry attempts)
- `connection reset`

## Verification

Before investigating code, check if a re-run succeeded:

```bash
gh run list --branch <branch> --json conclusion,status,databaseId | head -5
```

If the most recent run succeeded without code changes, the failure was transient.

## Action

For confirmed transient failures, re-run the failed CI job rather than investigating code.
```

---

#### 8. Update _ensure_branch_not_checked_out pattern documentation

**Location:** `docs/learned/architecture/multi-worktree-state.md`
**Action:** UPDATE
**Source:** [PR #7949]

**Draft Content:**

Update the "Defensive Branch Deletion" section (around line 111) to list all application sites:

```markdown
The defensive pattern in `_ensure_branch_not_checked_out()` is applied in:

- `_cleanup_slot_assigned()` - SLOT_ASSIGNED path
- `_cleanup_slot_unassigned()` - SLOT_UNASSIGNED path
- `_cleanup_non_slot_worktree()` - NON_SLOT path
- `_cleanup_no_worktree()` - NO_WORKTREE path (added in PR #7949)

<!-- Source: src/erk/cli/commands/land_cmd.py -->
```

---

### LOW Priority

#### 9. Review result synthesis guidance

**Location:** `docs/learned/reviews/` (new file or existing tripwires.md)
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Interpreting Parallel Review Results

When `/local:review` runs multiple review agents in parallel, synthesize findings by:

1. **Filtering false positives:** Notes like "established pattern", "test scaffolding", "false positive" indicate non-actionable items
2. **Aggregating actionable violations:** Count violations that lack dismissal notes
3. **Reporting "0 actionable violations":** Only when all findings are filtered out

Parallel reviews may overlap or contradict - prefer violations flagged by multiple reviews.
```

---

#### 10. Git error message for deleting checked-out branch

**Location:** `docs/learned/architecture/git-graphite-quirks.md`
**Action:** UPDATE
**Source:** [PR #7949]

**Draft Content:**

Add to the error message catalog:

```markdown
## Branch Deletion Errors

**Error:** `RuntimeError: cannot delete branch 'X' currently checked out at 'Y'`

**Cause:** Attempted to delete a branch that is checked out in another worktree.

**Resolution:** Call `_ensure_branch_not_checked_out()` before `delete_branch()`. This detaches HEAD in any worktree holding the branch, making deletion safe.

<!-- Source: src/erk/cli/commands/land_cmd.py, _ensure_branch_not_checked_out -->
```

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Missing defensive check before branch deletion

**What happened:** `_cleanup_no_worktree()` attempted to delete a branch that was still checked out in an implementation worktree, causing a crash.

**Root cause:** The NO_WORKTREE classification means "no worktree for the current session," not "branch isn't checked out anywhere." Pool state showing `worktree_path=None` doesn't mean the branch is safe to delete.

**Prevention:** Always call `_ensure_branch_not_checked_out()` before any `delete_branch()` call, regardless of pool state or worktree classification.

**Recommendation:** TRIPWIRE - This pattern should trigger on any code path that calls delete_branch.

### 2. Inconsistent defensive patterns across cleanup paths

**What happened:** Three out of four cleanup paths had the defensive check; the fourth was missing it.

**Root cause:** When the NO_WORKTREE path was created, it didn't follow the pattern established by the other three paths.

**Prevention:** When adding new code paths that perform destructive operations, verify consistency with existing parallel paths. Document the required defensive checks for each classification.

**Recommendation:** ADD_TO_DOC - The four-path architecture and required checks should be documented.

### 3. Stale pool state assumptions

**What happened:** Code assumed pool.json's `worktree_path` field accurately reflected where a branch was checked out.

**Root cause:** Pool state can become stale when worktrees are manipulated outside erk's control, or when parallel sessions create race conditions.

**Prevention:** Never trust pool state alone for destructive operations. Use defensive checks that query git directly (e.g., `find_worktree_for_branch()`).

**Recommendation:** TRIPWIRE - This pattern should warn whenever cleanup code relies on pool state without verification.

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Missing _ensure_branch_not_checked_out before branch deletion

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)

**Trigger:** Before calling `delete_branch()` in any land cleanup path or any code that deletes branches.

**Warning:** Always call `_ensure_branch_not_checked_out()` first to handle stale pool state and branches checked out in other worktrees. Git will fail with "currently checked out" error if the branch is checked out anywhere.

**Target doc:** `docs/learned/cli/tripwires.md`

This tripwire is high priority because branch deletion is destructive and the error (crash) only manifests in specific multi-worktree scenarios that are easy to miss in testing. The fix discovered that three out of four parallel code paths already had this check - the inconsistency caused the bug.

### 2. Stale pool state assumptions

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Silent failure +1)

**Trigger:** When implementing cleanup/deletion logic that uses pool state fields like `worktree_path`.

**Warning:** Don't rely solely on pool.json's `worktree_path` field. Pool state can become stale when worktree paths don't match actual locations. Use defensive checks that search for actual worktree locations (e.g., `find_worktree_for_branch()`).

**Target doc:** `docs/learned/architecture/multi-worktree-state.md` (add to tripwires frontmatter)

This tripwire addresses the root cause rather than the symptom. While the first tripwire catches missing defensive calls, this one warns about the broader anti-pattern of trusting recorded state for destructive operations.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. NO_WORKTREE path missing safety checks

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)

**Notes:** This is largely covered by tripwire #1 above. The specific issue was that NO_WORKTREE was the one path missing the check. Rather than a separate tripwire, this is better documented as part of the four-path architecture documentation.

### 2. Transient CI failure mistaken for code bug

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)

**Notes:** This is an operational pattern rather than a code pattern. Infrastructure failures (timeouts, CDN issues) can look like test failures. Better addressed through documentation of the triage keywords and verification process than a tripwire.

---

## Code Changes

Items that belong in code rather than documentation:

### 1. Docstring for _cleanup_no_worktree

**Action:** CODE_CHANGE

The `_cleanup_no_worktree()` function should have a docstring explaining:
- When this path is triggered (no worktree exists for current session)
- Why `_ensure_branch_not_checked_out()` is called (branch may be checked out elsewhere)
- The defensive pattern this follows (consistent with other cleanup paths)

**Location:** `src/erk/cli/commands/land_cmd.py`, line ~748

The current docstring ("Handle cleanup when no worktree exists: delete branch only if exists locally.") is incomplete - it doesn't explain the defensive check or why it's needed.

---

## Implementation Order

1. **Update cli/tripwires.md** - Add defensive branch deletion tripwire (HIGH priority)
2. **Update architecture/multi-worktree-state.md** - Add stale pool state section and tripwire (HIGH priority)
3. **Update erk/branch-cleanup.md** - Add four-path architecture documentation (HIGH priority)
4. **Update testing/tripwires.md** - Add NO_WORKTREE test pattern (MEDIUM priority)
5. **Update testing/testing.md** - Add sequential cleanup verification pattern (MEDIUM priority)
6. **Create workflows/pr-validation.md** - Document post-PR validation workflow (MEDIUM priority)
7. **Create ci/transient-failure-detection.md** - Document transient CI failure patterns (MEDIUM priority)
8. **Update architecture/multi-worktree-state.md** - List all _ensure_branch_not_checked_out application sites (MEDIUM priority)
9. **Update reviews docs** - Add review synthesis guidance (LOW priority)
10. **Update architecture/git-graphite-quirks.md** - Add error message catalog entry (LOW priority)
11. **CODE_CHANGE: Update _cleanup_no_worktree docstring** - Explain defensive pattern

---

## Attribution Summary

| Source | Items | HIGH | MEDIUM | LOW |
|--------|-------|------|--------|-----|
| Implementation Session | 6 | 2 | 3 | 1 |
| PR #7949 (Diff Analysis) | 4 | 2 | 2 | 0 |
| Post-PR Validation Session | 3 | 0 | 2 | 1 |
