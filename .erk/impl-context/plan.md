# Plan: Add fetch timing instrumentation to `erk dash`

## Context

`erk dash` Plans tab takes 6.6s to load (shown in status bar). PR #8168 attempted to speed this up with REST+GraphQL two-step and learn state removal, but isn't merged yet, and the actual bottleneck hasn't been diagnosed with data. Before optimizing further, we need to see WHERE the 6.6 seconds goes.

The data loading pipeline has these sequential phases:
1. **REST issues list** — `gh api` subprocess → REST GET /issues (server-side filtering)
2. **GraphQL PR enrichment** — `gh api graphql` subprocess → batched `pullRequest(number: N)`
3. **Plan body parsing** — extract metadata, parse headers for each of 27 PRs
4. **Workflow runs fetch** — `gh api graphql` subprocess → `nodes(ids: [...])` query
5. **Worktree mapping** — `git worktree list` + read `.impl/plan-ref.json` per worktree
6. **Row building** — `_build_row_data()` loop for each plan

We need timing for each phase to make data-driven optimization decisions.

## Approach: FetchTimings dataclass returned alongside rows

Add a `FetchTimings` frozen dataclass that captures millisecond-level timing for each phase. Thread it through the return path and display in the status bar.

### Step 1: Add FetchTimings dataclass

**File:** `src/erk/tui/data/types.py`

```python
@dataclass(frozen=True)
class FetchTimings:
    """Timing breakdown for a single fetch cycle."""
    rest_issues_ms: float
    graphql_enrich_ms: float
    plan_parsing_ms: float
    workflow_runs_ms: float
    worktree_mapping_ms: float
    row_building_ms: float
    total_ms: float

    def summary(self) -> str:
        """One-line summary for status bar: 'rest:1.2 gql:2.3 wf:0.8 rows:0.3 = 4.6s'"""
        parts = []
        if self.rest_issues_ms > 0:
            parts.append(f"rest:{self.rest_issues_ms / 1000:.1f}")
        if self.graphql_enrich_ms > 0:
            parts.append(f"gql:{self.graphql_enrich_ms / 1000:.1f}")
        if self.plan_parsing_ms > 100:
            parts.append(f"parse:{self.plan_parsing_ms / 1000:.1f}")
        if self.workflow_runs_ms > 0:
            parts.append(f"wf:{self.workflow_runs_ms / 1000:.1f}")
        if self.worktree_mapping_ms > 100:
            parts.append(f"wt:{self.worktree_mapping_ms / 1000:.1f}")
        if self.row_building_ms > 100:
            parts.append(f"rows:{self.row_building_ms / 1000:.1f}")
        return " ".join(parts) + f" = {self.total_ms / 1000:.1f}s"
```

### Step 2: Instrument PlannedPRPlanListService.get_plan_list_data

**File:** `src/erk/core/services/plan_list_service.py`

Add `time.monotonic()` checkpoints around:
- `list_plan_prs_with_details()` call (this covers REST + GraphQL enrichment combined)
- Plan body parsing loop
- `get_workflow_runs_by_node_ids()` call

Return timings as new fields on `PlanListData` (or as a separate return value).

### Step 3: Instrument list_plan_prs_with_details

**File:** `packages/erk-shared/src/erk_shared/gateway/github/real.py`

Split timing for REST vs GraphQL enrichment within `list_plan_prs_with_details`:
- Time the REST `gh api` call separately
- Time `_enrich_prs_via_graphql` separately
- Return both values (add to a timings dict or log them)

Approach: add `logger.info()` calls with timing. The plan_list_service can also wrap the outer call for end-to-end timing.

### Step 4: Instrument RealPlanDataProvider.fetch_plans

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

Add timing around:
- `get_plan_list_data()` (API calls phase)
- `_build_worktree_mapping()`
- Row building loop

Return `FetchTimings` alongside the rows. Change `fetch_plans` signature:
```python
def fetch_plans(self, filters: PlanFilters) -> tuple[list[PlanRowData], FetchTimings | None]:
```

### Step 5: Update ABC and fakes

**Files:**
- `src/erk/tui/data/provider.py` — update `PlanDataProvider` ABC signature
- `tests/fakes/plan_data_provider.py` — update `FakePlanDataProvider` to return `None` timings

### Step 6: Display in status bar

**File:** `src/erk/tui/app.py`

Pass `FetchTimings` to `_update_table`, then to `StatusBar.set_last_update`:
```python
# Current: updated: 05:59:47 (6.6s)
# New:     updated: 05:59:47 (6.6s) rest:1.2 gql:2.3 wf:0.8 rows:0.3
```

**File:** `src/erk/tui/widgets/status_bar.py`

Add `_fetch_timings` field, display `timings.summary()` after the duration.

### Step 7: Also add logger.info timing in the GitHub gateway

**File:** `packages/erk-shared/src/erk_shared/gateway/github/real.py`

Add `logger.info("list_plan_prs_with_details: REST=%.0fms GraphQL=%.0fms merge=%.0fms", ...)`

This helps with non-TUI debugging (e.g., `erk dash` static mode or future log review).

## Files to modify

1. `src/erk/tui/data/types.py` — add `FetchTimings` dataclass
2. `src/erk/core/services/plan_list_service.py` — add timing to `get_plan_list_data`
3. `packages/erk-shared/src/erk_shared/gateway/github/real.py` — timing in `list_plan_prs_with_details`
4. `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` — timing in `fetch_plans`
5. `src/erk/tui/data/provider.py` — update ABC return type
6. `src/erk/tui/app.py` — pass timings to status bar
7. `src/erk/tui/widgets/status_bar.py` — display timing breakdown
8. `packages/erk-shared/src/erk_shared/core/plan_list_service.py` — add timing fields to PlanListData
9. `tests/fakes/plan_data_provider.py` — update fake signature

## Key reuse

- `time.monotonic()` already used in `app.py:203` for total duration
- `FetchTimings` follows the frozen dataclass pattern
- `PlanListData` already in `packages/erk-shared/src/erk_shared/core/plan_list_service.py` — add timing fields there
- Status bar already has `_fetch_duration` display logic to extend

## Verification

1. Run `erk dash` and observe the timing breakdown in the status bar
2. Verify each phase timing adds up to approximately the total
3. Run `make fast-ci` to ensure tests pass
4. Use timing data to identify the actual bottleneck for the next optimization PR
