# Documentation Plan: Add inline objective filter to erk dash TUI (`o` key)

## Context

This PR (#8283) introduced an inline objective filter to the erk dash TUI, allowing users to press `o` on any plan row to filter the Plans view to show only plans linked to the same objective. The implementation replaced a modal screen (`ObjectivePlansScreen`) with a lightweight inline filter pattern that mirrors the existing stack filter (`t` key). The result is a net reduction of 701 lines of code while providing a more composable, consistent user experience.

The implementation demonstrates several patterns worth documenting for future TUI development: the three-stage composable filter pipeline, the progressive escape chain for clearing filters in LIFO order, and the modal-to-inline-filter migration pattern. The agent cleanly executed the plan with minimal errors, encountering only a status bar line length violation (quickly resolved by adjusting spacing) and discovering that removed actions require removal of associated test classes.

Documentation matters here because the filter composition architecture and progressive escape behavior are cross-cutting concerns that affect all future filter additions. Without explicit documentation, a future agent adding a new filter might not understand that they need to integrate into 7 different places in the codebase, or that the escape chain order matters for user experience.

## Raw Materials

PR #8283

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 9 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 4 |
| Potential tripwires (score 2-3) | 2 |

## Documentation Items

### HIGH Priority

#### 1. Progressive escape chain extension

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Progressive Escape Chain

When adding a new filter to the TUI, you must extend `action_exit_app` to clear the new filter before older filters. The escape key clears filters in LIFO order (newest/narrowest filters clear first):

1. Objective filter (newest)
2. Stack filter
3. Text content
4. Exit text mode
5. Quit app (last resort)

**Trigger:** Before adding a new filter to TUI

**Warning:** New filter checks must appear BEFORE existing filter checks in action_exit_app. If you add a filter at the end of the chain, users will have to press Escape through all other filters before reaching yours.

See `src/erk/tui/app.py` (grep for `action_exit_app`) for the current implementation.
```

---

#### 2. Filter pipeline architecture

**Location:** `docs/learned/tui/filter-pipeline.md`
**Action:** CREATE
**Source:** [Impl], [PR #8283]

**Draft Content:**

```markdown
---
title: TUI Filter Pipeline Architecture
read-when:
  - adding a new filter to erk dash TUI
  - modifying how TUI filtering works
  - understanding TUI data flow
---

# TUI Filter Pipeline Architecture

The erk dash TUI uses a three-stage composable filter pipeline in `_apply_filter_and_sort`. Filters are applied sequentially, allowing multiple filters to be active simultaneously.

## Pipeline Order

1. **Objective filter** - Filters by `objective_issue` field (plan-level scope)
2. **Stack filter** - Filters by branch membership in Graphite stack (branch-level scope)
3. **Text filter** - Filters by search query against row content
4. **Sort** - Applied after all filters

## Why Order Matters

More restrictive filters are applied first for performance. Objective filter (broad, plan-level) narrows the dataset before stack filter (narrow, branch-level) processes it. This minimizes the work done by subsequent filter stages.

## Adding a New Filter

When adding a new filter, integrate it into `_apply_filter_and_sort` at the appropriate position based on its scope. Broader filters (affecting more rows) should come before narrower filters.

## Filter Composition Test

Always add a test verifying your new filter composes correctly with existing filters. See `test_objective_filter_composes_with_text_filter` in `tests/tui/test_app.py` for the pattern.

## Source

See `src/erk/tui/app.py` (grep for `_apply_filter_and_sort`) for the current implementation.
```

---

#### 3. Key binding repurposing pattern

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [Plan]

**Draft Content:**

```markdown
## Key Binding Repurposing

Before repurposing a key binding, verify the existing functionality is redundant (covered by other keys). Document why the old binding was redundant in your plan.

**Trigger:** Before repurposing a TUI key binding

**Warning:** Verify existing functionality is covered by other keys before repurposing. If not truly redundant, you may break workflows that depend on the old binding.

**Example:** The `o` key was repurposed from "open row in browser" to "toggle objective filter" because:
- `p` already opens PRs in browser
- `enter` opens detail modal which has browser-open options
- Therefore `o` was genuinely redundant for browser access

Document similar justification when repurposing any key binding.
```

---

#### 4. Status bar line length constraint

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Status Bar Key Hints

When modifying status bar key hints in `status_bar.py`, the line must stay under 100 characters (E501 lint rule).

**Trigger:** Before modifying status_bar.py key hints

**Warning:** Line length must stay under 100 chars. Use single-space separation between items (not double-space) to save characters. Consider abbreviations like "o:obj" instead of "o:objective" if needed.

See `src/erk/tui/widgets/status_bar.py` (grep for `_update_display`) for current implementation.
```

---

### MEDIUM Priority

#### 1. Inline objective filter feature documentation

**Location:** `docs/learned/tui/inline-objective-filter.md`
**Action:** CREATE
**Source:** [Plan], [Impl]

**Draft Content:**

```markdown
---
title: Inline Objective Filter
read-when:
  - working with objective filtering in TUI
  - understanding TUI filter interactions
  - modifying Plans view filtering
---

# Inline Objective Filter

The `o` key in Plans view toggles filtering to show only plans linked to the same objective as the selected row.

## Behavior

1. **Toggle on:** Press `o` on a plan with an `objective_issue` field set. Table filters to rows with matching objective.
2. **Toggle off:** Press `o` again to restore all rows.
3. **Status display:** Shows "Objective: #123 (N plans)" in status bar when active.
4. **Edge case:** If the selected plan has no objective, displays status message "Plan not linked to an objective".

## Integration Points

- **Progressive escape:** Cleared by Escape before stack filter
- **View switching:** Cleared when switching views (1/2/3 keys)
- **Filter composition:** Composes with stack filter and text filter

## State Variables

- `_objective_filter_issue: int | None` - Active objective issue number
- `_objective_filter_label: str | None` - Display label for status bar

## Source

See `src/erk/tui/app.py` (grep for `action_toggle_objective_filter`) for implementation.
```

---

#### 2. Modal to inline filter migration pattern

**Location:** `docs/learned/refactoring/modal-to-filter.md`
**Action:** CREATE
**Source:** [PR #8283]

**Draft Content:**

```markdown
---
title: Modal to Inline Filter Migration
read-when:
  - replacing a modal screen with inline filtering
  - simplifying TUI interaction patterns
  - reducing TUI code complexity
---

# Modal to Inline Filter Migration

This pattern documents when and how to replace modal screens with inline filters for lighter UX and better composability.

## When to Apply

Replace modal screens with inline filters when:
- The modal's primary purpose is filtering/narrowing data
- The filtered data can be displayed in an existing view
- Users would benefit from composing this filter with others
- The modal adds significant code complexity

## Benefits

- **Lighter UX:** No modal overlay, faster interaction
- **Composability:** Can combine with stack and text filters
- **Less code:** Modal screen deletion often yields significant line reduction
- **Simpler mental model:** One filtering paradigm instead of modal + filter hybrid

## Migration Checklist

1. Identify existing filter pattern to mirror (e.g., stack filter)
2. Add state variables for filter value and display label
3. Create toggle action method following existing pattern
4. Create clear helper method
5. Integrate into `_apply_filter_and_sort` pipeline
6. Add to progressive escape chain in `action_exit_app`
7. Add to view-switch clearing in `_switch_view`
8. Update help screen with new key binding
9. Update status bar with key hint
10. Add test coverage mirroring existing filter tests
11. Delete modal screen file and its tests
12. Remove old key binding references

## Case Study: ObjectivePlansScreen

PR #8283 migrated from `ObjectivePlansScreen` modal (294 lines) to inline objective filter. Net result: -701 lines, plus better UX through filter composition.

See `src/erk/tui/app.py` (grep for `objective_filter`) and compare with deleted `objective_plans_screen.py` in git history.
```

---

#### 3. Filter toggle pattern

**Location:** `docs/learned/tui/filter-patterns.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: TUI Filter Toggle Pattern
read-when:
  - adding a new toggle filter to TUI
  - understanding filter state management
  - mirroring existing filter implementations
---

# TUI Filter Toggle Pattern

Both the stack filter and objective filter follow a consistent toggle pattern. Use this pattern when adding new filters.

## Pattern Components

### State Variables

```
self._<filter>_issue: <type> | None = None  # Filter value
self._<filter>_label: str | None = None     # Display label
```

### Toggle Action Method

1. Check if filter already active with same value -> toggle off
2. Get selected row -> validate it has the filterable field
3. Set state variables
4. Call `_apply_filter()` to refresh display
5. Post status message with count

### Clear Helper Method

1. Reset state variables to None
2. Call `_apply_filter()` to refresh display
3. Post status message confirming clear

### Integration Points

- `_apply_filter_and_sort`: Add filter logic
- `action_exit_app`: Add to progressive escape chain
- `_switch_view`: Clear filter on view switch

## Test Coverage Pattern

Create 6 tests mirroring existing filter tests:
1. Basic filter activation
2. Toggle off behavior
3. Invalid input handling (e.g., row without objective)
4. Progressive escape clears filter
5. View switch clears filter
6. Filter composition with other filters

See `tests/tui/test_app.py` (grep for `TestObjectiveFilter` or `TestStackFilter`) for examples.
```

---

#### 4. Update action inventory

**Location:** `docs/learned/tui/action-inventory.md`
**Action:** UPDATE
**Source:** [PR #8283]

**Draft Content:**

```markdown
## Updates from PR #8283

### Removed Actions

- `action_open_row` - Removed; functionality covered by `action_open_pr` (`p` key) and detail modal
- `action_drill_down` - Removed; replaced by inline objective filter

### Added Actions

- `action_toggle_objective_filter` - Key: `o`, View: Plans, Predicate: checks `objective_issue` field, Toggle behavior filters to matching objective
```

---

#### 5. Test class removal when removing actions

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Test Class Removal for Deleted Actions

When removing `action_*` methods from the TUI app, grep the tests directory for test classes that test those actions and remove them.

**Trigger:** Before removing action_* methods from TUI

**Warning:** When deleting action methods, also delete their test classes. Search for both the method name (e.g., "action_open_row") and likely test class names (e.g., "TestOpenRow").

**Example:** When `action_open_row` was removed, `TestOpenRow` class (102 lines) had to be deleted from `tests/tui/test_app.py`.
```

---

### LOW Priority

#### 1. Targeted test execution pattern

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Targeted Test Execution During Feature Development

When developing a focused feature like a new filter, run specific test classes first to avoid noise from pre-existing failures:

```bash
# Run only the new feature's tests
pytest tests/tui/test_app.py::TestObjectiveFilter -v

# Then run related tests
pytest tests/tui/test_app.py::TestStackFilter -v

# Then broader tests
pytest tests/tui/test_app.py -v

# Finally full CI
make ci
```

This progression validates your changes before encountering unrelated pre-existing failures.
```

---

## Contradiction Resolutions

No contradictions detected. The `o` key binding change from "open issue" to "toggle objective filter" was an intentional design change documented in the plan, not a contradiction with existing architectural patterns. The existing documentation correctly described the old behavior, and updates are captured in the action inventory update item above.

## Stale Documentation Cleanup

No stale documentation detected. The existing docs checker verified all code references and found no phantom references.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Status bar line length violation

**What happened:** Adding "o:obj" to status bar key hints pushed line 127 to 106 characters, exceeding the 100-character E501 limit.

**Root cause:** Double-space separation between key hint items was wasteful.

**Prevention:** Before modifying status bar key hints, count the resulting line length. Use single-space separation between items.

**Recommendation:** TRIPWIRE (documented above)

### 2. Orphaned test class after action removal

**What happened:** After removing `action_open_row`, `TestOpenRow` test class (102 lines) remained, causing test failures.

**Root cause:** When removing action methods, the associated test classes weren't identified as needing removal.

**Prevention:** When removing `action_*` methods, immediately grep the tests directory for test classes mentioning that action name and remove them.

**Recommendation:** TRIPWIRE (documented above with score 3, included in testing/tripwires.md)

### 3. Pre-existing test failures creating noise

**What happened:** Running full test suite encountered unrelated failures in `test_comment_counts_from_pr_data` and `test_pressing_2_switches_to_learn_view`.

**Root cause:** Pre-existing failures in the test suite unrelated to the current changes.

**Prevention:** For focused changes, run targeted test classes first to validate the change, then run broader tests. Document known pre-existing failures.

**Recommendation:** ADD_TO_DOC (captured in targeted test execution pattern above)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Progressive escape chain extension

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before adding a new filter to TUI
**Warning:** Must extend progressive escape chain in action_exit_app. Add new filter check BEFORE existing filter checks. Order: objective -> stack -> text content -> text mode -> quit.
**Target doc:** `docs/learned/tui/tripwires.md`

This is tripwire-worthy because the order matters and getting it wrong breaks user experience. If a new filter check is added at the end of the chain, users would have to press Escape through all other filters before reaching the new one. The LIFO ordering is non-obvious from the code without understanding the UX rationale.

### 2. Filter composition into _apply_filter_and_sort

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** Before adding a new filter to TUI
**Warning:** Must integrate into _apply_filter_and_sort pipeline. Add filter step in order of restrictiveness (more restrictive first for performance). Current order: objective -> stack -> text -> sort.
**Target doc:** `docs/learned/tui/tripwires.md`

This is tripwire-worthy because the pipeline order affects both correctness and performance. Adding a narrower filter before a broader one would work but waste computation. The current architecture isn't obvious from the code alone.

### 3. Key binding repurposing pattern

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** Before repurposing a TUI key binding
**Warning:** First verify existing functionality is redundant (covered by other keys). Document why in plan. Example: `o` for open was redundant because `p` opens PRs and `enter` opens detail modal.
**Target doc:** `docs/learned/tui/tripwires.md`

This is tripwire-worthy because repurposing a key without checking for redundancy could silently break user workflows. The verification step is non-obvious and applies to all future key binding changes.

### 4. Status bar line length constraint

**Score:** 4/10 (Cross-cutting +2, Silent failure +2)
**Trigger:** Before modifying status_bar.py key hints
**Warning:** Line length must stay under 100 chars (E501). Use single-space separation between items. Consider abbreviations like "o:obj" instead of "o:objective".
**Target doc:** `docs/learned/tui/tripwires.md`

This is tripwire-worthy because the failure is silent at edit time (only caught by linter), and the solution (single-space separation) isn't obvious. This constraint applies to all status bar modifications.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Test class removal when removing actions

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)
**Notes:** Pattern specific to action_* methods in TUI. May be obvious enough (grep for method name). Included in testing/tripwires.md at lower priority. Could be promoted if this mistake recurs in future sessions.

### 2. View switch clears filters

**Score:** 2/10 (Cross-cutting +2)
**Notes:** Pattern is already established and obvious from `_switch_view` code. Any new filter should follow this pattern, but it's visible in the existing code. Doesn't meet threshold - included in filter-patterns.md documentation instead.
