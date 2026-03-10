---
name: erk-tui-data-layer
description: PlanRowData, PlanFilters, column addition, data contracts, and frozen dataclass management
---

# TUI Data Layer

**Read this when**: Adding columns, modifying `PlanRowData`, changing `PlanFilters`, working with the provider ABC, or managing frozen dataclass fields.

## PlanRowData: Display-vs-Raw Duality

`PlanRowData` is a frozen dataclass with 47+ fields carrying both raw data and pre-formatted display strings.

**The duality pattern**:

- **Display fields** (`*_display`): Pre-formatted with emoji, relative times, etc. Ready for rendering.
- **Raw fields**: Actual identifiers, URLs, timestamps for actions and sorting.

```python
@dataclass(frozen=True)
class PlanRowData:
    plan_id: int              # Raw: used in predicates, sorting, API calls
    pr_display: str           # Display: rendered directly in table cell
    pr_number: int | None     # Raw: used by command availability predicates
    lifecycle_display: str    # Display: pre-formatted with color markup
    ...
```

**Why this matters**: DataTable renders frequently (scroll, resize, focus). Formatting at render time causes visible UI lag. Pushing formatting into `_build_row_data()` eliminates inconsistencies and keeps rendering fast.

## 5-Step Column Addition Checklist

Adding a column requires coordinated changes across FIVE files. Missing any one causes failures.

| Step | File                         | Change                                                   |
| ---- | ---------------------------- | -------------------------------------------------------- |
| 1    | `tui/data/types.py`          | Add raw field + display field to `PlanRowData`           |
| 2    | `plan_data_provider/real.py` | Populate both fields in `_build_row_data()`              |
| 3    | `tui/widgets/plan_table.py`  | Add column definition + value in `_row_to_values()`      |
| 4    | `plan_data_provider/fake.py` | Add parameter to `make_plan_row()` with sentinel default |
| 5    | `dash_data.py`               | Handle serialization if non-primitive type               |

**Derived columns shortcut**: If reusing an existing `PlanRowData` field, skip steps 1, 2, 4, 5. Only add the column definition (step 3).

**After adding/reordering columns**: Run systematic grep for `row[`, `values[`, `cells[` — column index changes invalidate ALL test assertions using indices.

## PlanFilters Construction

`PlanFilters` is a frozen dataclass. When constructing new filters in `_load_data()`, ALL fields must be explicitly copied from existing filters.

```python
# WRONG — missing fields cause silent filtering failures
filters = PlanFilters(labels=new_labels)

# CORRECT — copy all fields explicitly
filters = PlanFilters(
    labels=new_labels,
    creator=self._filters.creator,
    text_filter=self._filters.text_filter,
    ...
)
```

## Cross-Package Data Contract

| Artifact                     | Location                                             | Why                        |
| ---------------------------- | ---------------------------------------------------- | -------------------------- |
| `PlanRowData`, `PlanFilters` | `src/erk/tui/data/types.py`                          | TUI-specific display types |
| `PlanDataProvider` ABC       | `packages/erk-shared/.../plan_data_provider/abc.py`  | Shared interface           |
| `RealPlanDataProvider`       | `packages/erk-shared/.../plan_data_provider/real.py` | Production implementation  |
| `FakePlanDataProvider`       | `packages/erk-shared/.../plan_data_provider/fake.py` | Test double                |

**Transformation pipeline**:

1. `IssueInfo` (raw GitHub API response)
2. `Plan` (domain model with parsed metadata)
3. `PlanRowData` (display-ready with worktree data, PR linkages)

**Extending the ABC**: Requires 3-file update (abc.py + real.py + fake.py). The fake must initialize any new dict in `__init__` or tests get `AttributeError`.

## JSON Serialization Gotchas

`dataclasses.asdict()` doesn't handle three types:

1. **`datetime` fields**: Convert to ISO 8601 strings via `.isoformat()`
2. **`tuple[tuple[...]]`** (log_entries): Convert to list of lists
3. **Display strings with emoji**: Frontend-specific handling

See `_serialize_plan_row()` in `dash_data.py` for production implementation.

## Frozen Dataclass Field Management

**Adding a field**: Follow the 5-step column addition checklist above.

**Removing a field** — 6-place checklist:

1. Remove from `PlanRowData` definition
2. Remove from `RealPlanDataProvider._build_row_data()`
3. Remove from `FakePlanDataProvider` and `make_plan_row()` helper
4. Remove from `PlanDataTable._row_to_values()`
5. Remove from filtering/sorting logic
6. Remove from documentation

**Construction rule**: Always use keyword arguments. Positional arguments break silently when fields are reordered.

```python
# WRONG — breaks if fields reorder
row = PlanRowData(123, None, None, ...)

# CORRECT — survives field reordering
row = PlanRowData(plan_id=123, plan_url=None, ...)

# BEST — use test helper
row = make_plan_row(123, "Title", pr_number=456)
```

## PlanRowData Field Reference

`PlanRowData` has 48+ fields organized by category. See `src/erk/tui/data/types.py` for the full definition.

**Key categories**: Identifiers (plan_id, plan_url, pr_number, pr_url), Title (title, full_title, pr_title), Metadata (author, created_at, created_display), Display Strings (10 `*_display` fields), Worktree (worktree_name, exists_locally, worktree_branch, pr_head_branch), Timestamps, GitHub Actions (run_id, run_status, run_conclusion, run_url, log_entries), PR State (pr_state, resolved/total_comment_count), Learn Status (5 fields), Objective (objective_issue + 10 display fields).

**Availability predicate patterns**:

```python
is_available=lambda ctx: ctx.row.pr_number is not None   # Needs PR
is_available=lambda ctx: ctx.row.plan_url is not None     # Needs plan URL
is_available=lambda ctx: ctx.row.exists_locally           # Needs local worktree
is_available=lambda _: True                               # Always available
```

**Rule**: Use raw fields in predicates (for `None` checks), display fields for rendering.

## PlanDataProvider ABC

Located in `packages/erk-shared/.../plan_data_provider/abc.py`. 3 abstract properties (`repo_root`, `clipboard`, `browser`) and 7 abstract methods (`fetch_plans`, `close_plan`, `dispatch_to_queue`, `fetch_branch_activity`, `fetch_plan_content`, `fetch_objective_content`, `fetch_unresolved_comments`).

## PlanFilters Field Reference

Frozen dataclass in `src/erk/tui/data/types.py` with 7 fields: `labels` (tuple[str, ...]), `state` (str | None), `run_state` (str | None), `limit` (int | None), `show_prs` (bool), `show_runs` (bool), `creator` (str | None). Use `PlanFilters.default()` for standard open erk-plan queries.

## Dashboard Column Inventory

See `PlanDataTable._setup_columns()` in `src/erk/tui/widgets/plan_table.py` for the full column layout. Key facts:

- **Backend-conditional columns**: `stage` (8-char lifecycle) and `sts` (status indicators) only appear in `planned_pr` mode
- **`plan`/`pr` header**: Shows `plan` for issue-based, `pr` for planned_pr backend
- **`created` column position**: After `sts` in planned_pr mode, after `run` in issue mode
- **Objectives view**: Completely different column set (issue, slug, prog, state, deps-state, deps, next, updated, created by)

## RunRowData

Frozen dataclass for the Runs tab. See `src/erk/tui/data/types.py` for fields and `src/erk/tui/widgets/run_table.py` for columns.

**Branch resolution priority**: PR `head_branch` first (from `get_pr_head_branches()` batch query), then `run.branch` (if not master/main), then `"-"`. After merge+deletion, `run.branch` becomes the default branch, so PR head_branch is the reliable source.

## Column Reordering Warning

Reordering columns changes index-based value positions in `_row_to_values()`. This invalidates ALL test assertions referencing columns by index (`row[N]`, `values[N]`, `cells[N]`). Before reordering, grep test files for these patterns and update every reference after.

**View-specific columns**: If `_row_to_values()` has branching logic (plans vs objectives), verify both branches produce matching column counts. Mismatches cause silent DataTable rendering errors.
