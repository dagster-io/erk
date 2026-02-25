# Documentation Plan: Fix learn PRs appearing in Planned PRs tab

## Context

This implementation fixed a critical bug where learn PRs were incorrectly appearing in the "Planned PRs" tab of `erk dash`. The root cause was `PlannedPRBackend.create_plan()` unconditionally adding the `erk-plan` label to all PRs, including learn PRs that should only have `erk-learn`. A secondary bug compounded the issue: `RealPlanDataProvider.fetch_plans()` wasn't passing the `exclude_labels` parameter to the service layer, so the defense-in-depth filtering that should have caught mislabeled plans never fired.

The fix establishes an important architectural principle: backends should be label-agnostic and apply exactly what callers provide. Type-specific logic belongs in callers who understand business context. This is similar to erk's "no default parameters" rule - explicit is better than implicit, especially when implicit behavior can cause label contamination.

Documentation matters because future agents working with plan backends, view filtering, or adding new plan types need to understand: (1) the label hierarchy system (base + type labels), (2) why backends must not add classification labels, and (3) how to ensure filter parameters propagate through all layers of the call chain.

## Raw Materials

PR #8212

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 11    |
| Contradictions to resolve      | 1     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Correct view-switching.md label sharing statement

**Location:** `docs/learned/tui/view-switching.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8212]

**Draft Content:**

```markdown
## View Label Configuration (CORRECTION)

> **Note:** Previous documentation incorrectly stated that Plans and Learn views share the same API label. This has been corrected.

Each view is configured with DISTINCT label requirements:

### Plans View
- Primary labels: `("erk-plan",)` - queries for implementation plans only
- Excluded labels: `("erk-learn",)` - explicitly filters out learn plans
- Defense-in-depth: The exclude filter catches any plans with incorrect label combinations

### Learn View
- Primary labels: `("erk-learn",)` - queries for learn plans only
- Excluded labels: `()` - no exclusions needed

**Key insight:** Plans and Learn views use DIFFERENT type labels for GitHub API queries. They both share the base label `erk-planned-pr`, but the view queries filter by type-specific labels (`erk-plan` or `erk-learn`), not the base label.

See `src/erk/tui/views/types.py` for ViewConfig definitions.
```

---

#### 2. PlannedPRBackend unconditional label addition tripwire

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8212]

**Draft Content:**

```markdown
## Backend Label Application

**Before modifying PlannedPRBackend.create_plan() or implementing similar backend methods:**

Backend must apply ONLY caller-provided labels. Never add classification labels (like `erk-plan`). The caller determines plan type and provides the complete label list.

**Why this matters:** PR #8212 fixed a bug where `PlannedPRBackend.create_plan()` unconditionally added `erk-plan` to all PRs, causing learn plans to have three labels (`erk-planned-pr` + `erk-plan` + `erk-learn`). This broke label-based view filtering - learn plans appeared in the Plans tab.

**Correct pattern:** Callers build complete label lists based on plan type. Backends iterate over caller-provided labels without additions.

See `packages/erk-shared/src/erk_shared/plan_store/planned_pr.py` method `create_plan`.
```

---

#### 3. Missing exclude_labels parameter passthrough tripwire

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8212]

**Draft Content:**

```markdown
## Filter Parameter Propagation

**When adding filter parameters to PlanFilters or similar filter dataclasses:**

Ensure parameter is passed through entire pipeline: ViewConfig -> PlanFilters -> RealPlanDataProvider -> PlanListService -> GitHub gateway. Missing parameter forwarding causes defense-in-depth filtering to fail silently.

**Why this matters:** PR #8212 fixed a bug where `RealPlanDataProvider.fetch_plans()` had `exclude_labels` in its filter object but didn't pass it to the service layer. The Plans view's `exclude_labels=("erk-learn",)` was being ignored.

**Prevention:** When adding a parameter to a filter dataclass, trace through every method in the call chain. Verify the parameter is forwarded at each layer. Check both the objective branch and plan branch if both exist.

See `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` method `fetch_plans`.
```

---

#### 4. Label contamination between plan types tripwire

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Plan] [Impl]

**Draft Content:**

```markdown
## Label Consistency Across Backends

**Before querying plans by labels or creating new plan types:**

Always verify label assignment logic is consistent across all backends. `PlannedPRBackend` (PR-based) and `GitHubPlanStore` (issue-based) must use the same label logic to prevent type discrimination failures.

**Why this matters:** The issue-based plan creation path (`plan_issues.py`) correctly assigned mutually exclusive labels. The PR-based path (`planned_pr.py`) had divergent logic that added `erk-plan` unconditionally. This caused learn plans created via PRs to have both `erk-plan` and `erk-learn`, breaking view filtering.

**Audit checklist for new plan types:**
1. Check issue-based path: `packages/erk-shared/src/erk_shared/gateway/github/plan_issues.py`
2. Check PR-based path: `packages/erk-shared/src/erk_shared/plan_store/planned_pr.py`
3. Verify both paths produce identical label sets for the same plan type
```

---

### MEDIUM Priority

#### 5. Label-based view filtering mechanics

**Location:** `docs/learned/tui/label-based-view-filtering.md`
**Action:** CREATE
**Source:** [Plan] [Impl]

**Draft Content:**

```markdown
---
read-when:
  - debugging view filtering
  - understanding why plans appear in wrong tab
  - adding new view modes to erk dash
---

# Label-Based View Filtering

How GitHub labels map to TUI view segregation in erk dash.

## Label Hierarchy

All plans use a two-level label hierarchy:

1. **Base label**: `erk-planned-pr`
   - Applied to ALL plan PRs (standard + learn)
   - Marks PR as part of erk's plan system

2. **Type labels** (mutually exclusive):
   - `erk-plan` - Standard implementation plans
   - `erk-learn` - Documentation learning plans
   - Only ONE type label per plan

## View Configuration

Each tab queries for plans with specific labels:

| View | Primary Labels | Exclude Labels | Purpose |
|------|---------------|----------------|---------|
| Plans | `("erk-plan",)` | `("erk-learn",)` | Show standard plans only |
| Learn | `("erk-learn",)` | `()` | Show learn plans only |

See `src/erk/tui/views/types.py` for ViewConfig definitions.

## Two-Stage Filtering

Views use both server-side and client-side filtering:

1. **Server-side** (GitHub REST API): Query by `labels` parameter
2. **Client-side** (exclude_labels): Filter out items with excluded labels

The client-side filter is defense-in-depth - it catches plans with incorrect label combinations even if the primary filter would match them.

## is_learn_plan Determination

Client-side code determines if a plan is a learn plan by checking: `"erk-learn" in plan.labels`

See `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` for implementation.
```

---

#### 6. Backend label application pattern

**Location:** `docs/learned/architecture/backend-label-pattern.md`
**Action:** CREATE
**Source:** [Impl] [PR #8212]

**Draft Content:**

```markdown
---
read-when:
  - implementing plan/issue creation backends
  - modifying create_plan() methods
  - adding new entity types that share backends
---

# Backend Label Application Pattern

Backends should be label-agnostic. They apply exactly what callers provide without adding classification labels.

## Principle

The caller determines entity type and builds the complete label set. The backend is a dumb applicator - it doesn't know about plan types, learn types, or any business classification.

## Correct Pattern

Callers build complete label lists based on plan type:

```python
labels = ["erk-planned-pr"]
if plan_type == "learn":
    labels.append("erk-learn")
else:
    labels.append("erk-plan")

# Backend applies exactly what caller provides
backend.create_plan(..., labels=labels)
```

## Incorrect Pattern (Anti-Pattern)

Backend adding classification labels:

```python
def create_plan(self, labels):
    # WRONG: Backend assumes all plans need erk-plan
    self.add_label("erk-plan")  # Don't do this!
    for label in labels:
        if label != "erk-plan":
            self.add_label(label)
```

## Why This Matters

- Allows multiple entity types to share the same backend
- Maintains type separation through caller control
- Similar to "no default parameters" rule - explicit is better than implicit
- Prevents label contamination bugs like PR #8212

See `packages/erk-shared/src/erk_shared/plan_store/planned_pr.py` method `create_plan` for the correct implementation.
```

---

#### 7. Filter parameter propagation pattern

**Location:** `docs/learned/architecture/filter-parameter-propagation.md`
**Action:** CREATE
**Source:** [Impl] [PR #8212]

**Draft Content:**

```markdown
---
read-when:
  - adding parameters to PlanFilters or similar filter objects
  - implementing data provider methods with filtering
  - debugging why a filter parameter seems to be ignored
---

# Filter Parameter Propagation Pattern

When adding filter parameters to dataclasses, ensure they're passed through the entire pipeline.

## The Problem

Filter objects have many fields. When adding a new field, it's easy to add it to the dataclass but forget to forward it through every method in the call chain.

## Example Call Chain

From PR #8212, the exclude_labels parameter needed to flow through:

```
ViewConfig.exclude_labels (types.py)
    |
    v
PlanFilters.exclude_labels (data/types.py)
    |
    v
RealPlanDataProvider.fetch_plans() (real.py)
    |
    v
PlanListService.get_plan_list_data() (plan_issues.py)
    |
    v
GitHub API query
```

The bug: Parameter existed in ViewConfig and PlanFilters but wasn't passed from RealPlanDataProvider to PlanListService.

## Prevention Checklist

When adding a filter parameter:

1. Add to the filter dataclass (e.g., PlanFilters)
2. Find all methods that take the filter object
3. For each method, verify it forwards the parameter to underlying calls
4. Check BOTH branches if the code has conditional paths (e.g., objective vs plan)
5. Write a test that verifies the parameter affects the result

## Silent Failure Mode

Missing parameter forwarding typically fails silently - the filter just doesn't filter. This makes the bug hard to detect without explicit testing.
```

---

#### 8. Update learn-vs-implementation-plans.md with label hierarchy

**Location:** `docs/learned/planning/learn-vs-implementation-plans.md`
**Action:** UPDATE
**Source:** [Plan]

**Draft Content:**

```markdown
## Label Hierarchy

All plans use a two-level label hierarchy:

1. **Base label**: `erk-planned-pr`
   - Applied to ALL plan PRs (standard + learn)
   - Marks PR as part of erk's plan system
   - Shared across all plan types

2. **Type labels** (mutually exclusive):
   - `erk-plan` - Standard implementation plans
   - `erk-learn` - Documentation learning plans
   - Only ONE type label per plan

**Label assignment responsibility:** Callers (like `plan_save.py`) build the complete label list based on plan type. Backends apply exactly what callers provide without adding classification labels.

See `src/erk/cli/commands/exec/scripts/plan_save.py` for label list construction.
```

---

#### 9. Update view-switching.md with exclude_labels documentation

**Location:** `docs/learned/tui/view-switching.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## ViewConfig Fields

Each view is configured with two label-related fields:

### labels (primary filter)
Tuple of labels that must be present for the query. Passed to GitHub REST API.

### exclude_labels (defense-in-depth filter)
Tuple of labels that exclude an item from results. Applied client-side after API query.

**Example - Plans View:**
```python
PLANS_VIEW = ViewConfig(
    labels=("erk-plan",),           # Must have erk-plan
    exclude_labels=("erk-learn",),  # Must NOT have erk-learn
)
```

The exclude_labels field provides belt-and-suspenders protection. If a plan incorrectly has both `erk-plan` and `erk-learn` labels, the exclude filter catches it.

**Important:** For exclude_labels to work, it must be passed through the entire data pipeline. See `docs/learned/architecture/filter-parameter-propagation.md`.
```

---

### LOW Priority

#### 10. Defense-in-depth filtering pattern

**Location:** `docs/learned/architecture/gateway-patterns.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Defense-in-Depth Filtering Pattern

When querying plans or PRs, use both server-side and client-side filtering:

**Server-side** (GitHub API query):
- Query by primary labels (e.g., `labels=("erk-plan",)`)
- Returns all items matching the positive filter

**Client-side** (exclude_labels):
- Filter out items with excluded labels (e.g., `exclude_labels=("erk-learn",)`)
- Catches items with incorrect label combinations
- Provides safety net if label assignment has bugs

**Example from Plans view:**
1. Server query: `labels=("erk-plan",)` -> returns all PRs with erk-plan label
2. Client filter: `exclude_labels=("erk-learn",)` -> removes any that also have erk-learn
3. Result: Only standard plans, no learn plans (even if they incorrectly have both labels)
```

---

#### 11. Add docstring to is_learn_plan determination

**Location:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`
**Action:** CODE_CHANGE
**Source:** [Plan]

**Draft Content:**

This is a SHOULD_BE_CODE item. Add an inline comment or docstring explaining the `is_learn_plan` check:

```python
# is_learn_plan: True if plan has erk-learn label. Used for client-side filtering
# to distinguish learn plans from standard implementation plans.
is_learn_plan = "erk-learn" in plan.labels
```

This is single-location logic that belongs in source code, not in docs/learned/.

---

## Contradiction Resolutions

### 1. View Label Sharing Statement

**Existing doc:** `docs/learned/tui/view-switching.md`
**Conflict:** Documentation states "Plans and Learn share the same API label - this is intentional for the two-tier filtering strategy." However, source code shows Plans view uses `labels=("erk-plan",)` and Learn view uses `labels=("erk-learn",)` - they do NOT share the same API query label.
**Resolution:** Update `view-switching.md` to correctly state that:
1. Plans and Learn views use DIFFERENT type labels for queries (erk-plan vs erk-learn)
2. Both plan types share the BASE label `erk-planned-pr` (not the query label)
3. The two-tier strategy is: server-side GitHub API query by type label + client-side exclude_labels filtering

---

## Stale Documentation Cleanup

No stale documentation detected. All referenced source files exist and contain the documented code.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Backend Over-Classification

**What happened:** `PlannedPRBackend.create_plan()` unconditionally added `erk-plan` label to all PRs, assuming all plans needed this classification.
**Root cause:** Backend tried to be "helpful" by adding classification labels instead of trusting caller-provided labels.
**Prevention:** Backends should be label-agnostic and only apply what the caller provides. Type-specific logic belongs in callers who understand business context.
**Recommendation:** TRIPWIRE - Document in `docs/learned/planning/tripwires.md`

### 2. Filter Parameter Gap

**What happened:** `RealPlanDataProvider.fetch_plans()` had `exclude_labels` in its filter object but didn't pass it to the underlying service method.
**Root cause:** Parameter forwarding was incomplete - the field existed but wasn't threaded through all layers.
**Prevention:** When adding filter parameters to dataclasses, trace through every method in the call chain to verify forwarding at each layer.
**Recommendation:** TRIPWIRE + NEW_DOC - Add tripwire to `docs/learned/architecture/tripwires.md` and create `filter-parameter-propagation.md`

### 3. Inconsistent Backend Implementations

**What happened:** `PlannedPRBackend` (PR-based) and `GitHubPlanStore` (issue-based) had different label assignment logic.
**Root cause:** Two implementations of similar functionality diverged without shared tests verifying consistent behavior.
**Prevention:** When multiple backends implement the same interface, create shared test cases to verify consistent behavior.
**Recommendation:** ADD_TO_DOC - Note in `learn-vs-implementation-plans.md` to audit both paths when adding plan types

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. PlannedPRBackend unconditional label addition

**Score:** 8/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2, Silent failure +2)
**Trigger:** Before modifying `PlannedPRBackend.create_plan()` or implementing similar backend create methods
**Warning:** Backend must apply ONLY caller-provided labels. Never add classification labels (like `erk-plan`). The caller determines plan type and provides the complete label list. See bug #8212 where unconditional `erk-plan` addition broke learn plan filtering.
**Target doc:** `docs/learned/planning/tripwires.md`

This is tripwire-worthy because the error required understanding the multi-layer filtering system to diagnose. It affected all plan types and broke view filtering completely. The bug produced wrong results silently without any exception.

### 2. Label contamination between plan types

**Score:** 7/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2, Repeated pattern +1)
**Trigger:** Before adding new plan types or modifying label assignment logic
**Warning:** Always verify label assignment logic is consistent across all backends. `PlannedPRBackend` (PR-based) and `GitHubPlanStore` (issue-based) must use the same label logic to prevent type discrimination failures.
**Target doc:** `docs/learned/planning/tripwires.md`

This is tripwire-worthy because the same mistake could happen when adding new plan types (e.g., objective plans). The divergence between issue-based and PR-based paths was non-obvious.

### 3. Missing exclude_labels parameter passthrough

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** When adding filter parameters to `PlanFilters` dataclass or similar filter objects
**Warning:** Ensure parameter is passed through entire pipeline: ViewConfig -> PlanFilters -> RealPlanDataProvider -> PlanListService -> GitHub gateway. Missing `exclude_labels` passthrough in `RealPlanDataProvider.fetch_plans()` caused defense-in-depth filtering to fail silently. See PR #8212.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because the parameter existed but wasn't forwarded, causing silent failure. This applies to all data provider methods with filtering.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Backend over-classification pattern

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)
**Notes:** Could apply to other backends but less destructive than label contamination when caught during PR review. Would be promoted if similar bugs occur in other backends.

### 2. Generic filter parameter gap pattern

**Score:** 3/10 (Cross-cutting +2, Silent failure +1)
**Notes:** The specific `exclude_labels` case is documented as tripwire #3 above. The generic version is less severe without a concrete example. Would be promoted if more filter parameters fail to propagate.
