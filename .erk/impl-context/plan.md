# Fix: Objective #7978 Display Shows All Dashes Due to `status: '-'`

## Context

Objective #7978 (unify-cli-pr-universal-stages) displays all dashes in `erk dash` for the `prog`, `state`, `head-state`, `head`, and `next` columns. The issue has 2 pending nodes remaining (4.3, 4.4 — the "two steps left") but the TUI can't see any of them.

Root cause: nodes 4.1 and 4.2 have `status: '-'` in the roadmap YAML (set alongside `pr: '#8208'`). The string `'-'` is the *display symbol* for the `skipped` status, but it's not the canonical status value. `validate_roadmap_frontmatter()` in `roadmap.py:122–125` rejects any unrecognized status and returns `(None, errors)`, causing the entire roadmap to fail. `parse_roadmap()` then returns empty phases, so the TUI has no data to display.

## Fix

### 1. Normalize `'-'` → `'skipped'` in the parser

In `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`, add normalization immediately after reading the `status` field (line 109), before the validity check at line 122:

**File**: `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`

Change this (around line 109):
```python
status = step_dict["status"]
```

To:
```python
status = step_dict["status"]
# '-' is the display symbol for 'skipped'; normalize it
if status == "-":
    status = "skipped"
```

This is a 2-line addition before the existing `isinstance` check and the `status not in {...}` guard.

### 2. Add test

**File**: `packages/erk-shared/tests/unit/github/metadata/test_roadmap_frontmatter.py`

Add a test verifying that a node with `status: '-'` is normalized to `'skipped'` and doesn't cause validation to fail:

```python
def test_dash_status_normalized_to_skipped() -> None:
    """'-' is the display symbol for skipped; it should be accepted and normalized."""
    data = {
        "schema_version": "4",
        "nodes": [
            {"id": "1.1", "description": "Done task", "status": "done", "pr": "#100"},
            {"id": "1.2", "description": "Skipped via dash", "status": "-", "pr": "#200"},
        ],
    }
    steps, errors = validate_roadmap_frontmatter(data)
    assert errors == []
    assert steps is not None
    assert steps[1].status == "skipped"
```

## Critical Files

- `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py:109–125` — add normalization
- `packages/erk-shared/tests/unit/github/metadata/test_roadmap_frontmatter.py` — add test

## Verification

1. Run `uv run pytest packages/erk-shared/tests/unit/github/metadata/test_roadmap_frontmatter.py` — new test passes
2. Run `erk objective check 7978` — should show roadmap data, no longer all dashes
3. Run `erk dash` and navigate to Objectives tab — #7978 should show `11/13` progress (11 done + 2 skipped = 13 terminal, 2 pending remaining), state sparkline with checkmarks/dashes, and next node `4.3`
