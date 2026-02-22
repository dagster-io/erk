# Documentation Plan: Fix: Decouple Objectives Screen Columns from Plans Screen

## Context

This PR (#7800) fixed a critical column leakage bug in the `erk dash` TUI where the objectives view was inheriting columns intended for the draft_pr mode of the plans view. PR #7763 had added draft_pr columns (sts, stage, created) BEFORE the objectives view check in `_setup_columns()`, causing the objectives view to inherit 10 columns while `_row_to_values()` returned only 6 values. The symptom was data appearing in wrong columns: progress appeared under "sts", next_node under "stage", etc., with rightmost columns empty.

The fix established an important architectural pattern: view modes with fully independent column sets must define ALL their columns and return early BEFORE any shared column logic executes. This prevents column index misalignment between column setup and row value generation. The fix also added a new "title" column to the objectives view (using the existing `full_title` field in PlanRowData) and corrected the first column header to always show "issue" for objectives view, regardless of plan_backend setting.

This documentation effort captures three critical tripwires to prevent similar bugs: the view mode early return pattern, the three-way plan column header logic, and the test tuple index update pattern when columns are added. These patterns are cross-cutting and apply beyond PlanDataTable to any TUI table widget with view modes or tuple-based row data.

## Raw Materials

Session materials from PR #7800 implementation (no gist URL available).

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 6     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. View Mode Early Return Pattern

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7800]

**Draft Content:**

```markdown
**adding columns to PlanDataTable for a mode-specific feature without checking view mode order** -> Read [Dashboard Column Inventory](dashboard-columns.md) first. View modes with fully independent column sets MUST define ALL columns and return early BEFORE shared column logic. If a mode's columns are added conditionally AFTER another mode's logic, column leakage occurs. The objectives view must return early before draft_pr columns are added.
```

---

#### 2. Plan Column Header Three-Way Logic

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7800]

**Draft Content:**

```markdown
**setting the first column header in PlanDataTable without checking all three cases** -> Read [Dashboard Column Inventory](dashboard-columns.md) first. The first column header has THREE cases: ViewMode.OBJECTIVES uses "issue", plan_backend=="draft_pr" uses "pr", default uses "plan". Check BOTH view_mode AND plan_backend before determining the header.
```

---

#### 3. Test Tuple Index Updates After Column Additions

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7800]

**Draft Content:**

```markdown
**adding a column to a TUI table widget that returns tuples** -> Read [Dashboard Column Inventory](../../tui/dashboard-columns.md) first. When adding a column at index N in `_setup_columns()`, all `_row_to_values()` tuple indices >= N shift by +1. Update test assertions: `len(values)` must match new count, and index-based assertions (e.g., `values[1]` becomes `values[2]`) must shift accordingly.
```

---

### MEDIUM Priority

#### 4. Objectives View Column Inventory Update

**Location:** `docs/learned/tui/dashboard-columns.md`
**Action:** UPDATE
**Source:** [PR #7800]

**Draft Content:**

Update the Objectives View Columns table to reflect the current column structure. The existing table is outdated - it shows "plan or pr" as the first column header, but objectives view now always uses "issue". Also add the new "title" column as the second column.

Replace the Objectives View Columns section with:

```markdown
## Objectives View Columns

When `ViewMode.OBJECTIVES` is active, an entirely independent column set is used. This view mode returns early in `_setup_columns()` before any plans-specific or draft_pr-specific columns are added.

| Column Header | Key         | Width | Purpose                       |
| ------------- | ----------- | ----- | ----------------------------- |
| `issue`       | `plan`      | 6     | Objective issue number        |
| `title`       | `title`     | 50    | Full objective title          |
| `prog`        | `progress`  | 5     | Completion progress           |
| `next node`   | `next_node` | 50    | Recommended next roadmap node |
| `deps`        | `deps`      | 12    | Dependency count              |
| `updated`     | `updated`   | 7     | Last update time              |
| `created by`  | `author`    | 12    | Creator                       |

Note: The objectives view header is ALWAYS "issue", regardless of `plan_backend` setting. This differs from the plans view which shows "pr" or "plan" based on backend.
```

---

#### 5. Column Width Recalculation on Header Rename

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
**renaming a TUI table column header** -> Read [Dashboard Column Inventory](dashboard-columns.md) first. When renaming column headers, verify the new header text fits in the column width. Example: renaming "author" (6 chars) to "created by" (10 chars) requires increasing width from 9 to 12.
```

---

### LOW Priority

#### 6. Column Count vs Tuple Length Debugging

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7800]

**Draft Content:**

```markdown
**debugging column misalignment in PlanDataTable** -> Read [Dashboard Column Inventory](dashboard-columns.md) first. Verify that the number of columns defined in `_setup_columns()` matches the number of values returned by `_row_to_values()` for the SAME view mode. Column leakage from other view modes causes misalignment.
```

---

## Contradiction Resolutions

No contradictions were detected. All existing TUI documentation is consistent with the current codebase:

- `docs/learned/tui/dashboard-columns.md` - CLEAN (needs update for new column, but no conflicts)
- `docs/learned/tui/view-switching.md` - CLEAN
- `docs/learned/tui/column-addition-pattern.md` - CLEAN
- `docs/learned/tui/architecture.md` - CLEAN
- `docs/learned/tui/data-contract.md` - CLEAN
- `docs/learned/tui/plan-row-data.md` - CLEAN

## Stale Documentation Cleanup

No stale documentation requiring deletion. All verified files have valid source references.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Column Header Semantic Mismatch

**What happened:** The agent initially left the "pr" vs "plan" dynamic header logic in place for objectives view, which was semantically incorrect since objectives always show issue numbers, never PR numbers.

**Root cause:** The agent focused on column structure but didn't consider the semantic meaning of the header text in each view mode.

**Prevention:** When modifying view-specific column setup, verify that column headers semantically match what the view displays. Objectives show issues, not PRs.

**Recommendation:** ADD_TO_DOC (included in tripwire #2 above)

### 2. Column Width Underestimate

**What happened:** When renaming "author" to "created by", the agent kept the original width of 9, which truncated the header text.

**Root cause:** Width wasn't recalculated after text change.

**Prevention:** Calculate header length and ensure column width >= header length + padding.

**Recommendation:** ADD_TO_DOC (included in tripwire candidate #5 above - borderline score)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. View Mode Early Return Pattern

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** When adding columns to PlanDataTable for a mode-specific feature
**Warning:** View modes with fully independent column sets MUST define ALL columns and return early BEFORE shared column logic. Without early return, columns from other modes leak into the view.
**Target doc:** `docs/learned/tui/tripwires.md`

This is tripwire-worthy because the failure is silent - data appears in wrong columns with no exception thrown. The bug introduced by PR #7763 passed all tests because the test assertions only checked the structure, not that the structure matched the view mode. This pattern applies to any TUI table widget with multiple view modes needing independent column sets.

### 2. Three-Way Plan Column Header Logic

**Score:** 4/10 (criteria: Non-obvious +2, Cross-cutting +2)
**Trigger:** When setting column headers for the plan/issue/PR identifier column
**Warning:** Check BOTH view_mode AND plan_backend: OBJECTIVES always uses "issue", draft_pr uses "pr", default uses "plan".
**Target doc:** `docs/learned/tui/tripwires.md`

This is tripwire-worthy because the header logic depends on two independent configuration dimensions. Easy to check only one dimension and get incorrect semantics.

### 3. Test Tuple Index Updates

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** When adding columns to TUI table widgets that return tuples
**Warning:** Update test assertions: len() must match new count, indices >= insertion point shift by +1.
**Target doc:** `docs/learned/testing/tripwires.md`

This is tripwire-worthy because it's a mechanical update that's easy to forget. The PR review caught exactly this issue - the implementation added a column but tests were asserting on the old tuple structure.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Column Width Recalculation on Header Rename

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** User had to manually correct "created by" width from 9 to 12. Could become a full tripwire if pattern repeats. Currently borderline because column width issues are immediately visible (truncation), unlike silent column leakage.

### 2. PR Review Bot Metadata Format

**Score:** 3/10 (criteria: External tool quirk +1, Non-obvious +2)
**Notes:** HTML comment markers and YAML metadata blocks used by automated review bots (test-coverage-review, dignified-python-review, tripwires-review). Specific to CI integration. Only relevant if implementing similar automation; not broadly cross-cutting enough for full tripwire status.
