<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2026-02-19T12:08:31.767033+00:00'
created_by: schrockn
plan_comment_id: null
last_dispatched_run_id: '22191972315'
last_dispatched_node_id: WFR_kwLOPxC3hc8AAAAFKr6f2w
last_dispatched_at: '2026-02-19T17:10:01.105996+00:00'
last_local_impl_at: null
last_local_impl_event: null
last_local_impl_session: null
last_local_impl_user: null
last_remote_impl_at: null
last_remote_impl_run_id: null
last_remote_impl_session_id: null
branch_name: plan-O7390-plan-enhance-objecti-02-19-1208
objective_issue: 7390
created_from_session: 387aed58-b13d-43ce-a558-ad0689a3c266

```

</details>
<!-- /erk:metadata-block:plan-header -->

---

<details>
<summary>original-plan</summary>

# Plan: Enhance Objective View for Parallel In-Flight Status

**Objective**: #7390 node 2.3
**Scope**: `erk objective view` CLI command

## Context

The `--all-unblocked` feature (node 2.1) dispatches multiple objective nodes simultaneously, and batch atomic updates (node 2.2) mark them as `planning` status. However, the `erk objective view` command doesn't clearly surface this parallel work:

1. The `planning` status has no display handler — it silently falls through to the `pending` default in `_format_node_status()`
2. There's no "at a glance" view of what's currently in flight across phases
3. The summary doesn't show planning/dispatched counts

## Changes

### 1. Add `planning` status to `_format_node_status()`

**File**: `src/erk/cli/commands/objective/view_cmd.py` (line ~91)

Add a case for `planning` between `skipped` and the default pending case:
```python
if status == "planning":
    ref_text = f" plan {escape(plan)}" if plan else ""
    return f"[yellow]📋 planning{ref_text}[/yellow]"
```

### 2. Add "In Flight" section to view display

**File**: `src/erk/cli/commands/objective/view_cmd.py`

After the `─── Roadmap ───` header (line 249), before the phase tables (line 280), add an "In Flight" section that shows all nodes with `planning` or `in_progress` status grouped together.

- Only show when there are 1+ in-flight nodes
- Header: `─── In Flight (N dispatched) ───`
- Render as a compact Rich table with columns: node, status, description, plan, pr
- Reuse `_format_node_status()` and `_format_ref_link()` for consistency

This gives immediate visibility into what's running in parallel without changing the existing phase table structure.

Collect in-flight nodes:
```python
in_flight_nodes = [
    (step, phase)
    for phase in phases
    for step in phase.nodes
    if step.status in ("planning", "in_progress")
]
```

### 3. Enhance summary section

**File**: `src/erk/cli/commands/objective/view_cmd.py` (lines 324-356)

Update the Nodes line to include `planning` count when > 0:
```
Nodes:       3/7 done, 1 in progress, 2 planning, 1 pending
```

Add "In flight" line showing total dispatched count (planning + in_progress):
```
In flight:   3 (1 in progress, 2 planning)
```
Only show this line when count > 0.

Keep "Unblocked" line as-is (shows pending unblocked count — what's ready to dispatch next).

### 4. Update JSON output

**File**: `src/erk/cli/commands/objective/view_cmd.py`, `_display_json()` (lines 125-156)

Add to the graph dict:
- `in_flight`: list of node IDs with planning or in_progress status

The `summary` dict already includes `planning` count from `compute_graph_summary()`.

### 5. Tests

**File**: `tests/unit/cli/commands/objective/test_view_cmd.py`

Add a new test fixture `OBJECTIVE_WITH_PARALLEL_DISPATCH` using schema v3 with:
- 1.1: done
- 2.1: planning (dispatched, depends on 1.1)
- 2.2: in_progress (dispatched, depends on 1.1)
- 2.3: pending (depends on 1.1, unblocked)
- 3.1: pending (depends on 2.1, 2.2, 2.3 — blocked)

New tests:
- `test_view_planning_status_emoji()`: planning status shows 📋 emoji
- `test_view_in_flight_section_shown()`: "In Flight" section appears with correct count when dispatched nodes exist
- `test_view_in_flight_section_hidden()`: "In Flight" section not shown when no active nodes (use existing OBJECTIVE_WITH_ROADMAP which has no planning nodes — but it does have in_progress, so we need a fixture with only done/pending)
- `test_view_summary_shows_planning_count()`: Summary includes planning count
- `test_view_summary_shows_in_flight_line()`: "In flight:" line with breakdown
- `test_view_json_includes_in_flight()`: JSON output has in_flight field

## Files Modified

| File | Change |
|------|--------|
| `src/erk/cli/commands/objective/view_cmd.py` | Add planning status, In Flight section, enhanced summary, JSON update |
| `tests/unit/cli/commands/objective/test_view_cmd.py` | New fixture and 5-6 new tests |

## Verification

1. Run tests: `uv run pytest tests/unit/cli/commands/objective/test_view_cmd.py`
2. Run type checker on changed files
3. Run linter/formatter
4. Manual check: `erk objective view 7390` to verify output against the real objective


</details>
---


To checkout this PR in a fresh worktree and environment locally, run:

```
source "$(erk pr checkout 7591 --script)" && erk pr sync --dangerous
```
