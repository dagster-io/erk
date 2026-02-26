# Documentation Plan: Stack Filter for erk dash TUI

## Context

This implementation added a stack filter feature to the erk dash TUI, enabling users to filter the plan table by Graphite stack membership using the `t` key binding. The feature represents the first query-only gateway delegation to BranchManager (accessing Graphite's local cache without subprocess calls) and establishes a composable filter architecture where multiple independent filters (stack, text) AND together to narrow results.

The session demonstrated mature agent workflow patterns: parallel Explore agents gathered comprehensive context before planning, progressive questioning clarified requirements (preventing a cross-view vs single-view misunderstanding), and explicit architectural pattern mirroring ensured the new filter followed established conventions. Future agents implementing similar filter features will benefit from understanding the filter pipeline architecture, the progressive escape pattern, and the bidirectional test fake registration requirement.

Key insights include: (1) gateway methods that delegate to external tools for cache access require the standard 5-place implementation pattern even though no subprocess is involved, (2) test fakes for membership/graph data must register bidirectionally to mirror real system behavior, and (3) new TUI filter types must integrate with the progressive escape hierarchy and respect view switching semantics.

## Raw Materials

Session analyses available at:
- `.erk/scratch/sessions/5d567c43-0ba1-4bbb-a57b-af3e824329f6/learn-agents/session-fdb271f2-part1.md`
- `.erk/scratch/sessions/5d567c43-0ba1-4bbb-a57b-af3e824329f6/learn-agents/session-fdb271f2-part2.md`
- `.erk/scratch/sessions/5d567c43-0ba1-4bbb-a57b-af3e824329f6/learn-agents/diff-analysis.md`
- `.erk/scratch/sessions/5d567c43-0ba1-4bbb-a57b-af3e824329f6/learn-agents/gap-analysis.md`

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 10 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 3 |
| Potential tripwires (score 2-3) | 4 |

## Documentation Items

### HIGH Priority

#### 1. Gateway ABC Addition: get_branch_stack()

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8211] [Impl]

**Draft Content:**

```markdown
### Gateway ABC Method Addition: Query-Only Delegation

When adding a new method to a Gateway ABC that delegates to external tools for cache access (no subprocess), follow the 5-place implementation pattern:

1. **ABC signature** with Optional return type for data that may not exist
2. **Fake implementation** with test configuration setter (e.g., `get_X()` → `set_X()`)
3. **Real implementation** with proper delegation to the external tool/manager
4. **Update all tests** to use the new Fake setter for test data setup
5. **For asymmetric data** (membership, graphs), ensure Fake setter registers bidirectionally

**Example: get_branch_stack()**

The `get_branch_stack()` method returns `list[str] | None` — the ordered stack list or None for Git-mode repos. This is the first query-only delegation to BranchManager (reads Graphite's local cache, no subprocess).

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py, get_branch_stack -->

See `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/` for the ABC, Fake, and Real implementations. Grep for `get_branch_stack` to find all three.
```

---

#### 2. Test Fake Bidirectional Registration Pattern

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8211] [Impl]

**Draft Content:**

```markdown
### Bidirectional Registration for Membership/Graph Fakes

When implementing a fake for a method that returns membership, graph, or relationship data, registration must be bidirectional to mirror real system behavior.

**Problem:** Real systems (like Graphite) cache data for ALL related entities. If a stack contains branches [A, B, C], querying any of those branches returns the same stack list.

**Anti-pattern:** Registering only the "selected" branch's stack:
- Tests pass if that branch is always selected
- Tests fail mysteriously when row ordering changes

**Solution:** Register every branch in the relationship:

```python
# For stack [A, B, C], register three entries
for branch in ["branch-a", "branch-b", "branch-c"]:
    fake.set_branch_stack(branch, ["branch-a", "branch-b", "branch-c"])
```

**Why this matters:** Test fakes must model the real system's invariants. Asymmetric registration creates tests that pass coincidentally but fail under different conditions (row reordering, data changes).

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py, set_branch_stack -->
<!-- Source: tests/tui/test_app.py, TestStackFilter -->

See `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py`, grep for `set_branch_stack` for the implementation pattern.
```

---

#### 3. Filter Feature Architectural Mirroring

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8211] [Impl]

**Draft Content:**

```markdown
### Adding New Filter Types to erk dash TUI

When adding a new filter type (e.g., stack filter, objective filter, label filter), follow this checklist to ensure architectural consistency:

**State Management:**
- Add state tracking fields matching the pattern: `_*_filter_*` (value) and `_*_filter_label` (display)
- Use appropriate types: `frozenset[str] | None` for set membership, `str | None` for single values

**Filter Pipeline Integration:**
- Integrate with the composable filter pipeline: new filter → existing filters → sort
- Filters compose via AND (all must pass), not OR
- Order matters: broadest filter first (reduces working set for subsequent filters)

**Progressive Escape Behavior:**
- ESC clears the newest filter first, then cascades to older filters
- Order: stack filter → text content → text mode → quit
- Add clearing logic to `action_exit_app()`

**View Switching:**
- Clear view-specific filters (like stack filter) on view switch
- Preserve universal filters (like text filter) across views
- Update `_switch_view()` to handle new filter state

**UI Updates:**
- Add status bar message when filter is active (format: "FilterName: label (count)")
- Add key binding hint to status bar
- Update help screen with new key binding description

<!-- Source: src/erk/tui/app.py, action_toggle_stack_filter -->
<!-- Source: src/erk/tui/app.py, _apply_filter_and_sort -->

See `src/erk/tui/app.py`, grep for `action_toggle_stack_filter` and `_apply_filter_and_sort` for the reference implementation.
```

---

#### 4. Composable Filter Pipeline Architecture

**Location:** `docs/learned/tui/filtering-architecture.md`
**Action:** CREATE
**Source:** [PR #8211] [Impl]

**Draft Content:**

```markdown
---
category: tui
read-when:
  - working with erk dash TUI filtering
  - adding new filter types to the TUI
  - understanding how multiple filters compose
tripwires: 0
---

# TUI Filtering Architecture

## Overview

The erk dash TUI uses a composable filter architecture where multiple independent filters combine to narrow results. This document covers the filter pipeline, composition semantics, and progressive escape pattern.

## Filter Pipeline

The filter pipeline applies filters in sequence:

1. **Stack filter** (broadest) — filters by Graphite stack membership
2. **Text filter** (narrower) — filters by title/description content
3. **Sort** — orders the final results

**Pipeline ordering rationale:** Filters are ordered from broadest to narrowest. Stack filter reduces the working set before text matching, improving perceived performance for large plan lists.

<!-- Source: src/erk/tui/app.py, _apply_filter_and_sort -->

## Composition Semantics

Filters compose via **AND**, not OR:
- A plan must pass ALL active filters to be displayed
- Clearing one filter expands results (removes a constraint)
- This enables compound queries like "all plans in this stack that match 'auth'"

## State Management

Each filter maintains independent state:
- **Stack filter:** `_stack_filter_branches: frozenset[str] | None`, `_stack_filter_label: str | None`
- **Text filter:** `_search_text: str`, `_search_mode: bool`

State independence means clearing one filter doesn't affect others.

## Progressive Escape Pattern

ESC key progressively removes constraints rather than jumping to quit:

1. If stack filter active → clear stack filter
2. If text filter has content → clear text content
3. If text mode active → exit text mode
4. Otherwise → quit app

This gives users fine-grained control over their filter state.

<!-- Source: src/erk/tui/app.py, action_exit_app -->

## None-Handling for Optional Fields

Stack filtering requires None checks at two levels:

1. **Branch existence:** Some plans have no PR yet (`pr_head_branch is None`)
2. **Stack membership:** Git-mode repos or standalone branches return `None` from `get_branch_stack()`

Both conditions are normal (not exceptional), so the code uses LBYL pattern with explicit None checks.

## Source Locations

- Filter pipeline: `src/erk/tui/app.py`, grep for `_apply_filter_and_sort`
- Stack filter action: `src/erk/tui/app.py`, grep for `action_toggle_stack_filter`
- Escape handling: `src/erk/tui/app.py`, grep for `action_exit_app`
- Existing filter types: `src/erk/tui/filtering/types.py` (FilterState), `src/erk/tui/filtering/logic.py` (filter_plans)
```

---

#### 5. Gateway Query-Only Delegation Pattern

**Location:** `docs/learned/architecture/gateway-delegation-patterns.md`
**Action:** CREATE
**Source:** [PR #8211] [Impl]

**Draft Content:**

```markdown
---
category: architecture
read-when:
  - adding gateway methods that delegate to external tools
  - working with Graphite cache access
  - understanding query vs mutation delegation patterns
tripwires: 0
---

# Gateway Delegation Patterns

## Overview

Gateway ABCs sometimes delegate operations to external tools or managers. This document covers delegation patterns, distinguishing between mutation delegation and query-only delegation.

## Mutation Delegation

Most gateway delegations are for mutations that require subprocess calls:
- Creating branches (`git checkout -b`)
- Deleting branches (`git branch -D`)
- Submitting PRs (`gt stack submit`)

These follow the standard subprocess wrapper pattern documented in `architecture/subprocess-wrappers.md`.

## Query-Only Delegation

Some delegations are pure reads that access cached data without subprocess calls:
- Getting branch stack membership (reads Graphite's local cache)
- Checking branch existence (reads git refs)

**Key difference:** Query-only delegations are:
- **Lightweight:** No subprocess overhead
- **Safe:** No mutations, no side effects
- **Cacheable:** Results can be memoized if needed

**Example: get_branch_stack()**

This method delegates to BranchManager to access Graphite's local stack cache. No git or gt commands are executed — it reads the `.graphite/` directory directly.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py, get_branch_stack -->

## When to Use Query Delegation

Use query-only delegation when:
1. Data is available from an external tool's local cache
2. No network calls are required
3. The operation has no side effects

Still follow the 5-place implementation pattern (ABC, Fake, Real, tests, docs) even for query-only methods.

## Source Locations

See `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`, grep for `get_branch_stack` for the reference implementation.
```

---

### MEDIUM Priority

#### 6. TUI View Switching Clears Stack Filter

**Location:** `docs/learned/tui/view-switching.md`
**Action:** UPDATE
**Source:** [PR #8211] [Impl]

**Draft Content:**

```markdown
### Filter Clearing on View Switch

Different filter types have different persistence semantics during view switches:

**Preserved across views:**
- Text filter — user may want to search for the same term in all views

**Cleared on view switch:**
- Stack filter — inherently tied to a specific branch; different views may show different branches

**Rationale:** Stack filtering makes sense only within a single view where the filtered branches exist. Preserving stack filters across views would confuse users when the filtered branches don't appear in the new view.

**Implementation:** `_switch_view()` clears `_stack_filter_branches` and `_stack_filter_label` before loading the new view.

<!-- Source: src/erk/tui/app.py, _switch_view -->

See `src/erk/tui/app.py`, grep for `_switch_view` for the implementation.
```

---

#### 7. TUI Key Binding Pattern with Stack Filter Example

**Location:** `docs/learned/tui/adding-commands.md`
**Action:** UPDATE
**Source:** [PR #8211] [Impl]

**Draft Content:**

```markdown
### Adding Toggle-Style Key Bindings

For features that toggle state on/off (like filters), follow this pattern:

**1. Add BINDINGS entry:**
```python
BINDINGS = [
    # ... existing bindings ...
    Binding("t", "toggle_stack_filter", "Filter stack", show=False),
]
```

**2. Implement action method:**
- Name must match binding: `action_toggle_stack_filter()`
- Check preconditions (correct view, data availability)
- Toggle state: if active, clear; if inactive, activate
- Update status bar with result

**3. Update status bar hints:**
Add key hint to status bar for discoverability (e.g., "t:stack")

**4. Update help screen:**
Add description to help screen key binding list

**5. Integrate with escape handling:**
If the toggle adds state that should be clearable, integrate with `action_exit_app()`

<!-- Source: src/erk/tui/app.py, action_toggle_stack_filter -->
<!-- Source: src/erk/tui/app.py, BINDINGS -->

See `src/erk/tui/app.py`, grep for `action_toggle_stack_filter` for a complete example.
```

---

#### 8. Explore-Before-Plan Workflow

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
### Explore-Before-Plan for Multi-System Features

When implementing features that touch multiple existing systems (3+ files, unclear scope), launch parallel Explore agents before creating a plan.

**When to use:**
- Feature interacts with multiple subsystems (e.g., TUI + gateway + tests)
- Implementation approach is unclear
- Need to understand existing patterns before designing new ones

**Pattern:**
1. Launch Explore agents in parallel, one per subsystem of interest
2. Each agent documents: code locations, patterns used, data flow, state management
3. Synthesize findings before launching Plan agent
4. Plan agent receives comprehensive context, avoids premature assumptions

**Example:** Stack filter feature launched two Explore agents:
- One to understand existing stack filter implementation patterns
- One to understand the objective drill-down modal being replaced

This prevented a cross-view vs single-view misunderstanding that would have complicated the implementation.

**Anti-pattern:** Launching a Plan agent immediately without understanding existing patterns. This leads to plans that don't align with established conventions.
```

---

#### 9. Progressive Questioning for Requirement Clarification

**Location:** `docs/learned/planning/requirement-elicitation.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
category: planning
read-when:
  - clarifying ambiguous user requirements
  - features with unclear view context in TUI
  - interaction flow is not explicitly stated
tripwires: 0
---

# Requirement Elicitation Through Progressive Questioning

## Overview

When requirements are ambiguous, use progressive questioning to narrow down user intent rather than making assumptions that may lead to incorrect implementations.

## When to Use

Apply progressive questioning when:
- View context is unclear (which view(s) does the interaction span?)
- Interaction flow is ambiguous (navigation vs filtering vs modal)
- Feature name could mean multiple things

## Pattern

1. **Start broad:** Ask about the general interaction model
2. **Narrow options:** Present 2-3 specific interpretations
3. **Validate understanding:** Restate the requirement in concrete terms
4. **Confirm before planning:** Get explicit user confirmation

## Example: Cross-View vs Single-View Confusion

Initial requirement: "add keyboard filter to drill down to objective's plans"

**Ambiguity:** Does this mean:
- (A) From Objectives view, navigate to filtered Plans view
- (B) Within Plans view, filter by selected plan's objective

Progressive questions revealed option (B) was intended, completely changing the implementation approach.

## Key Questions to Ask

- "Where does this interaction start — in which view?"
- "Where does it end — same view or different view?"
- "Is this filtering (staying in place) or navigation (switching views)?"
- "Should other state be preserved or cleared?"
```

---

#### 10. Cross-View vs Single-View Feature Decision Framework

**Location:** `docs/learned/tui/feature-classification.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
category: tui
read-when:
  - designing new TUI features
  - unclear whether feature crosses view boundaries
  - planning navigation vs filtering features
tripwires: 0
---

# TUI Feature Classification: Cross-View vs Single-View

## Overview

TUI features fall into two categories with different implementation complexity:
- **Single-view:** Operates entirely within one view (simpler)
- **Cross-view:** Navigates between views or affects multiple views (complex)

## Classification Questions

Ask these questions to classify a feature:

1. **Where does interaction start?** (Which view?)
2. **Where does interaction end?** (Same view or different?)
3. **Is state preserved or cleared?** (Filters, selections, scroll position)
4. **What triggers the action?** (Key press, click, automatic)

## Single-View Patterns

Single-view features stay within one view:
- **Filtering:** Apply predicate to current view's data (e.g., stack filter)
- **Sorting:** Reorder current view's data
- **Selection:** Change selected row within current view

Implementation is simpler: no view switching logic, no state transfer.

## Cross-View Patterns

Cross-view features navigate between views:
- **Drill-down:** Go from summary view to detail view
- **Navigation:** Move between related entities across views
- **Modals:** Overlay additional data without changing base view

Implementation is complex: view switching, state transfer, back navigation.

## Default to Single-View

When requirements are ambiguous, prefer single-view implementations:
- Simpler to implement
- Easier to maintain
- More consistent with existing patterns
- Ask clarifying questions before assuming cross-view

## Example: Stack Filter

Initial interpretation: Cross-view (Objectives → Plans)
Actual requirement: Single-view (filter Plans by objective)

The single-view approach was simpler, matched existing patterns, and met user needs.
```

---

## Contradiction Resolutions

No contradictions detected between existing documentation and new insights.

## Stale Documentation Cleanup

No stale documentation detected. All referenced docs have valid file references.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Cross-View vs Single-View Misunderstanding

**What happened:** Agent initially interpreted "drill down to objective's plans" as cross-view navigation (Objectives view → Plans view), but user intended single-view filtering within Plans view.

**Root cause:** Ambiguous language ("drill down") could mean navigation or filtering. Agent assumed more complex interpretation without clarifying.

**Prevention:** When requirements mention view interactions, explicitly ask: "Where does this interaction start and end — same view or different views?"

**Recommendation:** ADD_TO_DOC (covered in requirement-elicitation.md)

### 2. Keyboard Shortcut Redundancy Assumption

**What happened:** Agent assumed `o` (open row) was redundant with `enter`, but they have different functions (`o` opens in browser, `enter` shows modal).

**Root cause:** Checked binding descriptions but not actual implementations.

**Prevention:** Grep for action method implementations to verify actual behavior, not just binding descriptions.

**Recommendation:** CONTEXT_ONLY (standard verification practice)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Gateway ABC Addition (5-place pattern)

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before adding a new method to any Gateway ABC
**Warning:** Follow 5-place implementation pattern: ABC signature with Optional return type, Fake with test configuration setter, Real implementation, test updates. For asymmetric data (membership, graphs), ensure Fake setter registers bidirectionally.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because agents may add an ABC method without realizing the Fake needs a bidirectional setter. Missing Fake setters break all tests silently; missing Real implementations crash production. The pattern applies to all gateway ABCs, making it cross-cutting.

### 2. Test Fake Bidirectional Registration

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2, but limited to specific data types -1)
**Trigger:** When implementing a fake for a method that returns membership/graph/relationship data
**Warning:** Registration must be bidirectional. Real system caches data for all related entities; Fake must mirror this. Asymmetric registration causes silent test failures when row ordering changes.
**Target doc:** `docs/learned/testing/tripwires.md`

This is tripwire-worthy because tests appear to work with asymmetric registration until row ordering changes. The failure is silent and mysterious — tests pass in isolation but fail when combined or when data changes.

### 3. Filter Feature Architectural Mirroring

**Score:** 4/10 (criteria: Non-obvious +2, Cross-cutting +2)
**Trigger:** Before adding a new filter type to erk dash TUI
**Warning:** Follow filter feature checklist: state tracking fields (`_*_filter_*`), filter pipeline integration, progressive escape behavior (ESC clears newest first), view switching clears view-specific filters, status bar updates, key binding hints, help screen update.
**Target doc:** `docs/learned/tui/tripwires.md`

This is tripwire-worthy because it's not immediately clear that new filters must integrate with progressive escape and view switching. Missing these integrations leads to inconsistent UX where some filters respect escape and view switching while others don't.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Cross-View vs Single-View Feature Classification

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** The session showed this confusion can happen. Not severe enough for tripwire (doesn't cause silent failures), but worth documenting as a decision framework in the planning workflow.

### 2. Explore-Before-Plan for Multi-System Features

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** Good planning practice that prevents premature implementation. Not a pitfall (no silent failure), but a workflow improvement worth documenting.

### 3. View Switching Filter Clearing

**Score:** 3/10 (criteria: Non-obvious +2, Silent failure +1)
**Notes:** Users might expect all filters to persist across views. Clearing stack filter is intentional but could surprise future maintainers who might "fix" it. Worth documenting the rationale.

### 4. Query-Only Gateway Delegation

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)
**Notes:** First example of cache-only delegation (no subprocess). Worth documenting as a pattern variant, but doesn't cause failures if agents use standard subprocess approach — just unnecessary overhead.
