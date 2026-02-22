# Documentation Plan: Eliminate checkout race condition in one_shot_dispatch.py

## Context

This plan captures documentation and tripwire needs from PR #7786, which eliminated a race condition in `one_shot_dispatch.py` by replacing the checkout/write/stage/commit pattern with the `commit_files_to_branch()` git plumbing method. The race window previously spanned approximately 200 lines of network calls while HEAD was checked out on the branch. The new approach commits files directly to the branch without any checkout, making the operation race-free.

The implementation revealed several cross-cutting patterns that deserve documentation. Most significantly, the session exposed an incomplete test discovery pattern where the agent found tests in `test_one_shot_dispatch.py` but missed related tests in `test_one_shot.py` that also needed assertion migration. Additionally, when addressing PR feedback and syncing diverged branches, the session demonstrated the critical requirement to run `gt track` after raw git rebases before using Graphite commands.

The PR represents the fourth step in a larger effort to eliminate checkout-based race conditions in erk, applying the same `commit_files_to_branch()` pattern already documented for `plan_save.py`. Rather than creating new documentation, this plan focuses on updating existing docs to reference the additional usage site, adding tripwires for discovered pitfalls, and strengthening testing guidance.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 4     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Update plan-save-branch-restoration.md to include one_shot_dispatch.py

**Location:** `docs/learned/architecture/plan-save-branch-restoration.md`
**Action:** UPDATE
**Source:** [PR #7786]

**Draft Content:**

```markdown
## Usage Sites

The `commit_files_to_branch()` pattern is used in multiple locations:

- **plan_save.py** — Commits plan files to branch without checkout
- **one_shot_dispatch.py** — Commits `.worker-impl/prompt.md` to branch without checkout

See `src/erk/cli/commands/one_shot_dispatch.py`, function `dispatch_one_shot()`, grep for `commit_files_to_branch`.
```

---

#### 2. Update testing.md with branch_commits assertion pattern

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Testing Direct Branch Commits

When code uses `commit_files_to_branch()` (git plumbing approach), files are committed directly to the branch without modifying HEAD or the working tree. Tests must use different assertion patterns:

**Instead of:**
- `git.commits[0].message` (tracks HEAD commits)
- `git.commits[0].staged_files` (tracks working tree staging)
- Filesystem assertions on file content

**Use:**
- `git.branch_commits[0].message` (tracks direct branch commits)
- `git.branch_commits[0].files` dict (committed file content)

The `branch_commits` property on FakeGit tracks commits made via `commit_files_to_branch()`. For reference implementation, see `tests/commands/one_shot/test_one_shot_dispatch.py`.
```

---

### MEDIUM Priority

#### 3. Update one-shot-workflow.md with git plumbing approach

**Location:** `docs/learned/planning/one-shot-workflow.md`
**Action:** UPDATE
**Source:** [PR #7786]

**Draft Content:**

```markdown
## Dispatch Implementation

The `dispatch_one_shot()` function commits `.worker-impl/prompt.md` directly to the branch using git plumbing (`commit_files_to_branch`). This avoids checkout, making the operation race-free.

Key behavior:
- HEAD never moves from the original branch
- Working tree is not modified
- No try/finally restoration needed (nothing to restore)

See `docs/learned/architecture/plan-save-branch-restoration.md` for the full git plumbing pattern.
```

---

#### 4. Update learned-docs.md with drift prevention guidance

**Location:** `docs/learned/documentation/learned-docs.md`
**Action:** UPDATE
**Source:** [PR #7786]

**Draft Content:**

```markdown
## Preventing Documentation Drift

Documentation drifts when it duplicates implementation details that change. Follow these guidelines:

**Avoid numbered implementation steps.** Instead of "Step 1: Create tree object, Step 2: Create commit object", describe what the code accomplishes conceptually and point to the source file.

**Avoid naming specific test functions.** Tests get renamed and refactored. Use prose like "see the test suite for `dispatch_one_shot`" instead of "see `test_dispatch_happy_path()`".

**Avoid internal attribute names.** Private methods and implementation details change. Describe behavior and link to source files for implementation details.

**Prefer source pointers.** Write "See `src/erk/cli/commands/one_shot_dispatch.py`, function `dispatch_one_shot()`" instead of copying code blocks.
```

---

## Contradiction Resolutions

**NONE DETECTED**

All existing documentation is consistent. The git plumbing approach and finally block restoration patterns are consistently documented across relevant files.

## Stale Documentation Cleanup

**NO PHANTOM REFERENCES DETECTED**

All code references in existing documentation were verified as accurate. Key verified references include paths in `plan-save-branch-restoration.md`, `planning/one-shot-workflow.md`, and `workflows/one-shot-workflow.md`.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Incomplete Test Discovery Pattern

**What happened:** The agent found and updated tests in `test_one_shot_dispatch.py` but missed a related test in `test_one_shot.py` that also called `dispatch_one_shot` via CLI, discovered only after CI failure.

**Root cause:** The agent used a filename-based heuristic (looking for `test_one_shot_dispatch.py`) rather than grepping for all imports/uses of `dispatch_one_shot` across the test directory.

**Prevention:** Before marking implementation complete, grep for ALL test files that import the module or function being changed: `grep -r 'dispatch_one_shot' tests/`

**Recommendation:** TRIPWIRE

### 2. Test Assertion Migration Gap

**What happened:** Tests were checking `git.commits[0].staged_files` but implementation switched to `git.branch_commits` (direct branch commits without checkout), causing test failures.

**Root cause:** When refactoring from checkout-based commits to direct branch commits, only some tests were updated. The relationship between commit mechanism and assertion type was not immediately obvious.

**Prevention:** When changing from checkout/commit pattern to `commit_files_to_branch`, grep for ALL test assertions using `git.commits` and update to `git.branch_commits`.

**Recommendation:** TRIPWIRE

### 3. Graphite Cache Invalidation

**What happened:** After `git rebase origin/$BRANCH` to sync diverged branches, running `gt restack` failed with "diverged from tracking" errors.

**Root cause:** Git rebase changes commit SHAs, but Graphite's cache (`.graphite_cache_persist`) still points to pre-rebase SHAs. Without running `gt track` first, Graphite doesn't know about the new commit graph.

**Prevention:** ALWAYS run `gt track --no-interactive` after any raw git rebase before running any Graphite commands.

**Recommendation:** TRIPWIRE

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Graphite Cache Invalidation After Rebase

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)

**Trigger:** After running `git rebase` outside Graphite commands

**Warning:** ALWAYS run `gt track --no-interactive` before `gt restack` or Graphite cache will be stale and cause "diverged from tracking" errors.

**Target doc:** `docs/learned/architecture/tripwires.md`

This tripwire is critical because the error message from Graphite ("diverged from tracking") doesn't indicate that running `gt track` is the solution. Agents encountering this error may try force-pushing, resetting, or other destructive operations without realizing the simple cache invalidation fix.

### 2. Incomplete Test Discovery When Refactoring

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)

**Trigger:** Before running CI on a refactored shared function

**Warning:** Grep for ALL test files that import the function (`grep -r 'function_name' tests/`), not just tests with matching filenames. Update ALL test consumers.

**Target doc:** `docs/learned/testing/tripwires.md`

The session demonstrated this exact failure pattern. The agent correctly refactored the implementation and found the obvious test file (`test_one_shot_dispatch.py`) but missed `test_one_shot.py` which exercises the same code path via CLI. Filename-based test discovery is a common heuristic that fails for shared/integrated code.

### 3. Test Assertion Migration for Commit Mechanism Change

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)

**Trigger:** When changing from checkout-based commits to `commit_files_to_branch`

**Warning:** Update ALL test assertions from `git.commits` to `git.branch_commits` across entire test suite. Files are committed directly to branch without modifying working tree.

**Target doc:** `docs/learned/testing/tripwires.md`

This tripwire codifies the relationship between implementation pattern and test assertion pattern. When code shifts from modifying HEAD/working-tree to using git plumbing, the fake git's tracking mechanism also shifts. This is non-obvious because `git.commits` and `git.branch_commits` are both valid properties, and tests will silently pass if checking the wrong one (they'll just be checking nothing).

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Documentation Drift from Implementation Details

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)

**Notes:** The PR review bot flagged both numbered implementation steps and specific test function names as drift risks. This affects all learned docs but doesn't cause immediate breakage. Could warrant tripwire promotion if documentation quality degrades.

### 2. Test Coverage Gap from Filename-Based Heuristics

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)

**Notes:** Similar to incomplete test discovery but less severe. Agents often match test files by filename pattern (`test_<module>.py`) when they should search for all importers. Could be promoted if this pattern recurs in future sessions.
