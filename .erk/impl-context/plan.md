# Fix: Auto-match roadmap nodes by PR reference

## Context

`erk exec objective-apply-landed-update` consistently fails to update any roadmap nodes when called without explicit `--node` flags. The calling agent (via `/erk:objective-update-with-landed-pr`) must then semantically match the PR to a node and re-run with `--node` specified, wasting a full API round-trip every time.

The data for auto-matching already exists: each roadmap node has a `pr` field (e.g., `pr: "#8279"`) set when the node's implementation PR is submitted. The parsed roadmap is available at the point where matching occurs — it just isn't used.

## Changes

### 1. Add auto-match logic in `objective_apply_landed_update.py`

**File**: `src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py`

At line 232, replace:
```python
matched_steps = list(node_ids)
```

With:
```python
if node_ids:
    matched_steps = list(node_ids)
else:
    pr_ref = f"#{pr_number}"
    matched_steps = [
        node["id"]
        for phase in roadmap["phases"]
        for node in phase["nodes"]
        if node["pr"] == pr_ref
    ]
```

Note: `pr_ref` is also defined later at line 238. Move the later definition to use the same variable (or just remove the duplicate since it's the same value).

### 2. Update `TestApplyLandedUpdateNoNodes` test

**File**: `tests/unit/cli/commands/exec/scripts/test_objective_apply_landed_update.py`

The existing `test_no_node_flags_still_posts_comment` test uses `ROADMAP_BODY` where all nodes have `pr: null`, so no auto-match occurs. This test remains valid as-is (no-op when no nodes match).

Add a new test: `test_auto_matches_nodes_by_pr_ref` that:
- Uses a roadmap body where node `1.1` has `pr: "#6517"` and `status: "in_progress"`
- Invokes without `--node` flags
- Asserts `node_updates` contains `1.1` (auto-matched)
- Asserts the issue body was updated

### 3. Update slash command documentation (minor)

**File**: `.claude/commands/erk/objective-update-with-landed-pr.md`

Update lines 41-45 to clarify that `--node` is optional — when omitted, the command auto-matches nodes whose `pr` field references the landing PR.

## Verification

1. Run the updated test file: `pytest tests/unit/cli/commands/exec/scripts/test_objective_apply_landed_update.py`
2. Run type checker on the modified file
3. Verify the existing tests still pass (explicit `--node` flags, no-nodes case, error cases, discovery)
