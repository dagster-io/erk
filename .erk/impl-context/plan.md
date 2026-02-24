# Documentation Plan: Set lifecycle_stage to "impl" in PR submit and rewrite pipelines

## Context

This PR (#8014) addresses a gap in lifecycle tracking where plans submitted via `erk pr submit` or `erk pr rewrite` could remain stuck at earlier stages like "planned" instead of advancing to "impl". Previously, only plans implemented through the formal `/erk:plan-implement` pipeline had their lifecycle stages updated correctly via `impl-signal.py`. Users who bypass the formal pipeline by coding first and then submitting would have inconsistent lifecycle tracking.

The implementation adds a shared helper function `maybe_advance_lifecycle_to_impl()` that acts as a "catch-up mechanism" - it advances plans from pre-implementation stages (`None`, `"prompted"`, `"planning"`, `"planned"`) to `"impl"` during PR operations. This ensures consistent lifecycle tracking regardless of which workflow path the user takes. The function follows a "best-effort, never-block" pattern: it attempts the update but silently returns on failure, ensuring metadata operations never interfere with core PR submission workflows.

Documentation is needed to: (1) clarify terminology around the abbreviated `"impl"` field value vs. the conceptual "implementing" stage name, (2) document the new Phase 6 behavior in both PR pipelines, and (3) explain the catch-up mechanism pattern for future maintainers.

## Raw Materials

PR #8014

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 8     |
| Contradictions to resolve      | 1     |
| Tripwire candidates (score>=4) | 0     |
| Potential tripwires (score2-3) | 1     |

## Documentation Items

### HIGH Priority

#### 1. Clarify lifecycle_stage field value terminology

**Location:** `docs/learned/planning/lifecycle.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8014]

**Draft Content:**

```markdown
<!-- Add after line 1037, before "The field is nullable" paragraph -->

**Field Value Convention:** The metadata field stores abbreviated stage values. The `implementing` stage is stored as `"impl"` in the `lifecycle_stage` field. Code that checks or sets this field uses the abbreviated form (e.g., `lifecycle_stage: "impl"`).

<!-- Update the Write Points table (lines 1045-1052) to replace implementing/implemented rows -->

| Stage    | Set By                                                                      | When                                        |
| -------- | --------------------------------------------------------------------------- | ------------------------------------------- |
| impl     | `mark-impl-started`, `maybe_advance_lifecycle_to_impl`                      | Implementation begins (local, remote, or catch-up) |

<!-- Add new subsection after Write Points -->

### Catch-up Mechanism

Plans may reach implementation through different paths:

1. **Formal path:** `/erk:plan-implement` sets `lifecycle_stage` via `impl-signal.py`
2. **Direct path:** User codes first, then runs `erk pr submit` or `erk pr rewrite`

For the direct path, the `maybe_advance_lifecycle_to_impl()` function in `src/erk/cli/commands/pr/shared.py` acts as a catch-up mechanism. It advances plans from pre-impl stages (`{None, "prompted", "planning", "planned"}`) to `"impl"` during PR operations, ensuring consistent lifecycle tracking regardless of workflow path.

The function follows a "best-effort, never-block" pattern: it attempts the update but silently returns on failure, ensuring metadata operations never interfere with core PR submission.
```

#### 2. Add lifecycle update to PR submit Phase 6

**Location:** `docs/learned/pr-operations/pr-submit-phases.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8014]

**Draft Content:**

```markdown
<!-- Add at end of Phase 6 section, after the Two-Target Pattern paragraph (around line 117) -->

**Lifecycle Advancement:** Phase 6 also calls `maybe_advance_lifecycle_to_impl()` to advance linked plans from pre-implementation stages to `"impl"`. This serves as a catch-up mechanism for plans submitted without going through `/erk:plan-implement`. The update is best-effort and never blocks submission. See `src/erk/cli/commands/pr/shared.py` for implementation.
```

#### 3. Add lifecycle update to PR rewrite Phase 6

**Location:** `docs/learned/cli/pr-rewrite.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8014]

**Draft Content:**

```markdown
<!-- Add to the 6-Phase Pipeline list item 6, after "updates PR title/body on GitHub" -->

6. **Push and update PR** — Force-pushes via `branch_manager.submit_branch()`, updates PR title/body on GitHub, and advances linked plan lifecycle to `"impl"` via `maybe_advance_lifecycle_to_impl()`

<!-- Add to Key Behaviors section -->

**Lifecycle advancement**: After updating the PR, calls `maybe_advance_lifecycle_to_impl()` to advance linked plans from pre-implementation stages to `"impl"`. This catch-up mechanism ensures consistent lifecycle tracking for plans submitted without using `/erk:plan-implement`.
```

#### 4. Document best-effort operation pattern

**Location:** `docs/learned/architecture/error-handling-patterns.md` (CREATE)
**Action:** CREATE
**Source:** [Impl], [PR #8014]

**Draft Content:**

```markdown
---
title: Error Handling Patterns
read_when:
  - "implementing operations that should not block primary workflows"
  - "deciding when to catch RuntimeError"
  - "implementing graceful degradation for metadata operations"
---

# Error Handling Patterns

## Best-Effort, Never-Block Pattern

For auxiliary operations (like metadata updates) that should not interfere with primary workflows:

1. **Attempt the operation** within a try block
2. **Catch broad exceptions** (including `RuntimeError` from gateway operations)
3. **Log a warning** (unless quiet mode) but never re-raise
4. **Return silently** on failure

**When to use:**
- Metadata updates during PR operations
- Lifecycle stage advancement
- Analytics or telemetry
- Cache updates

**When NOT to use:**
- CLI validation (fail fast with clear errors)
- Core business logic (let errors propagate)
- User-requested operations (report failures)

**Example:** See `maybe_advance_lifecycle_to_impl()` in `src/erk/cli/commands/pr/shared.py` - advances plan lifecycle but never blocks PR submission.

## Gateway RuntimeError Handling

Gateway operations may raise `RuntimeError` for transient failures (network issues, API rate limits). The handling depends on context:

**Acceptable to catch:** Best-effort metadata operations, graceful degradation paths
**Not acceptable to catch:** CLI validation, operations where failure should be visible

Always distinguish between operations where failure should be silent vs. operations where failure should be reported.
```

### MEDIUM Priority

#### 5. Document test coverage standards for state transitions

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [PR #8014]

**Draft Content:**

```markdown
<!-- Add new section after "Test Requirements for Code Changes" -->

## Testing State Transitions

Functions that transition between states (like lifecycle stages) need comprehensive edge case coverage:

| Edge Case | Example Test |
|-----------|--------------|
| **All valid source states** | Test advancement from each of `{None, "prompted", "planning", "planned"}` |
| **Idempotency** | Test that calling when already at target state is a no-op |
| **Missing entity** | Test graceful handling when the entity doesn't exist |
| **Already-at-target** | Test no mutation when already at the target state |

**Pattern:** Create a parameterized test for source states, plus dedicated tests for edge cases. See `tests/unit/cli/commands/pr/test_lifecycle_update.py` for an example.
```

#### 6. Add LBYL conditional assignment pattern to dignified-python skill

**Location:** `.claude/skills/dignified-python.md`
**Action:** CODE_CHANGE (skill update)
**Source:** [PR #8014] (review comment)

**Draft Content:**

The automated review caught a conditional assignment anti-pattern:

```python
# WRONG: assign in if, use unconditionally
if not quiet:
    msg = "Updating lifecycle..."
echo(msg)  # NameError if quiet=True

# CORRECT: assign unconditionally OR guard both
msg = "Updating lifecycle..."
if not quiet:
    echo(msg)
```

Add this pattern to the dignified-python skill under a "Conditional Assignment" section. The pattern violates the LBYL principle because the variable's existence depends on runtime conditions.

### LOW Priority

#### 7. Add cross-reference from PR body assembly doc

**Location:** `docs/learned/architecture/pr-body-assembly.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
<!-- Add to Key Functions section if it exists, or create one -->

## Related Functions

- `maybe_advance_lifecycle_to_impl()` - Shared utility in `shared.py` that advances plan lifecycle to "impl" during PR operations. Used by both submit and rewrite pipelines.
```

#### 8. Document automated review workflow cycle times

**Location:** `docs/learned/ci/automated-review-workflow.md` (if exists) or skip
**Action:** UPDATE or SKIP
**Source:** [PR #8014] (activity logs)

The PR demonstrated a 1 hour 13 minute cycle time from violation detection (16:52) to fix (17:00) to verification (18:05). This could be documented as a benchmark for the automated review workflow effectiveness, but is lower priority since it's process documentation rather than code pattern documentation.

## Contradiction Resolutions

### 1. Lifecycle Stage Field Value Terminology

**Existing doc:** `docs/learned/planning/lifecycle.md` (lines 1031-1052)
**Conflict:** Documentation shows five stage names (`prompted`, `planning`, `planned`, `implementing`, `implemented`) in the Stage Values table, but the actual field value stored is `"impl"` (abbreviated), not `"implementing"`. The Write Points table shows `implemented` set by `handle-no-changes`, but the PR reveals this should be `impl` set by `maybe_advance_lifecycle_to_impl`.
**Resolution:** Update the Stage Values table to clarify that `implementing` stage is stored as `"impl"` field value. Update the Write Points table to show `impl` is set by both `mark-impl-started` and the new `maybe_advance_lifecycle_to_impl` function. Add a note explaining the abbreviation convention.

**Evidence:**
- Code in `src/erk/cli/commands/pr/shared.py:168` sets `lifecycle_stage: "impl"`
- Test in `test_mark_impl_started_ended.py:135` asserts `block.data["lifecycle_stage"] == "impl"`
- `_STAGES_BEFORE_IMPL` set includes `{None, "prompted", "planning", "planned"}`, confirming "impl" comes after planning

## Stale Documentation Cleanup

No stale documentation detected. All referenced files and code patterns in existing docs are current.

## Prevention Insights

### 1. LBYL Conditional Assignment Violation

**What happened:** The initial implementation assigned a message variable inside an `if not quiet:` block but used it unconditionally in the `echo()` call outside the block.
**Root cause:** Violates LBYL - variable existence depends on runtime condition but usage assumes it always exists.
**Prevention:** Always assign variables unconditionally, then conditionally use them. Or guard both assignment and usage with the same condition.
**Recommendation:** ADD_TO_DOC (dignified-python skill)

## Tripwire Candidates

No items scored >= 4. The primary pattern (catch-up mechanism) is an architecture-level pattern that deserves documentation but is not a tripwire because:
- It's additive, not destructive
- Failure is explicitly designed to be non-blocking
- It's specific to PR pipeline integration, not cross-cutting

## Potential Tripwires

### 1. Gateway RuntimeError catching for graceful degradation

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)
**Notes:** The pattern of catching `RuntimeError` from gateway operations is generally discouraged but acceptable for best-effort metadata operations. Did not meet threshold because:
- Not cross-cutting enough (specific to metadata operations)
- Failure is explicitly designed to be non-blocking
- First occurrence of this specific pattern

Better as expanded guidance in error handling documentation rather than a new tripwire. Future occurrences of this pattern could promote it to tripwire status.

## Cornerstone Redirects (SHOULD_BE_CODE)

The following items belong in code artifacts, not learned documentation:

| Item | Recommended Action | Rationale |
|------|-------------------|-----------|
| `_STAGES_BEFORE_IMPL` constant value | None - keep in code only | Enumerable set of stage names belongs in code as constant, not docs |
| `maybe_advance_lifecycle_to_impl()` signature | Add docstring to function | Single-artifact API belongs in code docstring (already has one) |
| LBYL conditional assignment pattern | Add to dignified-python skill | Single-location coding guidance belongs in coding standards |
