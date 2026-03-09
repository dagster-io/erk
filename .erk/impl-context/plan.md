# Plan: Support multi-node roadmap markers in objective-plan flow

## Context

When `/erk:objective-plan` is used and the user selects multiple nodes (e.g., "all of Phase 1"), the roadmap nodes are never marked as in-progress after plan-save. This is because:

1. The outer skill (`objective-plan.md`) delegates to the inner skill (`objective-plan-node.md`) which only accepts a single `--node` flag
2. The `roadmap-step` marker stores a single node ID
3. `plan-save.md` Step 6 reads the marker and calls `update-objective-node` with one `--node`

When the user bypasses the inner skill (as happened here — Claude handled the multi-node case directly), no `roadmap-step` marker is created at all, so plan-save skips the roadmap update entirely.

**Root cause:** The marker system and skill flow assume one-node-per-plan, but users can legitimately plan multiple nodes together.

## Fix

Support newline-delimited multi-node values in the `roadmap-step` marker. The downstream `update-objective-node` command already supports multiple `--node` flags, so the fix is purely in the marker layer and skill instructions.

### Step 1: Update `read_roadmap_step_marker()` to return `list[str]`

**File:** `packages/erk-shared/src/erk_shared/scratch/session_markers.py` (lines 109-130)

Change return type from `str | None` to `list[str]`. Parse newline-delimited content. Return empty list instead of None.

```python
def read_roadmap_step_marker(session_id: str, repo_root: Path) -> list[str]:
    """Read roadmap node IDs from session's roadmap-step marker.

    Supports both single-node markers (legacy) and multi-node markers
    (newline-delimited). Returns empty list if marker doesn't exist.
    """
    marker_dir = get_scratch_dir(session_id, repo_root=repo_root)
    marker_file = marker_dir / "roadmap-step.marker"
    if not marker_file.exists():
        return []
    content = marker_file.read_text(encoding="utf-8").strip()
    if not content:
        return []
    return [line.strip() for line in content.split("\n") if line.strip()]
```

Backward compatible: old single-value marker `"1.3"` splits to `["1.3"]`.

### Step 2: Update `plan_save.py` to handle list

**File:** `src/erk/cli/commands/exec/scripts/plan_save.py` (lines 404-407)

Change from wrapping single value in tuple to using the list directly:

```python
# Before:
if session_id is not None:
    step_id = read_roadmap_step_marker(session_id, repo_root)
    if step_id is not None:
        node_ids = (step_id,)

# After:
if session_id is not None:
    step_ids = read_roadmap_step_marker(session_id, repo_root)
    if step_ids:
        node_ids = tuple(step_ids)
```

### Step 3: Update `objective-plan.md` to support multi-node selection

**File:** `.claude/commands/erk/objective-plan.md` (Step 4)

Change the AskUserQuestion in Step 4 to use `multiSelect: true` and add a "whole phase" option. When user selects multiple nodes or a phase:

- Store all selected node IDs in the marker (newline-delimited)
- Invoke the inner skill with the first node as `--node` but also create the multi-node marker

Actually, simpler approach: when the user selects multiple nodes in Step 4, **don't delegate to the inner skill**. Instead, handle directly:
1. Create objective-context marker
2. Create roadmap-step marker with all node IDs (newline-delimited)
3. Mark all nodes as `planning` via `update-objective-node --node X --node Y --status planning`
4. Enter plan mode
5. Plan-save handles the rest (reads multi-node marker, updates all nodes)

Update Step 4 to add multi-select and phase-level options. Update Step 5 to branch:
- Single node → delegate to inner skill (existing behavior)
- Multiple nodes → handle inline (create markers, enter plan mode, plan-save)

### Step 4: Update `plan-save.md` Step 6 for multi-node

**File:** `.claude/commands/erk/plan-save.md` (Step 6, lines 137-163)

Change from reading single `step_id` to reading all node IDs and passing multiple `--node` flags:

```bash
# Before:
step_id=$(erk exec marker read --session-id "${CLAUDE_SESSION_ID}" roadmap-step)
erk exec update-objective-node <objective-issue> --node "$step_id" --pr "#<plan_number>" --status in_progress

# After:
node_ids=$(erk exec marker read --session-id "${CLAUDE_SESSION_ID}" roadmap-step)
# node_ids may contain multiple lines — build --node flags for each
node_flags=""
while IFS= read -r node_id; do
  [ -n "$node_id" ] && node_flags="$node_flags --node $node_id"
done <<< "$node_ids"
erk exec update-objective-node <objective-issue> $node_flags --pr "#<plan_number>" --status in_progress
```

### Step 5: Update tests

**File:** Tests for `read_roadmap_step_marker` — update assertions for list return type.
**File:** Tests for `plan_save.py` — verify multi-node marker is parsed correctly.

## Files to modify

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/scratch/session_markers.py` | `read_roadmap_step_marker` returns `list[str]` |
| `src/erk/cli/commands/exec/scripts/plan_save.py` | Handle list from marker |
| `.claude/commands/erk/objective-plan.md` | Add multi-select, handle inline for multi-node |
| `.claude/commands/erk/plan-save.md` | Step 6 handles multiple node IDs |
| Tests for session_markers and plan_save | Update for new return type |

## Verification

1. Run unit tests for `session_markers.py` and `plan_save.py`
2. Manual test: `/erk:objective-plan` → select multiple nodes → `/erk:plan-save` → verify all nodes updated in roadmap
3. Backward compat: single-node selection still works (old marker format parses correctly)
