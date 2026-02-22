# Documentation Plan: Split status indicators into separate 'sts' column in TUI dashboard

## Context

This implementation refactored the TUI dashboard to display status indicators (emoji) in a dedicated "sts" column rather than appending them to the lifecycle stage name. The change improves visual clarity by separating two concerns: the lifecycle stage (a text label like "planned", "impling") and the status indicators (emoji like rocket, eyes, conflict markers).

The implementation introduced `compute_status_indicators()` as a new public function, extracted shared logic into `_build_indicators()` helper, and updated the data flow from `RealPlanDataProvider` through `PlanRowData` to `PlanDataTable`. This required coordinated changes across 7 files following the established column addition pattern. A secondary session discovered an important unicode rendering lesson: variation selectors in emoji can force double-wide terminal rendering, breaking column alignment.

Future agents benefit from understanding: (1) when to use the new status indicator functions vs the existing `format_lifecycle_with_status()`, (2) the gotchas around emoji rendering in fixed-width TUI columns, and (3) the systematic approach to propagating dataclass field additions through the codebase.

## Raw Materials

PR #7860

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 10    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 3     |

## Documentation Items

### HIGH Priority

#### 1. Unicode emoji variation selector rendering

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session 3fa035bf

**Draft Content:**

```markdown
## Unicode Emoji Rendering in Fixed-Width Columns

When adding emoji to Textual DataTable columns, be aware that unicode variation selectors affect terminal rendering width.

**The Problem**: The variation selector `\ufe0f` (Variation Selector-16) forces emoji presentation, causing double-wide rendering that breaks column alignment.

**Example**:
- `\u2601\ufe0f` (cloud with VS16) renders double-wide, breaking alignment
- `\u2601` (plain cloud) renders at text width, predictable alignment

**Prevention**:
1. Prefer plain unicode codepoints without variation selectors
2. Test emoji rendering in actual terminal before committing
3. When alignment breaks after emoji change, check for hidden variation selectors, not just column width

See `plan_table.py` for tested emoji configurations.
```

#### 2. Status indicator function selection

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session fd8890c0, [PR #7860]

**Draft Content:**

```markdown
## Status Indicator Function Selection

When adding status indicators to TUI displays, choose the appropriate function:

- **`compute_status_indicators()`**: Returns emoji indicators as a list. Use when displaying in a separate column or when you need the raw indicator values.
- **`format_lifecycle_with_status()`**: Returns a combined string with stage name and indicators. Use when displaying inline with the lifecycle stage.

Both functions delegate to `_build_indicators()` for consistent indicator logic. Do not call `_build_indicators()` directly from outside `lifecycle.py`.

See `lifecycle.py` for implementation details.
```

#### 3. PlanRowData.status_display field reference

**Location:** `docs/learned/tui/plan-row-data.md`
**Action:** UPDATE
**Source:** [PR #7860]

**Draft Content:**

```markdown
## status_display Field

| Field | Type | Description | Example Values |
|-------|------|-------------|----------------|
| `status_display` | `str` | Emoji indicators for plan status, displayed in "sts" column | "-", "rocket", "eyes rocket", "conflict" |

**Purpose**: Carries status indicators separately from `lifecycle_display`, enabling separate column display and independent formatting.

**Populated by**: `RealPlanDataProvider._build_row_data()` via `compute_status_indicators()`

See `types.py`, grep for "class PlanRowData".
```

#### 4. Dashboard "sts" column entry

**Location:** `docs/learned/tui/dashboard-columns.md`
**Action:** UPDATE
**Source:** [PR #7860]

**Draft Content:**

```markdown
## Plans View Columns

| Column | Width | Content | Notes |
|--------|-------|---------|-------|
| sts | 4 | Emoji indicators (rocket, eyes, conflict) or "-" | Added in PR #7860, positioned after "stage" |

The "sts" column displays status indicators extracted from the lifecycle display. Width 4 accommodates up to 2 emoji indicators (2 chars each, space-joined).

See `plan_table.py`, grep for "sts" or "_setup_columns".
```

### MEDIUM Priority

#### 5. Status indicator extraction pattern

**Location:** `docs/learned/tui/status-indicators.md` (CREATE)
**Action:** CREATE
**Source:** [Impl] Session fd8890c0, [PR #7860]

**Draft Content:**

```markdown
---
read-when:
  - adding status indicators to TUI displays
  - modifying lifecycle display formatting
  - working with PlanRowData lifecycle fields
tripwires: 0
---

# Status Indicator Extraction Pattern

## Overview

Status indicators (emoji) are computed separately from lifecycle stage names, enabling independent display in dedicated TUI columns.

## Architecture

The status indicator system has three layers:

1. **`_build_indicators()`**: Internal helper that determines which indicators apply based on plan state (conflicts, draft/published, review decisions, merge readiness)

2. **`compute_status_indicators()`**: Public function returning indicators as a list. Use for separate column display.

3. **`format_lifecycle_with_status()`**: Public function returning combined string. Use for inline display.

## Data Flow

RealPlanDataProvider._build_row_data() populates two separate fields:
- `lifecycle_display`: Stage name only (e.g., "planned", "impling")
- `status_display`: Space-joined indicators (e.g., "rocket eyes") or "-"

## When to Use

| Need | Use | Returns |
|------|-----|---------|
| Separate column display | `compute_status_indicators()` | `["rocket", "eyes"]` |
| Inline display | `format_lifecycle_with_status()` | `"planned rocket eyes"` |

See `lifecycle.py` for implementation.
```

#### 6. Extract shared logic pattern

**Location:** `docs/learned/refactoring/extract-shared-logic.md` (CREATE or UPDATE existing refactoring doc)
**Action:** CREATE
**Source:** [Impl] Session fd8890c0-part1

**Draft Content:**

```markdown
---
read-when:
  - extracting shared computation from existing function
  - two functions need same intermediate result
  - refactoring to reduce duplication
tripwires: 0
---

# Extract Shared Logic Pattern

## Pattern

When two public functions need the same computation, extract it to a private helper:

1. Identify the shared computation in the existing function
2. Extract to a private helper (prefix with `_`)
3. Have the original function delegate to the helper
4. Create the new public function that also delegates to the helper
5. Test both public functions independently

## Example: Status Indicators

The `_build_indicators()` helper was extracted from `format_lifecycle_with_status()` to support both:
- `format_lifecycle_with_status()` - original function, now delegates
- `compute_status_indicators()` - new function, also delegates

## Benefits

- DRY: Single source of truth for indicator logic
- Consistency: Both callers get identical behavior
- Testability: Each public function tested independently
- Maintainability: Fix indicator logic in one place

See `lifecycle.py` for the implementation.
```

#### 7. Column width decisions

**Location:** `docs/learned/tui/column-width-decisions.md` (CREATE as section or decision record)
**Action:** CREATE
**Source:** [Impl] Session fd8890c0-part2

**Draft Content:**

```markdown
---
read-when:
  - setting TUI column widths
  - adding new columns to dashboard
  - optimizing table layout
tripwires: 0
---

# Column Width Decisions

## Stage Column (width 8)

After extracting status indicators to separate column, stage column was reduced from 11 to 8:
- Longest abbreviated stage names: "prompted", "planning" (8 chars)
- Previous width 11 accommodated stage + emoji indicators

## Status Column (width 4)

New "sts" column uses width 4:
- Supports 2 emoji indicators (approximately 2 display chars each)
- Indicators are space-joined: "rocket eyes"
- "-" displayed when no indicators

## Design Tradeoff

Compact display vs readability. Chose minimal widths that accommodate all content without truncation.

See `plan_table.py`, grep for "add_column".
```

#### 8. TUI emoji column alignment tripwire

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session 3fa035bf

**Draft Content:**

```markdown
## Emoji Column Alignment

When changing emoji characters in TUI columns:

1. Test rendering width in actual terminal (not just character count)
2. Verify column alignment with real data, not just test fixtures
3. If alignment breaks, investigate both:
   - Column width setting
   - Unicode codepoint (variation selectors are invisible but affect width)

Terminal emoji rendering varies by character and terminal emulator. What works in one terminal may break in another.

See session 3fa035bf for debugging example where treating symptom (width) instead of root cause (variation selector) led to incomplete fix.
```

### LOW Priority

#### 9. make_plan_row() status_display parameter

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [PR #7860]

**Draft Content:**

```markdown
## Test Helper Updates

### make_plan_row() Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status_display` | `str` | `"-"` | Emoji indicators for plan status |

Use when creating `PlanRowData` in tests that verify status indicator behavior.

See `fake.py`, grep for "make_plan_row".
```

#### 10. Test data factory update requirement

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [Impl] Session fd8890c0-part2

**Draft Content:**

```markdown
## Dataclass Field Addition Checklist

When adding a required field to a widely-used dataclass like `PlanRowData`:

1. **Factory functions**: Grep for factory helpers (e.g., `make_plan_row`) and add the parameter
2. **Direct constructions**: Grep for the class name in tests to find direct constructions
3. **Serialization tests**: Update field lists in tests like `test_serialize_*_all_fields_present`

**Tip**: Add with a sensible default value in the factory to minimize test churn. Only tests that care about the field need to specify it.

The session fd8890c0-part2 encountered 4 test failures from missing `status_display` in direct `PlanRowData` constructions.
```

## Contradiction Resolutions

None detected. All existing documentation is consistent with the implementation approach.

## Stale Documentation Cleanup

None detected. All referenced files exist and are valid.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. TUI column misalignment after emoji change

**What happened:** Changed globe emoji to cloud emoji, column alignment broke. Increasing column width didn't fix it.
**Root cause:** Unicode variation selector `\ufe0f` forces emoji presentation at double-wide rendering in terminal.
**Prevention:** Prefer plain unicode codepoints without variation selectors. Test rendering in actual terminal before committing. When alignment breaks, investigate the codepoint itself, not just column width.
**Recommendation:** TRIPWIRE

### 2. Missing required field in dataclass construction

**What happened:** Added `status_display` field to `PlanRowData`, 4 tests failed because direct constructions didn't include the new field.
**Root cause:** Frozen dataclass requires all fields at construction; didn't update all construction sites.
**Prevention:** Before adding required field, grep for (1) factory functions, (2) direct constructions in tests, (3) serialization tests. Update all sites atomically or add with default value first.
**Recommendation:** ADD_TO_DOC (testing patterns)

### 3. Incomplete fix (width adjustment alone)

**What happened:** When alignment broke, first tried increasing column width from 3 to 4. Still broken.
**Root cause:** Treated symptom (wrong width) instead of root cause (variation selector on emoji).
**Prevention:** When debugging emoji issues, check both width AND the unicode codepoint for hidden variation selectors.
**Recommendation:** CONTEXT_ONLY (include in tripwire as debugging guidance)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Unicode emoji variation selector rendering

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before using emoji in Textual DataTable columns
**Warning:** Avoid variation selectors like `\ufe0f` as they force emoji presentation at double-wide, breaking alignment. Use plain unicode codepoints (e.g., `\u2601` not `\u2601\ufe0f`). Test rendering in terminal before committing.
**Target doc:** `docs/learned/tui/tripwires.md`

This is tripwire-worthy because the failure mode is silent and non-obvious. The emoji looks correct visually but causes alignment to break. The variation selector is invisible in most editors, making the root cause hard to identify. Session 3fa035bf shows the debugging escalation: simple fix failed, width increase failed, only removing the variation selector worked.

### 2. Status indicator function selection

**Score:** 4/10 (Cross-cutting +2, Repeated pattern +1, Non-obvious +1)
**Trigger:** Before adding status indicators to TUI display
**Warning:** Use `compute_status_indicators()` for separate column display; use `format_lifecycle_with_status()` for inline indicators. Both delegate to `_build_indicators()` for consistent logic.
**Target doc:** `docs/learned/tui/tripwires.md`

This is tripwire-worthy because the codebase now has two public functions for status indicators with different return types and use cases. Without guidance, an agent might call the wrong one or attempt to call `_build_indicators()` directly.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. TUI emoji column alignment

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** Related to variation selector tripwire. Could be merged as a sub-section rather than separate tripwire. The core lesson (test rendering in terminal) overlaps with the variation selector warning.

### 2. Dataclass field addition test coverage

**Score:** 2/10 (Repeated pattern +1, Cross-cutting +1)
**Notes:** When adding required field to frozen dataclass, update all factory functions and direct test constructions. Already partially covered by `column-addition-pattern.md`. May warrant tripwire if pattern repeats frequently.

### 3. Incomplete fix (width adjustment alone)

**Score:** 2/10 (Non-obvious +2)
**Notes:** Session 3fa035bf showed treating symptom instead of root cause. This is a debugging pattern rather than a standalone tripwire. Include as guidance in the emoji rendering tripwire.

## Code Change Items (SHOULD_BE_CODE)

These items should be implemented as code changes rather than documentation:

### 1. `_build_indicators()` docstring

**Location:** `lifecycle.py`, function `_build_indicators()`
**Action:** Add comprehensive docstring
**Content:** Document the purpose (shared indicator computation), parameters (lifecycle stage, plan state), return value (list of emoji strings), and the indicators it produces (draft/published, conflict, review decisions, merge readiness).

### 2. Column width calculation comment

**Location:** `plan_table.py`, in `_setup_columns()`
**Action:** Add inline comment
**Content:** Explain width=8 for stage column (longest stage name "prompted"/"planning") and width=4 for sts column (2 emoji indicators maximum).
