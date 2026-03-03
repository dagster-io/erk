# Plan: Support Objectives Without a Roadmap

## Context

When creating high-level objectives that need more iteration before a concrete roadmap can be defined (e.g., the "Skill Architecture — Capture, Promote, Gate" objective from #8655), `erk objective check` fails because it conflates "no roadmap block" with "legacy format." The objective-create skill already documents "perpetual objectives" with Principles instead of Roadmap, but the validation and view infrastructure rejects them.

**Goal:** Objectives without an `objective-roadmap` metadata block should be valid — they pass validation, display correctly in `erk objective view` and `erk dash`, and the tooling clearly distinguishes "no roadmap" from "broken/legacy roadmap."

## Changes

### 1. `parse_roadmap()` — distinguish "no roadmap" from "legacy format"

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`

Currently line 464-480 returns the legacy error whenever no valid v2 block is found, even when no block exists at all.

**Change:** When `matching_blocks` is empty (no `objective-roadmap` block in the body), return `([], [])` — valid, just no roadmap. Only return the legacy error when a block exists but fails to parse.

```python
def parse_roadmap(body: str) -> tuple[list[RoadmapPhase], list[str]]:
    raw_blocks = extract_raw_metadata_blocks(body)
    matching_blocks = [block for block in raw_blocks if block.key == BlockKeys.OBJECTIVE_ROADMAP]

    if not matching_blocks:
        # No objective-roadmap block at all — valid roadmap-free objective
        return ([], [])

    # Block exists — try to parse it
    roadmap_block = matching_blocks[0]
    try:
        steps = parse_roadmap_frontmatter(roadmap_block.body)
    except ValueError:
        steps = None

    if steps is not None:
        phases = group_nodes_by_phase(steps)
        phases = enrich_phase_names(body, phases)
        return (phases, [])

    # Block exists but failed to parse — legacy/broken format
    return ([], [_LEGACY_FORMAT_ERROR])
```

### 2. `validate_objective()` — make roadmap optional

**File:** `src/erk/cli/commands/objective/check_cmd.py`

**Change Check 2 (lines 106-122):** Detect whether a roadmap block exists. If no block → pass with "no roadmap" message and skip checks 3-7. If block exists but parsing fails → fail as before.

Use `has_metadata_block` from `erk_shared.gateway.github.metadata.core` (already exists) to check for block presence before interpreting `parse_roadmap` results.

```python
from erk_shared.gateway.github.metadata.core import (
    find_metadata_block,
    has_metadata_block,  # ADD this import
)
```

New Check 2 logic:
```python
    # Check 2: Roadmap
    phases, validation_errors = parse_roadmap(issue.body)
    has_roadmap = has_metadata_block(issue.body, BlockKeys.OBJECTIVE_ROADMAP)

    if not has_roadmap:
        # No roadmap block — valid roadmap-free objective
        checks.append((True, "Roadmap: none (objective has no roadmap)"))
        # Skip checks 3-7 (all roadmap-dependent)
        failed_count = sum(1 for passed, _ in checks if not passed)
        return ObjectiveValidationSuccess(
            passed=failed_count == 0,
            checks=checks,
            failed_count=failed_count,
            graph=DependencyGraph(nodes=()),
            summary={},
            next_node=None,
            validation_errors=[],
            issue_body=issue.body,
        )

    if not phases:
        # Block exists but failed to parse
        checks.append((False, f"Roadmap parses successfully ({'; '.join(validation_errors)})"))
        # ... existing early return ...
```

### 3. `_output_human()` — handle empty summary in success display

**File:** `src/erk/cli/commands/objective/check_cmd.py` lines 284-289

When a roadmap-free objective passes, `summary` is `{}`. Display "Objective validation passed" without the "(0/0 done)" suffix.

```python
    if result.passed:
        summary = result.summary
        if summary:
            user_output(
                click.style("Objective validation passed", fg="green")
                + f" ({summary.get('done', 0)}/{summary.get('total_nodes', 0)} done)"
            )
        else:
            user_output(click.style("Objective validation passed", fg="green"))
```

### 4. `view_objective()` — allow viewing roadmap-free objectives

**File:** `src/erk/cli/commands/objective/view_cmd.py` lines 198-205

Currently `parse_v2_roadmap() → None` is treated as a fatal legacy error. Need to distinguish "no block" from "legacy block."

Add import:
```python
from erk_shared.gateway.github.metadata.core import (
    extract_raw_metadata_blocks,  # ADD
)
from erk_shared.gateway.github.metadata.types import BlockKeys  # ADD (if not already)
```

Replace lines 198-206:
```python
    # Parse roadmap from issue body (v2 format only)
    raw_blocks = extract_raw_metadata_blocks(issue.body)
    has_roadmap_block = any(b.key == BlockKeys.OBJECTIVE_ROADMAP for b in raw_blocks)

    if has_roadmap_block:
        v2_result = parse_v2_roadmap(issue.body)
        if v2_result is None:
            raise UserFacingCliError(
                "This objective uses a legacy format that is no longer supported. "
                "To migrate, open Claude Code and use /erk:objective-create to "
                "recreate this objective with the same content."
            )
        phases, _validation_errors = v2_result
    else:
        phases = []
```

The rest of view_cmd.py already handles `phases=[]` correctly — lines 251 (`if phases:`) shows roadmap, lines 369-373 (`else:`) shows "No roadmap data found."

### 5. Update tests

**a. `test_roadmap.py`** — `packages/erk-shared/tests/unit/github/metadata/test_roadmap.py`

Update `test_parse_roadmap_no_metadata_block` (line 162-168):
- Change assertion: `assert errors == []` (was `len(errors) == 1`)
- Remove "legacy format" assertion

Tests `test_parse_roadmap_invalid_frontmatter` and `test_parse_roadmap_legacy_format_returns_error` stay unchanged — they have blocks that fail to parse, so still return legacy error.

**b. `test_check_cmd.py`** — `tests/unit/cli/commands/objective/test_check_cmd.py`

Update `test_malformed_roadmap_fails` (line 164-182):
- Rename to `test_roadmap_free_objective_passes`
- Change `exit_code == 1` to `exit_code == 0`
- Change `[FAIL]` assertion to `[PASS]`
- Assert "no roadmap" in output

Add new test `test_roadmap_free_objective_json_output`:
- Invoke with `--json-output`
- Assert `success: True`, `phases: []`, `summary: {}`, `validation_errors: []`

**c. `test_view_cmd.py`** — `tests/unit/cli/commands/objective/test_view_cmd.py`

Update `test_view_objective_empty_roadmap` (line 199-214):
- Change `exit_code == 1` to `exit_code == 0`
- Remove "legacy format" assertion
- Assert "No roadmap data found" in output

Update `test_view_objective_legacy_format_rejected` (line 346-362):
- `OBJECTIVE_LEGACY_TABLE` has no metadata block → now treated as roadmap-free
- Change `exit_code == 1` to `exit_code == 0`
- Rename to `test_view_objective_table_only_shows_as_roadmap_free`
- Assert "No roadmap data found" in output

`test_view_objective_v1_schema_rejected` (line 365-380) stays unchanged — `OBJECTIVE_V1_SCHEMA` has an `objective-roadmap` metadata block with unsupported schema, so still rejected.

### 6. Update objective-create skill — success reporting

**File:** `.claude/commands/erk/objective-create.md` (line 296-306)

Update the "Report success" section to handle no-roadmap case. When objective has no roadmap:
```
Roadmap validation: none (objective has no roadmap)
```

## Files Modified

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py` | `parse_roadmap()` — return `([], [])` when no block exists |
| `src/erk/cli/commands/objective/check_cmd.py` | `validate_objective()` + `_output_human()` — roadmap optional |
| `src/erk/cli/commands/objective/view_cmd.py` | Guard clause: distinguish no-block from legacy-block |
| `.claude/commands/erk/objective-create.md` | Success reporting for no-roadmap case |
| `packages/erk-shared/tests/unit/github/metadata/test_roadmap.py` | Update no-block test |
| `tests/unit/cli/commands/objective/test_check_cmd.py` | Update + add roadmap-free tests |
| `tests/unit/cli/commands/objective/test_view_cmd.py` | Update empty/legacy tests |

## Files NOT Modified (already handle empty phases)

- `objective_fetch_context.py` — already returns `_empty_roadmap()` when no block
- `plan_data_provider/real.py` — already defaults to `objective_progress_display="-"`
- `update_objective_node.py` — correctly rejects empty phases (can't update nodes without roadmap)
- `plan_issues.py` — already skips roadmap block when none in content

## Verification

1. Run affected tests: `uv run pytest tests/unit/cli/commands/objective/ packages/erk-shared/tests/unit/github/metadata/test_roadmap.py -v`
2. Verify issue #8655 now passes: `erk objective check 8655`
3. Verify view works: `erk objective view 8655`
4. Verify existing objectives with roadmaps still work: pick one from `erk objective list` and run `erk objective check` on it
5. Run broader CI: `make fast-ci`
