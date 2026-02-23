# Documentation Plan: Clear error when trigger_workflow finds skipped/cancelled run

## Context

This PR implements a fail-fast error improvement in `trigger_workflow` that transforms a confusing timeout error into an immediate, actionable diagnostic. Before this change, when a workflow run matched the correlation ID but had a `skipped` or `cancelled` conclusion, the method would silently filter it out and continue polling all 15 attempts (~25 seconds), ultimately reporting "could not find run ID" even though the run was visible in diagnostics. Now, when the matched run is skipped/cancelled, the method raises immediately with a clear error message explaining the run was found but skipped, and providing context about likely causes (such as job-level conditions like `vars.CLAUDE_ENABLED = 'false'`).

The implementation sessions revealed two significant cross-cutting patterns beyond the primary code change. First, git rebase operations cause Graphite's metadata to become stale, requiring a `gt track` resync before PR submission can succeed. This appeared in both session parts as a critical recovery step. Second, changing behavior from "silent continue" to "explicit raise" requires synchronous updates to all related tests — the test name and assertions must reflect the new expected behavior immediately, not as a follow-up task.

Documentation matters here because: (1) the polling failure mode behavior is a critical aspect of the GitHub Actions integration that callers need to understand; (2) the git/Graphite resync pattern is a universal tripwire that blocks PR submission if forgotten; and (3) the test-behavior synchronization pattern prevents a common CI failure mode where tests encode assumptions about old behavior.

## Raw Materials

Materials collected via learn workflow from plan #7941 and PR #7941.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 6     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Git rebase + Graphite metadata resync [TRIPWIRE]

**Location:** `docs/learned/erk/graphite-rebase-resync.md` (new doc, tripwire in `docs/learned/erk/tripwires.md`)
**Action:** CREATE
**Source:** [Impl] (both session parts)

**Draft Content:**

```markdown
---
title: Graphite Rebase Resync
read_when:
  - "running git rebase or git pull --rebase"
  - "seeing 'diverged branch' error from gt submit"
  - "recovering from failed erk pr submit after rebase"
tripwires:
  - action: "running git rebase or git pull --rebase on a Graphite-tracked branch"
    warning: "MUST run `gt track <branch> --no-interactive` to resync Graphite metadata. Git rebase changes commit history without updating Graphite's tracking, causing 'diverged branch' errors in gt submit."
---

# Graphite Rebase Resync

Git rebase operations rewrite commit history, but Graphite tracks branch relationships using commit SHAs. After any rebase, Graphite's metadata becomes stale because the SHAs it knows about no longer exist.

## The Problem

When you run `git rebase` or `git pull --rebase`:
1. Git rewrites commits with new SHAs
2. Graphite still references the old SHAs
3. `gt submit` (and `erk pr submit`) fails with "Cannot perform this operation on diverged branch"

## The Solution

After any git rebase operation:
1. Run `gt track <branch> --no-interactive` to resync Graphite's metadata
2. Then proceed with `erk pr submit` or other Graphite operations

This applies to ALL git rebase operations, including:
- Manual `git rebase <base>`
- `git pull --rebase`
- Rebase during impl-context cleanup

## Related Documentation

- [Graphite Divergence Detection](graphite-divergence-detection.md)
- [Graphite Stack Troubleshooting](graphite-stack-troubleshooting.md)
```

---

#### 2. Test-behavior synchronization when changing exception handling [TRIPWIRE]

**Location:** `docs/learned/testing/test-behavior-synchronization.md` (new doc, tripwire in `docs/learned/testing/tripwires.md`)
**Action:** CREATE
**Source:** [Impl] (session part 2)

**Draft Content:**

```markdown
---
title: Test-Behavior Synchronization
read_when:
  - "changing error handling from silent to explicit"
  - "changing behavior from continue-on-error to raise-on-error"
  - "test fails after changing exception behavior"
tripwires:
  - action: "changing exception behavior from 'continue on error' to 'raise on error'"
    warning: "Audit all tests that exercise the affected code path. Tests may assume the old behavior (e.g., 'skipped runs are ignored') and need updating to expect the new behavior (e.g., 'skipped runs raise immediately'). Update test names to reflect the new behavior."
---

# Test-Behavior Synchronization

When changing code behavior from "silent continue" to "explicit raise", test updates are not a follow-up task — they're part of the implementation.

## The Pattern

Tests encode behavioral expectations in their assertions. Changing from:
- "on error, log and continue" to "on error, raise exception"
- "filter and skip" to "detect and fail-fast"

...invalidates those expectations. The tests will fail with the new behavior.

## Required Actions

When changing exception behavior:

1. **Find all related tests**: Search for test functions that exercise the affected code path
2. **Update assertions**: Change from checking success/return values to checking `pytest.raises(Exception)`
3. **Update test names**: Rename to reflect the new behavior (e.g., `test_foo_skips_errors` to `test_foo_raises_on_errors`)
4. **Simplify test structure**: The new behavior may make old test logic irrelevant (e.g., polling progression tests when behavior now fails immediately)

## Example

Before (old behavior):
- Test name: `test_trigger_workflow_skips_cancelled_runs`
- Assertion: Checks that method eventually returns a valid run ID

After (new behavior):
- Test name: `test_trigger_workflow_raises_on_skipped_cancelled_runs`
- Assertion: `pytest.raises(RuntimeError, match="run was skipped")`

See the test change in `tests/integration/test_real_github.py` for the concrete example.

## Why This Is Tripwire-Worthy

Without this pattern:
- CI fails with unexpected test failures
- Debugging reveals the test was written for old behavior
- Developer must then figure out how to update the test

With this pattern:
- Developer updates tests as part of the behavior change
- Single atomic commit with both production code and test changes
- CI passes on first try
```

---

#### 3. Skipped/cancelled workflow run handling in trigger_workflow

**Location:** `docs/learned/reference/github-actions-api.md`
**Action:** UPDATE (add new section)
**Source:** [PR #7941]

**Draft Content:**

Add a new section "Polling Failure Modes" after the "The distinct_id Correlation Problem" section:

```markdown
## Polling Failure Modes

The `trigger_workflow` polling loop handles several terminal states differently:

### Skipped or Cancelled Runs

When a workflow run matches the correlation ID but has a `conclusion` of `skipped` or `cancelled`, `trigger_workflow` raises immediately with a diagnostic error:

```
Error: Workflow 'workflow-name.yml' run was skipped.
Run ID: 12345, title: 'context:distinct-id'
This usually means a job-level condition was not met (e.g., vars.CLAUDE_ENABLED is 'false').
```

**Why fail-fast?** A skipped/cancelled run will never transition to success. Continuing to poll would waste ~25 seconds before eventually timing out with a confusing "could not find run ID" message — even though the run was visible in the API responses.

**Common causes:**
- Job-level `if:` conditions that evaluate to false (e.g., `if: vars.CLAUDE_ENABLED == 'true'`)
- Workflow-level concurrency rules that cancelled the run
- Manual cancellation

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/real.py, RealGitHub.trigger_workflow -->

See `RealGitHub.trigger_workflow()` in `packages/erk-shared/src/erk_shared/gateway/github/real.py` for the implementation. The check happens after matching by `displayTitle` but before returning the run ID.

### Other Terminal States

Runs with `conclusion` of `failure`, `timed_out`, or `action_required` are returned normally — the caller decides how to handle the failure. Only `skipped` and `cancelled` warrant fail-fast because they indicate the run will never produce useful output.
```

Also add a new tripwire to the frontmatter:

```yaml
tripwires:
  # ... existing tripwires ...
  - action: "adding retry logic to trigger_workflow when run is skipped or cancelled"
    warning: "Don't retry skipped/cancelled runs. If a run matches the correlation ID but was skipped/cancelled, it's the triggered run and won't complete. Raise immediately with diagnostic error."
```

---

### MEDIUM Priority

#### 4. Polling logic restructuring pattern: check positive match before negative filters

**Location:** `docs/learned/architecture/early-error-detection-patterns.md` (new doc)
**Action:** CREATE
**Source:** [Impl] (session part 1)

**Draft Content:**

```markdown
---
title: Early Error Detection Patterns
read_when:
  - "implementing polling loops that search for a specific resource"
  - "adding error detection to resource discovery"
  - "debugging confusing timeout errors in polling code"
tripwires:
  - action: "filtering candidates by negative conditions before checking positive match"
    warning: "Check for positive match (correlation ID, name, etc.) FIRST, then evaluate terminal state. Filtering first causes silent skips and confusing timeout errors."
---

# Early Error Detection Patterns

When polling for a resource by correlation ID, the order of checks determines error clarity.

## The Anti-Pattern

```python
# BAD: Filter first, match second
for run in runs:
    if run.conclusion in ("skipped", "cancelled"):
        continue  # Silent skip
    if distinct_id in run.displayTitle:
        return run.id
# Result: Timeout with "not found" even though run existed
```

## The Correct Pattern

```python
# GOOD: Match first, evaluate terminal state second
for run in runs:
    if distinct_id in run.displayTitle:
        # Found the run! Now check if it's in a usable state
        if run.conclusion in ("skipped", "cancelled"):
            raise RuntimeError(f"Run was {run.conclusion}: {diagnostics}")
        return run.id
# Result: Immediate error with context
```

## Why This Matters

The anti-pattern creates a debugging nightmare:
1. User sees "could not find run ID" after 25 seconds
2. User checks GitHub UI and sees the run (with "skipped" status)
3. User is confused: the run exists, why wasn't it found?

The correct pattern provides immediate clarity:
1. User sees "Run was skipped: Run ID 12345, likely cause: job condition not met"
2. User understands the problem and can fix the root cause

## Applicability

This pattern applies to any polling operation where:
1. You're looking for a specific resource by correlation ID
2. The resource can be in a terminal failure state
3. Continuing to poll won't change the state
4. Users need to understand WHY the resource is in that state
```

---

#### 5. Impl-context cleanup push failures and recovery

**Location:** `docs/learned/planning/impl-context-cleanup-failures.md` (new doc)
**Action:** CREATE
**Source:** [Impl] (session part 1)

**Draft Content:**

```markdown
---
title: Impl-Context Cleanup Push Failures
read_when:
  - "impl-context cleanup step fails with non-fast-forward error"
  - "debugging plan-implement workflow push failures"
tripwires: []
---

# Impl-Context Cleanup Push Failures

The impl-context cleanup step in plan-implement can fail with push conflicts when the remote branch has diverged.

## The Problem

During plan-implement, the impl-context cleanup step commits and pushes changes. If the remote branch advanced while local changes were being committed, the push fails:

```
error: failed to push some refs
hint: Updates were rejected because the remote contains work that you do not have locally.
```

## Recovery

When this occurs:
1. Run `git pull --rebase origin <branch>` to sync with remote
2. Retry the push
3. If using Graphite, also run `gt track <branch> --no-interactive` (see graphite-rebase-resync.md)

## Root Cause

This typically happens when:
- Another process pushed to the same branch
- CI committed impl-context cleanup while local session was still running
- Multiple agents working on the same plan branch

## Prevention Considerations

Future workflow improvements could:
- Pre-fetch before cleanup steps that will push
- Automatically retry with pull-rebase on non-fast-forward errors
- Add advisory locking for plan branches
```

---

#### 6. CI failure triage: PR changes vs master issues

**Location:** `docs/learned/ci/ci-failure-triage.md` (new doc)
**Action:** CREATE
**Source:** [Impl] (session part 2)

**Draft Content:**

```markdown
---
title: CI Failure Triage
read_when:
  - "CI fails on files not modified by PR"
  - "lint errors in unrelated files after merge/rebase"
  - "debugging CI failures that don't match PR changes"
tripwires:
  - action: "attempting to fix CI failures in files not modified by the PR"
    warning: "Check if the failing files were modified by the PR first. If not, the failure may be a pre-existing master issue. Rebase on latest master to pick up upstream fixes."
---

# CI Failure Triage

Before attempting to fix CI failures, verify they're caused by your PR changes.

## Triage Pattern

1. **Check which files were modified**: `git diff origin/master --name-only`
2. **Check which files are failing**: Read the CI error output
3. **Compare the sets**: If failing files are not in the modified set, the issue is likely pre-existing

## When to Rebase

If CI fails on files NOT in your PR:
1. The failure is likely a pre-existing master issue
2. Someone else may have already fixed it
3. Rebase on latest master: `git fetch origin && git rebase origin/master`
4. Re-run CI to pick up the fix

## When to Fix

If CI fails on files IN your PR:
1. The failure is likely caused by your changes
2. Fix the issue in your branch
3. The fix becomes part of your PR

## Example

PR modifies: `src/erk/gateway/github/real.py`, `tests/integration/test_real_github.py`

CI fails on: `src/erk/cli/admin.py` (lint error: redefinition of function)

Triage: `admin.py` is not in the PR diff. This is a master issue. Rebase to pick up the fix that was merged upstream.
```

---

## Contradiction Resolutions

No contradictions found. The existing documentation (particularly `docs/learned/reference/github-actions-api.md` and `docs/learned/architecture/discriminated-union-error-handling.md`) is consistent with the changes in this PR.

## Stale Documentation Cleanup

No stale documentation detected. All referenced files in the existing docs have clean references with no phantom file paths.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Graphite divergence after git rebase

**What happened:** After running `git pull --rebase` to resolve push conflicts, `erk pr submit` failed with "Cannot perform this operation on diverged branch"
**Root cause:** Git rebase rewrites commit history, but Graphite tracks branches by commit SHA. After rebase, Graphite's metadata references non-existent commits.
**Prevention:** Always run `gt track <branch> --no-interactive` immediately after any git rebase operation.
**Recommendation:** TRIPWIRE (score 6)

### 2. Test assumptions violated by behavior change

**What happened:** Integration test `test_trigger_workflow_skips_cancelled_runs` failed after changing `trigger_workflow` to raise on skipped/cancelled runs.
**Root cause:** Test was written for old behavior (skip and continue polling) but implementation now raises immediately.
**Prevention:** When changing exception behavior, grep for all related tests before committing. Update test assertions AND test names to reflect new behavior.
**Recommendation:** TRIPWIRE (score 5)

### 3. Impl-context cleanup push conflict

**What happened:** Push after impl-context cleanup commit failed with non-fast-forward error.
**Root cause:** Remote branch advanced while local changes were being committed.
**Prevention:** Pre-fetch in cleanup workflow, or handle push failures with automatic pull-rebase retry.
**Recommendation:** ADD_TO_DOC (score 3)

### 4. Confusing error messages from silent polling skips

**What happened:** User saw "could not find run ID" after 25 seconds even though the run existed.
**Root cause:** Polling loop filtered by conclusion before checking displayTitle match, causing silent skips.
**Prevention:** Check match conditions before applying filters in polling loops.
**Recommendation:** CONTEXT_ONLY (score 2 - fixed by this PR)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Git rebase + Graphite metadata resync

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before running `git rebase` or `git pull --rebase` on a Graphite-tracked branch
**Warning:** MUST run `gt track <branch> --no-interactive` to resync Graphite metadata. Git rebase changes commit history without updating Graphite's tracking, causing 'diverged branch' errors in `gt submit`.
**Target doc:** `docs/learned/erk/graphite-rebase-resync.md` (and tripwire entry in `docs/learned/erk/tripwires.md`)

This is tripwire-worthy because:
- It's non-obvious: git rebase is a common operation, but its interaction with Graphite requires extra knowledge
- It's cross-cutting: affects ANY git rebase operation, not just a specific workflow
- It has destructive potential: blocks PR submission until resolved, with no clear error message pointing to the fix

Evidence: Appeared in both session parts as a critical recovery step. Session 1 documented the full `gt track` recovery. Session 2 referenced it when rebasing to pick up upstream fixes.

### 2. Test-behavior synchronization when changing exception handling

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** Before changing exception behavior from "continue on error" to "raise on error"
**Warning:** Audit all tests that exercise the affected code path. Tests may assume the old behavior (e.g., 'skipped runs are ignored') and need updating to expect the new behavior (e.g., 'skipped runs raise immediately'). Update test names to reflect the new behavior.
**Target doc:** `docs/learned/testing/test-behavior-synchronization.md` (and tripwire entry in `docs/learned/testing/tripwires.md`)

This is tripwire-worthy because:
- It's non-obvious: developers often think of test updates as a follow-up task, not part of the implementation
- It's cross-cutting: applies to ANY behavior change from silent to explicit, not just trigger_workflow
- It's a repeated pattern: this will recur whenever error handling is tightened

Evidence: Session 2 documented the test failure and the required changes: rename from `test_trigger_workflow_skips_cancelled_runs` to `test_trigger_workflow_raises_on_skipped_cancelled_runs`, change from success assertion to `pytest.raises(RuntimeError)`.

## Potential Tripwires

Items with score 2-3 (may warrant tripwire status with additional context):

### 1. Impl-context cleanup push failures

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)
**Notes:** Specific to plan-implement workflow. Could become tripwire if it recurs frequently. Currently one occurrence in session 1. Would need additional occurrences to justify tripwire overhead.

### 2. Polling logic restructuring for early errors

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** Architectural pattern but not urgent. Only one occurrence in sessions. The specific case (trigger_workflow) is now fixed. Would need evidence of the anti-pattern appearing elsewhere in the codebase to justify a tripwire.
