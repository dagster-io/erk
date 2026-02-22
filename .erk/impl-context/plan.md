# Documentation Plan: Remove conditional column display from TUI plans view

## Context

This implementation simplified the TUI plan table by removing conditional column visibility flags (`--runs`, `--show-prs`, `--show-runs`) and making all columns always visible. The change reflects a key insight: users always wanted all columns visible, so the flags added complexity without providing value.

The simplification cascaded through multiple layers: CLI flags were removed from `erk plan list` and `erk exec dash-data`, the `PlanFilters` dataclass lost its `show_prs` and `show_runs` fields, and column setup logic was significantly reduced. The change also added a new clickable learn column following established interaction patterns.

Documentation is essential here because these are breaking changes affecting external users and internal APIs. Future agents need to understand: (1) why the flags were removed, (2) what the current column behavior is, and (3) how to add new clickable columns following the established pattern.

## Raw Materials

PR #7794

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 11    |
| Contradictions to resolve      | 1     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 0     |

## Stale Documentation Cleanup

Existing docs with phantom references requiring action:

### 1. PlanFilters Field Count Staleness

**Location:** `docs/learned/tui/data-contract.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `PlanFilters.show_prs`, `PlanFilters.show_runs` (fields removed)
**Cleanup Instructions:** Update field count from 8 to 6. Remove `show_prs` and `show_runs` from the field reference table. Add note that these fields were removed in favor of always-visible columns.

### 2. Dashboard Columns Doc Phantom References

**Location:** `docs/learned/tui/dashboard-columns.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `PlanFilters.show_prs`, `PlanFilters.show_runs` references throughout
**Cleanup Instructions:** Remove all references to conditional column visibility based on these flags. Update column presence table to reflect always-visible columns.

## Contradiction Resolutions

### 1. PlanFilters Field Count

**Existing doc:** `docs/learned/tui/data-contract.md` (line 195)
**Conflict:** Documentation states "Frozen dataclass with 7 fields" but PlanFilters now has 6 fields after removing `show_prs` and `show_runs`.
**Resolution:** Update field count to 6 and document the removed fields with migration guidance.

## Documentation Items

### HIGH Priority

#### 1. Breaking CLI Flag Removals

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7794]

**Draft Content:**

```markdown
## Removed Column Visibility Flags

The following CLI flags have been removed as all columns are now always visible:

- `erk plan list --runs` / `-r` - Workflow run columns now always display
- `erk exec dash-data --show-prs` - PR data now always fetched
- `erk exec dash-data --show-runs` - Workflow run data now always fetched

**Migration:** Remove these flags from scripts and commands. The columns they controlled are now unconditionally visible.

**Rationale:** Flags added complexity without value - users always wanted all columns visible. See `src/erk/cli/commands/plan/list_cmd.py` for current implementation.
```

---

#### 2. PlanFilters API Change

**Location:** `docs/learned/tui/data-contract.md`
**Action:** UPDATE
**Source:** [PR #7794]

**Draft Content:**

```markdown
## PlanFilters Field Changes

`PlanFilters` is a frozen dataclass with 6 fields (reduced from 8):

- `labels: Sequence[str]`
- `state: PlanState | None`
- `run_state: WorkflowRunState | None`
- `limit: int`
- `creator: str | None`
- `show_pr_column: bool`

**Removed Fields:**
- `show_prs` - Removed, PR data now always fetched
- `show_runs` - Removed, workflow run data now always fetched

**Important Distinction:** `show_pr_column` (retained) controls layout - whether to show a separate PR column (suppressed in draft_pr mode where the first column IS the PR). This is different from the removed `show_prs` which controlled data visibility.

See `src/erk/tui/data/types.py` for current implementation.
```

---

#### 3. Dashboard Columns Inventory Update

**Location:** `docs/learned/tui/dashboard-columns.md`
**Action:** UPDATE
**Source:** [PR #7794]

**Draft Content:**

```markdown
## Column Visibility

All plan table columns are now unconditionally visible. The following columns always appear:

- PR column (if `show_pr_column=True`)
- Checks column
- Comments column
- Learn column (new - clickable when learn data exists)
- Local-wt column
- Remote-impl column
- Run-id column
- Run-state column

**Removed Conditional Logic:** The `_setup_columns` method no longer contains `if self._plan_filters.show_prs:` or `if self._plan_filters.show_runs:` blocks.

**Column Index Stability:** Column indices are now constant for a given `show_pr_column` value. This simplifies code that depends on column positions (cursor navigation, click handling).

See `src/erk/tui/widgets/plan_table.py` for the `_setup_columns` method.
```

---

#### 4. show_pr_column Distinction Clarification

**Location:** `docs/learned/tui/data-contract.md`
**Action:** UPDATE
**Source:** [PR #7794]

**Draft Content:**

```markdown
## Layout vs Data Visibility

`show_pr_column` is a **layout concern**, not a data visibility concern:

- **Layout concern** (`show_pr_column`): Should we render a separate PR column? In draft_pr mode, the first column already IS the PR, so a separate column would be redundant.
- **Data visibility** (removed): `show_prs` and `show_runs` controlled whether to fetch PR/run data. These were removed because users always wanted this data.

The distinction matters: `show_pr_column=False` does NOT mean "don't fetch PR data" - it means "don't render a redundant PR column."
```

---

### MEDIUM Priority

#### 5. Learn Column Click Handling Pattern

**Location:** `docs/learned/tui/dashboard-columns.md`
**Action:** UPDATE
**Source:** [PR #7794]

**Draft Content:**

```markdown
## Learn Column Click Handling

The learn column is clickable when a plan has learn data. Implementation follows the established pattern for clickable columns:

1. **Message class:** `PlanDataTable.LearnClicked` nested class posts when user clicks
2. **Column index tracking:** `_learn_column_index` field stores position during column setup
3. **Click handler:** `on_click` checks if click column matches `_learn_column_index`
4. **Styling:** Cell styled as "cyan underline" when clickable (when `learn_plan_issue`, `learn_plan_pr`, or `learn_run_url` is not None)

This follows the same pattern as `ObjectiveClicked`, `PrClicked`, and `BranchClicked` messages. See `src/erk/tui/widgets/plan_table.py` for implementation.
```

---

#### 6. Unconditional Column Rendering

**Location:** `docs/learned/tui/dashboard-columns.md`
**Action:** UPDATE
**Source:** [PR #7794]

**Draft Content:**

```markdown
## Unconditional Column Setup

`PlanDataTable._setup_columns` now unconditionally includes the full column set. Previous implementation had conditional blocks:

```python
# OLD (removed):
if self._plan_filters.show_prs:
    columns.append(...)
if self._plan_filters.show_runs:
    columns.extend([...])
```

The new implementation always adds all columns, reducing setup logic from ~28 lines to ~20 lines. Value construction in `_row_to_values` is similarly simplified.

See `src/erk/tui/widgets/plan_table.py` for current implementation.
```

---

#### 7. Column Index Stability

**Location:** `docs/learned/tui/dashboard-columns.md`
**Action:** UPDATE
**Source:** [PR #7794]

**Draft Content:**

```markdown
## Fixed Column Indices

Column indices are now fixed for a given `show_pr_column` value. Previously, indices varied based on `show_prs` and `show_runs` flag combinations.

**Benefits:**
- Simplified `local_wt_column_index` property (no longer needs to account for flag variations)
- Predictable column positions for cursor navigation and click handling
- Reduced test complexity (no need to test multiple flag combinations)

The `local_wt_column_index` property documentation was updated to reflect this simplification.
```

---

#### 8. Always-Fetch Workflow Runs

**Location:** `docs/learned/tui/architecture.md`
**Action:** UPDATE
**Source:** [PR #7794]

**Draft Content:**

```markdown
## Plan Data Provider: Always-Fetch Behavior

The plan data provider now always fetches workflow runs (`needs_workflow_runs = True` unconditionally). Previously, this was conditional based on `filters.show_runs`.

**Performance Note:** Every plan list/dash query now includes workflow run data fetch. This was deemed acceptable because users always wanted run data visible.

See `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` for the fetch implementation.
```

---

### LOW Priority

#### 9. Flag Removal Rationale

**Location:** `docs/learned/tui/dashboard-columns.md`
**Action:** UPDATE
**Source:** [PR #7794]

**Draft Content:**

```markdown
## Why Conditional Flags Were Removed

The `--runs`, `--show-prs`, and `--show-runs` flags created complexity without value:

1. **Column index tracking:** Varying indices based on flags complicated cursor navigation
2. **Value construction:** Conditional appending based on flags added code complexity
3. **Tests:** Multiple test cases for flag combinations (70+ lines of test code removed)
4. **Documentation:** Explaining when to use which flags added cognitive load

**User behavior insight:** The flags were never used with `False` values in practice. Users always wanted all columns visible.
```

---

#### 10. Simplification Benefits Metrics

**Location:** `docs/learned/tui/architecture.md`
**Action:** UPDATE
**Source:** [PR #7794]

**Draft Content:**

```markdown
## Column Simplification Metrics

The conditional column visibility removal achieved quantified simplification:

- Reduced column setup: 28 lines to 20 lines
- Fixed column indices instead of varying
- Removed 3 CLI parameters (`--runs`, `--show-prs`, `--show-runs`)
- Removed 2 dataclass fields (`show_prs`, `show_runs`)
- Deleted 70+ lines of test code for flag combinations
- PR stats: +259 -396 lines (net deletion)
```

---

#### 11. PlanFilters.default() Simplification

**Location:** `docs/learned/tui/data-contract.md`
**Action:** UPDATE
**Source:** [PR #7794]

**Draft Content:**

```markdown
## PlanFilters Factory Method

`PlanFilters.default()` factory method now constructs filters with 5 parameters (reduced from 7):

- `labels`
- `state`
- `run_state`
- `limit`
- `creator`

The removed `show_prs=False` and `show_runs=False` parameters are no longer needed since all columns are always visible.
```

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Flag Proliferation Anti-Pattern

**What happened:** Optional flags for column visibility created a proliferation of conditional logic across column setup, value construction, tests, and documentation.

**Root cause:** Initial design assumed users might want to hide columns, but usage data showed this was never true in practice.

**Prevention:** Before adding optional flags, verify there's actual use case diversity. Consider starting with the simpler always-on approach and only adding flags if users request configurability.

**Recommendation:** CONTEXT_ONLY (captured in design rationale sections)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Removed `--runs` Flag Causing CLI Errors

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Repeated pattern +1)

**Trigger:** Before using `erk plan list --runs` or `erk plan list -r`

**Warning:** "REMOVED: The `--runs` and `-r` flags no longer exist. All plan commands now unconditionally display workflow run columns (PR, checks, comments, learn, remote-impl, run-id, run-state). Remove these flags from scripts and commands."

**Target doc:** `docs/learned/cli/tripwires.md`

This tripwire is valuable because users with existing scripts or muscle memory may attempt to use the removed flags. The error message will inform them, but a tripwire provides proactive guidance explaining the rationale and confirming the new behavior.

### 2. Removed `--show-prs`/`--show-runs` Flags

**Score:** 4/10 (criteria: Non-obvious +2, Cross-cutting +2)

**Trigger:** Before using `erk exec dash-data` with `--show-prs` or `--show-runs` flags

**Warning:** "REMOVED: The `--show-prs` and `--show-runs` flags no longer exist. All columns are now always visible. Remove these flags from exec script calls."

**Target doc:** `docs/learned/cli/tripwires.md`

This affects exec scripts that may have been constructed with these flags. While less common than direct CLI usage, the impact on automated workflows makes this tripwire-worthy.

### 3. PlanFilters Construction with Removed Fields

**Score:** 4/10 (criteria: Non-obvious +2, Cross-cutting +2)

**Trigger:** Before constructing `PlanFilters` with `show_prs` or `show_runs` parameters

**Warning:** "REMOVED: `PlanFilters.show_prs` and `PlanFilters.show_runs` fields no longer exist. Remove these parameters from PlanFilters construction. All plan data now includes PR and workflow run data unconditionally."

**Target doc:** `docs/learned/tui/tripwires.md`

This is critical for any code that constructs PlanFilters instances. The Python error will be clear (unexpected keyword argument), but the tripwire explains why and confirms the new behavior.

## Potential Tripwires

No items scored 2-3. All candidates either met the threshold (>=4) or scored below 2.
