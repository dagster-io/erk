# Documentation Plan: Update PR Title for No-Changes Scenario

## Context

This implementation enhanced the erk-impl workflow's handling of "no code changes" scenarios by adding a visible `[no-changes]` prefix to PR titles. Previously, when an implementation attempt produced no code changes, the PR body was updated with diagnostic information but the title remained unchanged, making it difficult for users to identify failed implementations when scanning PR lists.

The implementation added a new `_build_no_changes_title()` function that formats titles as `[no-changes] P{issue_number} Impl Attempt: {original_title}`, and migrated from `update_pr_body()` to `update_pr_title_and_body()` to update both in a single API call. This change improves the erk-impl workflow's user experience by making failed implementations immediately visible without requiring users to click into each PR.

Documentation matters here because the PR title format is a user-facing convention that future agents and developers need to understand. Additionally, the remote implementation session revealed several error patterns during CI validation that warrant tripwire additions to prevent similar issues in future implementations.

## Raw Materials

https://gist.github.com/schrockn/5c73859cf9fbf50708a0d99d1158409b

## Summary

| Metric                    | Count |
| ------------------------- | ----- |
| Documentation items       | 1     |
| Contradictions to resolve | 0     |
| Tripwires to add          | 4     |

## Documentation Items

### HIGH Priority

#### 1. PR Title Format for No-Changes Scenario

**Location:** `docs/learned/planning/no-changes-handling.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## PR Title Format

When a plan implementation produces no code changes, the PR title is automatically prefixed to make it immediately visible in PR lists.

**Format:** `[no-changes] P{issue_number} Impl Attempt: {original_title}`

**Example:**

```
[no-changes] P5805 Impl Attempt: Update PR Title for No-Changes Scenario
```

**When applied:** During the `handle-no-changes` workflow step, after the PR body has been updated with diagnostic information.

**Why this matters:** Users reviewing large lists of PRs can immediately identify failed implementations without clicking into each PR. The `[no-changes]` prefix makes it clear that the erk-impl workflow ran but produced no code changes, helping with triage and issue diagnosis.

**Implementation reference:** See `_build_no_changes_title()` in `src/erk/cli/commands/exec/scripts/handle_no_changes.py`.
```

---

## Contradiction Resolutions

**Status:** No contradictions found. All existing documentation is consistent with the implementation. The PR title enhancement is purely additive and builds on the existing `no-changes-handling.md` document.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Function Signature Breaking Changes

**What happened:** The remote implementation session encountered test failures when `update_plan_header_learn_result()` signature was modified but 7 tests still used the old 3-parameter call pattern.
**Root cause:** Required kwargs were added to shared utility functions without atomically updating all callers.
**Prevention:** Ensure all callers (tests, commands, other modules) are updated in the same commit when changing function signatures.
**Recommendation:** TRIPWIRE

### 2. Fake Gateway Attribute Tracking Mismatch

**What happened:** Type checker (`ty`) identified that test code referenced `GitHubIssues.added_comments` attribute that didn't exist on the fake implementation.
**Root cause:** Tests were written against an API contract that the fake didn't implement yet.
**Prevention:** Before writing test assertions on fake objects, verify the fake has all required tracking attributes.
**Recommendation:** TRIPWIRE

### 3. Import Path Refactoring Without Test Updates

**What happened:** `_get_erk_package_dir` was refactored from `sync.py` to `paths.py`, but test imports weren't updated, causing `ImportError`.
**Root cause:** Helper function moves to new modules without atomic import updates.
**Prevention:** When moving internal helper functions, update all test imports atomically.
**Recommendation:** TRIPWIRE

### 4. __pycache__ Name Collisions in CI

**What happened:** Multiple `test_context.py` modules in different directories caused import ambiguity due to stale `__pycache__` directories.
**Root cause:** pytest collection found cached modules from different locations causing import collisions.
**Prevention:** CI setup should clean `__pycache__` directories before pytest runs.
**Recommendation:** TRIPWIRE (LOW priority - CI-specific)

---

## Tripwire Additions

### Tripwire 1: Function Signature Breaking Changes

**Add to:** `docs/learned/tripwires.md`

```
**CRITICAL: Before changing signatures of shared utility functions → Ensure all callers (tests, commands, other modules) are updated atomically in the same commit. Missing updates cause test failures and type errors. Run full test suite before committing.**

Source: Issue #5805 - `update_plan_header_learn_result()` signature change affected 7 test call sites.
```

### Tripwire 2: Fake Gateway Attribute Tracking

**Add to:** `docs/learned/testing/fake-driven-testing.md`

```
**CRITICAL: Before writing test assertions that reference tracking attributes on fake gateway objects → Verify the fake implementation has all required attributes before writing assertions. Test-driven development requires updating both the test expectations AND the fake in parallel.**

Source: Issue #5805 - Tests referenced `GitHubIssues.added_comments` attribute that didn't exist on fake implementation.
```

### Tripwire 3: Import Path Refactoring

**Add to:** `docs/learned/tripwires.md`

```
**CRITICAL: Before moving internal helper functions to new modules → Update all test imports atomically. Check for imports of the function name across the codebase and update them in the same commit to prevent ImportError during test collection.**

Source: Issue #5805 - `_get_erk_package_dir` refactored to paths.py but test imports still referenced sync.py.
```

### Tripwire 4: __pycache__ Name Collisions in CI

**Add to:** CI setup documentation (`.github/workflows/` or `docs/learned/ci/`)

```
**CRITICAL: Before running pytest in CI without cleaning __pycache__ → Add 'find . -type d -name __pycache__ -delete' before pytest runs. Stale __pycache__ directories can cause import name collisions when test files with the same name exist in different directories.**

Source: Issue #5805 - Multiple `test_context.py` modules in different directories caused import ambiguity.
```

---

## Implementation Instructions

### Primary Documentation Update (Required)

1. Open `docs/learned/planning/no-changes-handling.md`
2. Add the "PR Title Format" section from the draft content above
3. Place it after the "Workflow Response" section and before any implementation details
4. Verify the example matches the actual implementation in `handle_no_changes.py:_build_no_changes_title()`

### Tripwire Additions (Secondary - Preventive)

1. Add Tripwire 1 (Function Signature Breaking Changes) to `docs/learned/tripwires.md`
2. Add Tripwire 2 (Fake Gateway Attribute Tracking) to `docs/learned/testing/fake-driven-testing.md`
3. Add Tripwire 3 (Import Path Refactoring) to `docs/learned/tripwires.md`
4. Add Tripwire 4 (__pycache__ Collisions) to relevant CI documentation

**Note on Tripwire Additions:** These are based on errors discovered during implementation CI validation. They represent valuable patterns for preventing similar issues in future work. If time-constrained, focus on the primary documentation update; tripwires can be added later.

---

## Verification Checklist

- [x] Existing documentation is comprehensive and mostly complete
- [x] Zero contradictions between new feature and existing docs
- [x] Single focused documentation gap identified (PR title format)
- [x] Prevention patterns discovered and documented for future use
- [x] All code changes are working correctly (20 tests pass, no regressions)
- [x] Feature improves user experience (visibility in PR lists)