# Fix: Multi-Node Objective Planning Should Mark All Selected Nodes

## Context

When a user selects multiple nodes for planning (e.g., "Phase 3 (all 3.1-3.5)"), only the first node gets marked as `planning` and stored in the `roadmap-step` marker. The downstream infrastructure (`update-objective-node`, `plan_save.py`) already supports multiple node IDs — the bug is in the skill layer and marker read/write.

## Root Cause

Three layers conspire to drop multi-node info:

1. **`objective-plan-node.md` skill** (Step 4): Creates marker with single `--content "<node-id>"` and calls `update-objective-node` with single `--node`
2. **`read_roadmap_step_marker()`** in `session_markers.py:109`: Returns a single `str | None` — no multi-value support
3. **`plan_save.py:409-411`**: Wraps single marker value into `node_ids = (step_id,)` tuple

But note: `plan_save.py:125` already accepts `node_ids: tuple[str, ...] | None`, and `update-objective-node` already accepts multiple `--node` flags.

## Changes

### 1. Marker: Store comma-separated node IDs in `roadmap-step.marker`

**File:** `packages/erk-shared/src/erk_shared/scratch/session_markers.py`

- Add `read_roadmap_step_markers()` (plural) → returns `tuple[str, ...] | None`
  - Reads marker content, splits on `,`, strips whitespace, filters empty
  - Returns `None` if no marker or all empty
- Keep `read_roadmap_step_marker()` for backwards compat (returns first node or None)

**File:** `packages/erk-shared/tests/unit/scratch/test_session_markers.py`

- Add tests for `read_roadmap_step_markers()` with comma-separated values

### 2. Plan save: Use plural reader

**File:** `src/erk/cli/commands/exec/scripts/plan_save.py`

- Line 67: Import `read_roadmap_step_markers` (add to existing import)
- Lines 408-411: Replace single-value read with:
  ```python
  node_ids = read_roadmap_step_markers(session_id, repo_root)
  ```
  (Already returns `tuple[str, ...] | None`, matches `node_ids` type)

### 3. Skills: Support multi-node arguments

**File:** `.claude/commands/erk/system/objective-plan-node.md`

- Step 1: Parse `$ARGUMENTS` for repeated `--node` flags (e.g., `--node 3.1 --node 3.2 --node 3.3`)
- Step 4: Store comma-separated in marker: `--content "3.1,3.2,3.3"`
- Step 4: Call `update-objective-node` with all `--node` flags: `--node 3.1 --node 3.2 --status planning`
- Line 204: Remove "One node at a time" note; update to "Plans can target one or multiple nodes"
- Update argument-hint to `"<objective-number> --node <node-id> [--node <node-id>...]"`

**File:** `.claude/commands/erk/objective-plan.md`

- Step 5: When user selects a phase (multiple nodes), pass all `--node` flags to inner skill
- Line 150: Remove "One node at a time" constraint
- Update usage example to show multi-node: `/erk:objective-plan 3679 --node 3.1 --node 3.2`
- Step 0 fast path: Support multiple `--node` flags passed through to inner skill

### 4. Workflow markers doc update

**File:** `docs/learned/planning/workflow-markers.md`

- Update `roadmap-step` example to show comma-separated format: `"1B.4,1B.5,1B.6"`

## Files Modified

1. `packages/erk-shared/src/erk_shared/scratch/session_markers.py` — add `read_roadmap_step_markers()`
2. `packages/erk-shared/tests/unit/scratch/test_session_markers.py` — tests for plural reader
3. `src/erk/cli/commands/exec/scripts/plan_save.py` — use plural reader
4. `.claude/commands/erk/system/objective-plan-node.md` — multi-node support
5. `.claude/commands/erk/objective-plan.md` — multi-node selection + passthrough
6. `docs/learned/planning/workflow-markers.md` — update example

## Verification

1. Run unit tests for `session_markers.py` — new `read_roadmap_step_markers()` tests
2. Run unit tests for `plan_save.py` — verify node_ids populated correctly
3. Manual: `/erk:objective-plan 9318 --node 3.1 --node 3.2` should mark both nodes as planning
4. Manual: After plan-save, verify ref.json contains `"node_ids": ["3.1", "3.2"]`
