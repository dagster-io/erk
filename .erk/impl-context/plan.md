# Fix multi-node landing: store node_ids in plan-header metadata

## Context

When a PR covers multiple objective nodes (e.g., PR #9319 covered nodes 1.1-1.4), the landing script (`objective_apply_landed_update.py`) only marks one node as done. This is because:

1. `/erk:objective-plan` creates a `roadmap-step.marker` with a single node ID ("1.1")
2. `plan_save.py` wraps this in `node_ids = (step_id,)` and stores it in `ref.json`
3. `objective_link_pr.py` sets `pr: '#9319'` only on node 1.1 in the roadmap
4. At landing time, auto-discovery scans for `node["pr"] == "#9319"` — finds only node 1.1
5. Nodes 1.2-1.4 are never auto-discovered

**Root cause**: `node_ids` are stored in `ref.json` (branch-local, ephemeral) but NOT in plan-header metadata (PR body, durable). The landing script has no way to read node_ids from the plan/PR.

**Fix**: Store `node_ids` in plan-header metadata and use them as the primary auto-discovery source in the landing script.

## Implementation (TDD)

### Cycle 1: Add node_ids to Plan dataclass and plan-header schema

**Red** — Write failing tests:
- `tests/unit/plan_store/test_planned_pr_backend.py`: Test that `pr_details_to_plan` parses `node_ids` from plan-header YAML
- `tests/unit/cli/commands/exec/scripts/test_objective_apply_landed_update.py`: Test `test_auto_matches_nodes_from_plan_metadata` — PR has `node_ids: ["1.1", "1.2"]` in plan-header, objective roadmap has NO pr refs set on those nodes, landing auto-discovers both nodes

**Green** — Make tests pass:

1. **`packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py`**
   - Add `NODE_IDS: Literal["node_ids"] = "node_ids"` constant (after `OBJECTIVE_ISSUE`)
   - Add `NODE_IDS` to `PlanHeaderSchema.optional_fields` set
   - Add validation: `node_ids` must be a list of strings or null

2. **`packages/erk-shared/src/erk_shared/plan_store/types.py`**
   - Add `node_ids: tuple[str, ...] | None = None` to `Plan` dataclass (after `header_fields`, with default)

3. **`packages/erk-shared/src/erk_shared/plan_store/conversion.py`**
   - In `pr_details_to_plan()`: Parse `node_ids` from `header_fields` (list of strings → tuple)
   - In `github_issue_to_plan()`: Same parsing
   - Pass `node_ids=` to Plan constructor
   - Add import: `from erk_shared.gateway.github.metadata.schemas import NODE_IDS`

4. **`src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py`** (lines 249-257)
   - Change auto-discovery to use `plan_result.node_ids` as primary source:
   ```python
   if node_ids:
       matched_steps = list(node_ids)
   elif plan_result.node_ids:
       matched_steps = list(plan_result.node_ids)
   else:
       matched_steps = [
           node["id"]
           for phase in roadmap["phases"]
           for node in phase["nodes"]
           if node["pr"] == pr_ref
       ]
   ```

### Cycle 2: Write node_ids to plan-header during plan creation

**Red** — Write failing test:
- `tests/unit/plan_store/test_planned_pr_backend.py`: Test that `create_managed_pr` writes `node_ids` to plan-header when provided in metadata

**Green** — Make test pass:

5. **`packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py`**
   - Add `node_ids: list[str] | None` parameter to `create_plan_header_block()` and `format_plan_header_body()`
   - Include `NODE_IDS: node_ids` in the metadata dict when not None
   - Add import: `from erk_shared.gateway.github.metadata.schemas import NODE_IDS`

6. **`packages/erk-shared/src/erk_shared/plan_store/planned_pr.py`** (`create_managed_pr` ~line 325)
   - Parse `node_ids` from metadata dict (same as objective_issue pattern)
   - Pass `node_ids=` to `format_plan_header_body()`

7. **`src/erk/cli/commands/exec/scripts/plan_save.py`**
   - Already stores `node_ids` in `ref.json` — now also pass to plan metadata:
   - Add `"node_ids": list(node_ids) if node_ids else None` to the metadata dict passed to `create_managed_pr`

### Cycle 3: Extract function + update existing plan node_ids

**Red** — Write failing test:
- `tests/unit/plan_store/test_planned_pr_backend.py` or new test file: Test `extract_plan_header_node_ids()` returns parsed node IDs
- `tests/unit/plan_store/test_planned_pr_backend.py`: Test `update_plan_header_node_ids()` updates node_ids in existing plan-header

**Green** — Make test pass:

8. **`packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py`**
   - Add `extract_plan_header_node_ids(issue_body) -> tuple[str, ...] | None` (follows existing pattern)
   - Add `update_plan_header_node_ids(issue_body, node_ids) -> str` (follows existing update pattern)

### Files modified (all paths from repo root)

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py` | Add `NODE_IDS` constant + validation |
| `packages/erk-shared/src/erk_shared/plan_store/types.py` | Add `node_ids` to Plan |
| `packages/erk-shared/src/erk_shared/plan_store/conversion.py` | Parse node_ids from header |
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py` | Add node_ids param, extract/update functions |
| `packages/erk-shared/src/erk_shared/plan_store/planned_pr.py` | Pass node_ids through creation |
| `src/erk/cli/commands/exec/scripts/plan_save.py` | Pass node_ids to metadata |
| `src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py` | Use plan metadata for auto-discovery |

### Existing utilities to reuse

- `find_metadata_block()` / `extract_metadata_value()` in `metadata/core.py` — for parsing
- `replace_metadata_block_in_body()` in `metadata/core.py` — for updating
- `_parse_objective_id()` pattern in `planned_pr.py` — for parsing node_ids from YAML
- `extract_plan_header_*()` pattern in `plan_header.py` — for new extract function
- `update_plan_header_*()` pattern in `plan_header.py` — for new update function
- `context_for_test()` in `tests/fakes/tests/shared_context.py` — for test setup
- Existing test fixtures in `test_objective_apply_landed_update.py` — `ROADMAP_BODY`, `PLAN_BODY_WITH_OBJECTIVE`, etc.

## Verification

1. Run existing tests to ensure no regressions:
   ```
   pytest tests/unit/cli/commands/exec/scripts/test_objective_apply_landed_update.py
   pytest tests/unit/plan_store/
   ```

2. Run new tests for each TDD cycle

3. Run full CI:
   ```
   make fast-ci
   ```
