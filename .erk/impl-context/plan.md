# Documentation Plan: Fix get_diff_to_branch: use three-dot syntax for accurate PR diffs

## Context

This plan documents learnings from PR #8159, which fixed a subtle but impactful bug in `get_diff_to_branch`. The implementation was using two-dot git diff syntax (`branch..HEAD`) instead of three-dot (`branch...HEAD`). While this may seem like a minor character change, the semantic difference is significant: two-dot compares tree states at both tips directly, causing spurious files to appear in diffs when a feature branch has diverged from its base (e.g., when master has new commits the feature branch doesn't have). Three-dot syntax diffs from the merge-base to HEAD, showing only changes introduced on the feature branch -- exactly what GitHub shows in PR diffs.

The fix touched only two core files but the learnings have cross-cutting implications. The bug manifested as "noisy diffs" with 15x file inflation (45 spurious files vs 3 actual). Such silent failures are particularly dangerous because they produce valid output that looks plausible. An agent without the documented understanding of two-dot vs three-dot semantics could easily make this mistake again, or worse, "fix" the correct three-dot back to two-dot based on flawed reasoning.

The implementation sessions also revealed important patterns: pre-existing CI failures that must be distinguished from implementation-caused failures, the limitations of dict-based fakes for testing git command syntax, and a verification workflow that proves test discriminatory power. These patterns deserve documentation to prevent future agents from wasting time on the same issues.

## Raw Materials

PR #8159

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 7     |
| Contradictions to resolve      | 2     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 1     |

## Documentation Items

### HIGH Priority

#### 1. Git diff two-dot vs three-dot tripwire

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8159]

**Draft Content:**

```markdown
## TRIPWIRE: Git Diff Syntax for PR Comparisons

**Trigger:** Implementing git diff operations for PR or branch comparison

**Warning:** ALWAYS use three-dot syntax (`base...head`) not two-dot (`base..head`)

**Why:**
- Three-dot: `git diff base...head` = diff from merge-base to head (shows only feature branch changes)
- Two-dot: `git diff base..head` = diff between two tree states (includes inverse of diverged base commits)

When a feature branch diverges from its base (base has commits the feature doesn't have), two-dot diff includes the **inverse** of those base commits as spurious deletions.

**Example:** Feature branch adds `feature.txt`. Main branch adds `main-only.txt` after branch point.
- Two-dot shows: `feature.txt` added, `main-only.txt` deleted (WRONG - spurious)
- Three-dot shows: `feature.txt` added (CORRECT - only feature branch changes)

**Historical context:** PR #8159 fixed `get_diff_to_branch()` which incorrectly used two-dot, causing noisy diffs with 15x file inflation (45 spurious files vs 3 actual).

**Source pointers:**
- See `packages/erk-shared/src/erk_shared/gateway/git/analysis_ops/real.py` (grep `get_diff_to_branch`)
- See `packages/erk-shared/src/erk_shared/gateway/git/analysis_ops/abc.py` for ABC definition
- Integration test: `tests/integration/test_real_git_analysis_ops.py`
```

---

#### 2. Pre-existing CI failures during implementation tripwire

**Location:** `docs/learned/ci/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## TRIPWIRE: Pre-existing CI Failures During Implementation

**Trigger:** When CI fails during plan implementation

**Warning:** Don't assume CI failure is caused by your changes. Distinguish pre-existing failures from implementation-caused failures.

**Pattern:**
1. CI fails with error message
2. Check if error is related to files you modified
3. If unrelated (e.g., generated reference docs, unrelated lint failures), fix the pre-existing issue first
4. Re-run CI to verify your implementation passes

**Common pre-existing failures:**
- Generated reference docs out of date (e.g., `erk-exec/reference.md`)
  - Fix: Run the generation command (e.g., `erk-dev gen-exec-reference-docs`)
- Formatting drift in unrelated files
- Type errors from upstream dependency changes

**Example:** PR #8159 implementation changed only 2 files (real.py, abc.py) but CI failed on `exec reference check`. The reference doc was out of date from prior changes. After regenerating it, CI passed.
```

---

#### 3. Acknowledge fix in large-diff-recovery.md

**Location:** `docs/learned/pr-operations/large-diff-recovery.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8159]

**Draft Content:**

Add note after the existing three-dot example (around line 27):

```markdown
> **Note:** Prior to PR #8159, the `get_diff_to_branch()` implementation incorrectly used two-dot syntax (`branch..HEAD`) instead of three-dot. The example above was always correct and now matches the implementation. The bug caused spurious files in diffs when feature branches diverged from their base.
```

---

### MEDIUM Priority

#### 4. Git diff syntax reference documentation

**Location:** `docs/learned/reference/git-diff-syntax.md`
**Action:** CREATE
**Source:** [Impl] [PR #8159]

**Draft Content:**

```markdown
---
read-when: working with git diff, log, or rev-list operations; comparing branches; implementing PR diff features
why: git dot-notation semantics differ between commands in non-obvious ways
---

# Git Diff Syntax Reference

## Overview

Git uses two-dot (`..`) and three-dot (`...`) notation differently depending on the command. Confusing these leads to subtle bugs.

## Command Semantics

### git diff

| Syntax | Meaning | Use Case |
|--------|---------|----------|
| `git diff A..B` | Compare tree at A to tree at B directly | Rare - usually not what you want |
| `git diff A...B` | Diff from merge-base(A,B) to B | PR diffs, branch comparisons |

**Critical:** Three-dot is almost always correct for PR/branch diffs. Two-dot includes the inverse of commits that exist on A but not B as spurious deletions.

### git log

| Syntax | Meaning | Use Case |
|--------|---------|----------|
| `git log A..B` | Commits reachable from B but not A | Commits ahead |
| `git log A...B` | Symmetric difference (either side, not both) | Divergence analysis |

### git rev-list

| Syntax | Meaning | Use Case |
|--------|---------|----------|
| `git rev-list A..B` | Count commits in B not in A | `count_commits_ahead` |

**Note:** Two-dot is correct for `git rev-list` commit counting.

## Diverged Branch Scenario

When feature branch diverges from base (base has new commits):

```
     main-only.txt (new)
           |
    main --+-- ... (diverged)
           \
            +-- feature.txt (new)
                feature branch
```

- `git diff main..feature`: Shows `feature.txt` added AND `main-only.txt` deleted (WRONG)
- `git diff main...feature`: Shows only `feature.txt` added (CORRECT)

## Source Pointers

- Correct implementation: See `packages/erk-shared/src/erk_shared/gateway/git/analysis_ops/real.py` (grep `get_diff_to_branch`)
- Correct two-dot usage for counting: Same file (grep `count_commits_ahead`)
- Integration test demonstrating difference: `tests/integration/test_real_git_analysis_ops.py`
```

---

#### 5. Integration test pattern for git operations with divergence

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8159]

**Draft Content:**

```markdown
## Integration Test Pattern: Git Operations with Branch Divergence

**When to use:** Testing git operations that compare branches, especially diff operations.

**Why:** Dict-based fakes cannot catch git command syntax errors (e.g., two-dot vs three-dot). Bugs manifest in the subprocess invocation string, which fakes abstract away.

**Pattern:**
1. Use `init_git_repo()` from `tests/integration/conftest.py`
2. Create initial commit on main
3. Create feature branch from initial commit
4. Add file on feature branch
5. Checkout main, add different file (creates divergence)
6. Return to feature branch
7. Test from feature branch that base's diverged commits don't appear in results

**Verification rigor (TDD confirmation):**
1. Run test with fix (passes)
2. Temporarily revert to old code
3. Verify test fails (proves discriminatory power)
4. Restore fix

**Source pointer:** See `tests/integration/test_real_git_analysis_ops.py` (grep `test_get_diff_to_branch_excludes_diverged_master_changes`)
```

---

#### 6. Dict-based fake limitations for git syntax

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## TRIPWIRE: Dict-Based Fakes Cannot Test Git Command Syntax

**Trigger:** Changing git command syntax in gateway operations

**Warning:** Dict-based fakes abstract away git command details and cannot catch syntax errors (e.g., two-dot vs three-dot). Add integration tests with real git repos.

**Example:** The two-dot vs three-dot bug in `get_diff_to_branch()` (PR #8159):
- Fake implementation uses pre-configured diff dict
- Bug was in the actual git command string: `git diff branch..HEAD` vs `git diff branch...HEAD`
- Fake would pass with either syntax because it doesn't invoke git

**When integration tests are required:**
- Git command syntax changes (two-dot vs three-dot)
- Flag changes that affect git behavior (--no-ff, --strategy, etc.)
- Any change where the bug would be in the subprocess invocation string

**Source pointer:** See `tests/integration/test_real_git_analysis_ops.py` for integration test structure.
```

---

### LOW Priority

#### 7. TDD verification workflow (revert-test-restore)

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Include as a callout within the integration test pattern section:

```markdown
> **Verification rigor:** After writing a regression test, prove it has discriminatory power:
> 1. Run test with fix (passes)
> 2. Temporarily revert to old code
> 3. Verify test fails
> 4. Restore fix
>
> This confirms the test actually catches the bug and isn't a false positive. Demonstrated in PR #8159 test coverage session.
```

---

## Contradiction Resolutions

### 1. large-diff-recovery.md showed three-dot but implementation used two-dot

**Existing doc:** `docs/learned/pr-operations/large-diff-recovery.md`
**Conflict:** Line 27 shows `git diff <base-branch>...HEAD` (three-dot) but the `get_diff_to_branch()` implementation was using two-dot.
**Resolution:** The documentation was aspirational/correct; the implementation was wrong. PR #8159 fixes the implementation to match the documentation. Add a note acknowledging this historical context (see HIGH Priority item #3).

### 2. Docstrings justified incorrect two-dot syntax

**Existing doc:** Docstrings in `abc.py` and `real.py` stated "two-dot syntax... is correct for PR diffs"
**Conflict:** This reasoning was incorrect. Two-dot is NOT correct for PR diffs when branches diverge.
**Resolution:** The docstrings were updated as part of PR #8159. The learn documentation should reference the CORRECTED docstrings and explain the semantic difference between two-dot and three-dot.

## Stale Documentation Cleanup

No standalone stale docs requiring deletion. The contradictions above were resolved IN THE CODE as part of the PR (docstrings updated). The large-diff-recovery.md update (HIGH Priority item #3) adds context without removing content.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Pre-existing CI Failure on Generated Docs

**What happened:** CI failed during implementation with `exec reference check` error. The `.claude/skills/erk-exec/reference.md` file was out of date.
**Root cause:** Generated reference docs drift from code without explicit regeneration. The drift was unrelated to the git diff fix being implemented.
**Prevention:** When CI fails during implementation, first check if the failure is related to your changes. If unrelated (different files, different check), fix the pre-existing issue separately before continuing.
**Recommendation:** TRIPWIRE (see HIGH Priority item #2)

### 2. Dict-Based Fakes Cannot Catch Command Syntax Bugs

**What happened:** Agent recognized that existing fake-based tests would not have caught the two-dot vs three-dot bug.
**Root cause:** Fakes use pre-configured dict responses and never invoke the actual git subprocess. The bug was in the command string itself.
**Prevention:** When changing git command syntax (arguments, flags, dot notation), add integration tests that run against real git repos.
**Recommendation:** TRIPWIRE (see MEDIUM Priority item #6)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Git Diff Two-Dot vs Three-Dot for PR Diffs

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before implementing git diff operations for PR or branch comparison
**Warning:** Use three-dot syntax (branch...HEAD) not two-dot (branch..HEAD). Three-dot diffs from merge-base, showing only feature branch changes. Two-dot compares tree states at tips, including inverse of diverged base commits as spurious files.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because the semantic difference is non-obvious (even experienced developers confuse `git log` three-dot behavior with `git diff` three-dot behavior), it affects any PR diff operation across the codebase, and the bug produces valid output that looks plausible -- no exception is thrown, just noisy diffs with spurious files. The original implementation even had docstrings that incorrectly justified two-dot syntax, showing how easy it is to rationalize the wrong approach.

### 2. Pre-existing CI Failures During Implementation

**Score:** 4/10 (Non-obvious +2, Repeated pattern +1, Silent failure +1)
**Trigger:** When CI fails during plan implementation
**Warning:** Don't assume CI failure is caused by your changes. Distinguish pre-existing failures from implementation-caused failures. For generated reference docs, run the generation command first.
**Target doc:** `docs/learned/ci/tripwires.md`

This is tripwire-worthy because agents naturally assume CI failures are caused by their changes. When implementing a focused fix (like two files for the git diff bug), an unrelated CI failure on generated docs can derail the session. The pattern appeared in this implementation and is likely to recur.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Dict-Based Fakes Cannot Test Git Command Syntax

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** This is specific to git operations and may be better expressed as testing guidance within the fake-driven testing documentation rather than a standalone tripwire. The core insight is that when changing subprocess invocation strings (not just behavior), fakes provide no protection. If additional instances of this pattern emerge (e.g., similar issues with `gh` CLI syntax), this could be promoted to a full tripwire.

## Key Insights

1. **Documentation can be aspirational**: `large-diff-recovery.md` showed the CORRECT three-dot syntax even when implementation was wrong. This validates that documentation can guide fixes, not just describe current state.

2. **Subtle bugs need integration tests**: Dict-based fakes are essential for fast unit testing, but command syntax bugs (two-dot vs three-dot) require integration tests against real tools.

3. **Git command semantics vary by command**: Three-dot has different meanings for `git diff` (merge-base), `git log` (symmetric difference), and `git rev-list` (commits ahead). Agents must understand these distinctions.

4. **Pre-existing failures are common**: Implementation sessions should expect unrelated CI failures, especially with generated docs. Pattern: identify, fix separately, then continue.

5. **Clear plans accelerate implementation**: Session efficiency metrics show that specific line numbers and file paths in the plan led to flawless execution (2 file edits, no errors, no rework).

6. **Verification rigor proves test value**: The revert-test-restore workflow (run with fix, revert, verify failure, restore) proves a test has discriminatory power and isn't a false positive.
