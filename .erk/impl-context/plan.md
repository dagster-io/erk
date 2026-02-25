# Documentation Plan: Fix plan-save to base branch off current branch, not always trunk

## Context

This implementation fixed a critical stacking bug in erk's plan-save workflow. When users saved plans while on feature branches, the plan branch was always created from `origin/trunk`, but checkout later tried to track the plan with the user's current feature branch as the parent. This caused `gt track` failures with "parent is not in history" errors because the plan branch's git ancestry didn't include the intended Graphite parent.

The fix introduces context-aware branch base selection: plans created from feature branches now use that feature branch as the base (enabling natural Graphite stacking), while plans created from trunk continue using `origin/trunk`. A key architectural shift was moving from runtime inference (guessing the parent at checkout time) to design-time declaration (storing the parent in plan metadata during plan-save). This makes behavior deterministic regardless of which branch the user is on when they later check out the plan.

Future agents working with plan metadata, test helpers that convert between domain types, or Graphite branch tracking will benefit from understanding these patterns. The implementation revealed several subtle bugs including metadata key mismatches across components and type narrowing limitations that are valuable prevention insights.

## Raw Materials

PR #8103

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 8 |
| Contradictions to resolve | 1 |
| Tripwire candidates (score>=4) | 2 |
| Potential tripwires (score 2-3) | 2 |

## Contradiction Resolutions

### 1. Plan-save branch base selection documentation vs implementation

**Existing doc:** `docs/learned/planning/lifecycle.md` (lines 313-332) and `docs/learned/planning/learn-vs-implementation-plans.md` describe learn plans stacking on parent implementation branches via submit.py
**Conflict:** The old implementation in `plan_save.py:177-181` always created branches from `origin/trunk` with a comment "to avoid false stacking", contradicting the documented stacking model
**Resolution:** UPDATE both docs to reflect the new conditional behavior:
- On feature branch: base plan branch from current branch (enables natural stacking at plan-save time)
- On trunk/detached HEAD: base from `origin/trunk` (traditional isolation behavior)

This resolves the contradiction by documenting the actual new behavior and clarifying that stacking now happens during plan-save, not at submit time.

## Documentation Items

### HIGH Priority

#### 1. Metadata key consistency across components

**Location:** `docs/learned/architecture/cross-component-data-contracts.md` (new)
**Action:** CREATE
**Source:** [PR #8103]

**Draft Content:**

```markdown
---
read-when:
  - adding or renaming metadata fields that flow between components
  - debugging metadata that appears to be missing or ignored
  - working with plan metadata, PR details, or similar cross-component data
tripwires: 1
---

# Cross-Component Data Contracts

When data flows across components (writer -> storage -> reader), all locations must use identical key names. This is especially critical for dictionary-based metadata.

## The 3-Place Pattern

The `base_ref_name` rename in PR #8103 demonstrates this pattern:

1. **Writer:** `plan_save.py` sets `metadata["base_ref_name"] = base_branch`
2. **Storage:** `planned_pr.py` reads `metadata.get("base_ref_name")` when creating the PR
3. **Reader:** `checkout_cmd.py` reads `plan.metadata.get("base_ref_name")` to determine parent

All three must use the same key. If the writer uses `trunk_branch` but the reader expects `base_ref_name`, data is silently lost.

## Prevention

Before adding or renaming metadata fields:
- Grep codebase for all read/write locations of the key
- Update all locations in the same PR
- Add tests that verify round-trip data integrity
```

#### 2. Test helper round-trip conversion fidelity

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Test Helper Conversion Fidelity

Test helpers that convert between domain types (e.g., `Plan` to `PRDetails` and back) must preserve all fields from the source object.

**Anti-pattern:** Hardcoding values that should come from the source
```python
# BAD: loses plan's actual base_ref_name
def _plan_to_pr_details(plan: Plan) -> PRDetails:
    return PRDetails(base_ref_name="main", ...)  # hardcoded!
```

**Correct pattern:** Read from source with fallback defaults
```python
# GOOD: preserves plan's metadata
def _plan_to_pr_details(plan: Plan) -> PRDetails:
    base_ref = plan.metadata.get("base_ref_name", "main")
    return PRDetails(base_ref_name=base_ref, ...)
```

**Why this matters:** The `_plan_to_pr_details` helper in PR #8103 hardcoded `base_ref_name="main"`, causing test plans with custom `base_ref_name` metadata to lose that value during round-trip conversion. Tests that should have caught the real bug were silently broken.
```

#### 3. Plan-save conditional branch base behavior

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8103]

**Draft Content:**

```markdown
## Plan Branch Base Selection

Plan branches are created with context-aware base selection:

| Current Context | Plan Branch Base | Rationale |
|-----------------|------------------|-----------|
| Feature branch | Current branch | Enables natural Graphite stacking |
| Trunk (master) | `origin/trunk` | Traditional isolated plan behavior |
| Detached HEAD | `origin/trunk` | Safe fallback when no branch context |

The base branch is stored in plan metadata as `base_ref_name` and read during checkout to set the correct Graphite parent. This replaces the old runtime inference approach that guessed the parent from whatever branch the user happened to be on at checkout time.

See `src/erk/cli/commands/exec/scripts/plan_save.py` for the conditional logic.
```

#### 4. Checkout metadata-based parent resolution

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8103]

**Draft Content:**

```markdown
## Plan Checkout Parent Resolution

When checking out a plan, the Graphite parent is determined by:

1. Read `base_ref_name` from `plan.metadata` (set during plan-save)
2. Fall back to trunk if metadata is missing (backward compatibility)

This is a design-time declaration model, not runtime inference. The parent branch is recorded when the plan is saved, ensuring correct tracking regardless of the user's current branch at checkout time.

**Before PR #8103:** Checkout guessed parent from current branch, causing `gt track` failures when the plan branch's git ancestry didn't include the current branch.

**After PR #8103:** Checkout reads the declared parent from plan metadata, always matching the plan branch's actual git ancestry.

See `src/erk/cli/commands/branch/checkout_cmd.py` for the metadata reading logic.
```

### MEDIUM Priority

#### 5. BranchManager abstraction pattern

**Location:** `docs/learned/architecture/branch-manager-abstraction.md` (new)
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - creating branches with Graphite tracking
  - modifying branch creation logic
  - debugging Graphite tracking issues
tripwires: 1
---

# BranchManager Abstraction

The `BranchManager` ABC provides a unified interface for branch operations that may have different implementations (pure git vs Graphite-aware).

## Key Insight: create_branch() Handles Tracking

`GraphiteBranchManager.create_branch()` automatically handles both:
1. Git branch creation
2. Graphite tracking with `gt track --parent <base_branch>`

**Anti-pattern:** Adding separate `gt track` calls after `create_branch()`
**Correct:** The `base_branch` parameter to `create_branch()` determines the Graphite parent automatically.

When you change the base branch in plan-save, Graphite tracking automatically uses the correct parent without additional tracking calls.

See `src/erk/gateway/graphite.py` for the implementation.
```

#### 6. Plan metadata flow architecture

**Location:** `docs/learned/planning/plan-metadata-flow.md` (new)
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - adding new metadata fields to plans
  - debugging missing or incorrect plan metadata
  - understanding how plan data flows through the system
tripwires: 0
---

# Plan Metadata Flow

Understanding how metadata flows through the plan lifecycle is essential for adding new fields correctly.

## Flow Diagram

```
plan_save.py         planned_pr.py        pr_details_to_plan()   checkout_cmd.py
(writer)             (PR creation)        (conversion)           (reader)
    |                     |                    |                     |
    v                     v                    v                     v
metadata dict    -->  PR body metadata  --> Plan.metadata dict --> consumption
base_ref_name         base field              base_ref_name         parent branch
```

## Key Files

1. **Writer:** `src/erk/cli/commands/exec/scripts/plan_save.py` - Sets metadata fields
2. **Storage:** `packages/erk-shared/src/erk_shared/plan_store/planned_pr.py` - Stores in PR
3. **Conversion:** `packages/erk-shared/src/erk_shared/plan_store/conversion.py` - PR to Plan
4. **Reader:** `src/erk/cli/commands/branch/checkout_cmd.py` - Reads from Plan.metadata

When adding new metadata fields, all four locations may need updates.
```

#### 7. Type narrowing patterns with intermediate variables

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Type Narrowing Through Intermediate Variables

Python type checkers may not propagate type narrowing through intermediate boolean variables.

**Problematic pattern:**
```python
current_branch: str | None = get_current_branch()
on_feature_branch = current_branch is not None and current_branch != trunk
if on_feature_branch:
    base_branch = current_branch  # ERROR: still str | None, not narrowed
```

**Working pattern:**
```python
current_branch: str | None = get_current_branch()
if current_branch is not None and current_branch != trunk:
    base_branch = current_branch  # OK: type checker narrows to str
```

**Why:** When the check is extracted to an intermediate variable, the type checker loses the connection between the condition and the variable it narrows. Inline the check when type narrowing is needed.
```

### LOW Priority

#### 8. Backend naming inconsistency

**Location:** `.claude/commands/erk-plan-save.md`
**Action:** UPDATE
**Source:** [Planning]

**Draft Content:**

Update command documentation to use `planned_pr` consistently. The current docs reference `draft_pr` in several places, but the actual JSON output from the command shows `"plan_backend": "planned_pr"`. Search for `draft_pr` and replace with `planned_pr` where it refers to the backend type.

## Stale Documentation Cleanup

No stale documentation requiring deletion was identified. The existing docs describe intended behavior that was previously not implemented correctly. The implementation now matches the documented intent.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Metadata Key Naming Mismatch

**What happened:** Initial implementation used `trunk_branch` as the metadata key in the writer, but readers expected `base_ref_name`. Data was written but silently ignored.
**Root cause:** No coordination between writer and reader on key names. The rename was semantic (trunk_branch implies it's always trunk, but now it can be a feature branch).
**Prevention:** Grep all read/write locations when adding or renaming metadata keys. Update all locations in the same PR.
**Recommendation:** TRIPWIRE - This is a high-severity silent failure pattern.

### 2. Test Helper Round-Trip Data Loss

**What happened:** The `_plan_to_pr_details` test helper hardcoded `base_ref_name="main"`, causing test Plans with custom `base_ref_name` metadata to lose that value during conversion.
**Root cause:** Test helper prioritized simplicity over fidelity. Hardcoded a reasonable default instead of reading from the source object.
**Prevention:** Test helpers that convert between domain types must use `.get()` with fallback defaults for optional fields, never hardcode values that should come from the source.
**Recommendation:** TRIPWIRE - This pattern can cause tests to silently fail to catch real bugs.

### 3. Type Narrowing Through Boolean Variables

**What happened:** Code used `on_feature_branch = current_branch is not None and ...` then `if on_feature_branch:`, but the type checker couldn't narrow `current_branch` to `str` inside the if block.
**Root cause:** Type checker limitation - narrowing doesn't propagate through intermediate variable assignments.
**Prevention:** Inline type-narrowing checks directly in if/elif statements instead of extracting to variables.
**Recommendation:** ADD_TO_DOC - Medium severity, type checker catches this at CI time.

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Metadata key consistency across components

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before adding or renaming metadata fields that flow between components
**Warning:** All readers and writers must use identical metadata keys. Grep codebase for all read/write locations before renaming. The `base_ref_name` rename in PR #8103 required changes in 3 files: plan_save.py (writer), planned_pr.py (storage), checkout_cmd.py (reader).
**Target doc:** `docs/learned/architecture/cross-component-data-contracts.md`

This is tripwire-worthy because the failure mode is completely silent - data is written with one key and read with another, and the reader just gets None or a default value. No errors, no warnings, just incorrect behavior that's hard to debug.

### 2. Test helper round-trip conversion fidelity

**Score:** 5/10 (Non-obvious +2, Repeated pattern +1, Silent failure +2)
**Trigger:** Before creating test helpers that convert between domain types (Plan to PRDetails, etc)
**Warning:** Test helpers must preserve ALL fields from source object, especially metadata. Use `.get()` with fallback defaults for optional fields, never hardcode values. Example: `_plan_to_pr_details` hardcoded `base_ref_name='main'` causing test failures.
**Target doc:** `docs/learned/testing/tripwires.md`

This is tripwire-worthy because broken test helpers can mask real bugs. If the helper loses metadata, tests that should catch metadata-related bugs will pass even when the production code is wrong.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Type narrowing through intermediate boolean variables

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** Python type checker limitation. The workaround is simple (inline the check), and the type checker catches this at CI time, so it's not a silent failure. Could be promoted to tripwire if agents frequently make this mistake across multiple implementations.

### 2. BranchManager auto-tracking behavior

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** Graphite-specific behavior where `create_branch()` handles tracking automatically. Could be promoted to tripwire if agents commonly try to add manual `gt track` calls after `create_branch()`. Currently the pattern seems well-encapsulated and violations would likely cause obvious errors.
