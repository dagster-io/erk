# Plan: Port Roadmap Data to YAML Frontmatter (Objective #6629, Step 1.1)

Part of Objective #6629, Step 1.1

## Goal

Migrate roadmap step data from regex-parsed markdown tables to YAML frontmatter within the objective issue body. `parse_roadmap()` reads from frontmatter as primary source, falling back to table parsing for backward compatibility.

## Key Design Decision: Flat Steps, No Phases in Frontmatter

Phases are a **display-only concept**. Frontmatter stores a flat list of steps. Phase membership is derived from the step ID prefix by convention (e.g., "1.2" → phase 1, "2A.1" → phase 2A). Phase names live only in the markdown `### Phase N: Name` headers and are not stored in frontmatter.

This simplifies the dependency graph (step 1.4/1.5) by operating on steps directly without phase-level constraints.

## Architecture

Two-layer protocol (applies only when objectives are persisted as GitHub issues):
- **Transport layer**: `<!-- erk:metadata-block:objective-roadmap -->` wraps the roadmap content (same pattern as plan-header blocks). This metadata block is embedded in the GitHub issue body.
- **Content layer**: YAML frontmatter (`---` delimited) within the metadata block stores structured step data

The markdown table in the issue body remains a **rendered view** (not source of truth). Step 1.2 will handle regenerating tables from frontmatter.

## Frontmatter Schema

```yaml
---
schema_version: "1"
steps:
  - id: "1.1"
    description: "Port existing roadmap data to YAML frontmatter"
    status: "pending"
    pr: null
  - id: "1.2"
    description: "Add table regeneration"
    status: "pending"
    pr: null
  - id: "2.1"
    description: "Implement fetch_objective_tree"
    status: "pending"
    pr: null
---
```

Notes:
- `schema_version: "1"` for future evolution
- `status` uses canonical values: "pending", "done", "in_progress", "blocked", "skipped"
- `pr` is null or string like "#123" / "plan #456"
- Phase derived from step ID prefix (everything before the last `.`)

## Implementation

### Step 1: Create frontmatter parser module

**Create `src/erk/cli/commands/exec/scripts/objective_roadmap_frontmatter.py`**

Functions:
- `parse_roadmap_frontmatter(block_content: str) -> list[RoadmapStep] | None` — parses YAML frontmatter from metadata block content, returns flat list of steps or None if invalid/missing
- `serialize_steps_to_frontmatter(steps: list[RoadmapStep]) -> str` — converts step list to YAML frontmatter string
- `group_steps_by_phase(steps: list[RoadmapStep]) -> list[RoadmapPhase]` — reconstructs `RoadmapPhase` objects from step ID prefixes (for consumers that need grouped access)

Uses `yaml.safe_load` / `yaml.dump` (PyYAML already in deps via `python-frontmatter`).

LBYL validation:
- Check `schema_version` exists and equals "1"
- Check `steps` is a list
- Check each step has required fields (`id`, `description`, `status`)
- Return None on any validation failure (caller falls back to table parsing)

### Step 2: Wire frontmatter into `parse_roadmap()`

**Modify `src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py`**

Update `parse_roadmap(body: str)`:
1. Try to extract `objective-roadmap` metadata block from body using `find_metadata_block()` from `erk_shared.gateway.github.metadata.core`
2. If found, pass block content to `parse_roadmap_frontmatter()`
3. If frontmatter returns steps, use `group_steps_by_phase()` to reconstruct phases
4. Return `(phases, [])` — no validation errors for valid frontmatter
5. If no metadata block or frontmatter fails, fall through to existing regex table parsing

Signature unchanged: `parse_roadmap(body: str) -> tuple[list[RoadmapPhase], list[str]]`

### Step 3: Update `update_roadmap_step` for frontmatter-aware mutation

**Modify `src/erk/cli/commands/exec/scripts/update_roadmap_step.py`**

Currently uses regex to find and replace a single PR cell in the markdown table. With frontmatter as source of truth, this must also update the frontmatter data.

Updated mutation flow:
1. Fetch issue body
2. Check for `objective-roadmap` metadata block
3. **If frontmatter exists:**
   - Parse YAML frontmatter to get step list
   - Find step by ID in the list
   - Update `pr` field on the step (and reset `status` to let inference run)
   - Serialize updated steps back to YAML frontmatter
   - Replace the metadata block content in the issue body
   - Also update the markdown table (keeping it in sync as rendered view)
4. **If no frontmatter (backward compat):**
   - Fall through to existing regex replacement on markdown table

Key functions to add to `objective_roadmap_frontmatter.py`:
- `update_step_in_frontmatter(block_content: str, step_id: str, *, pr: str) -> str | None` — returns updated YAML content, or None if step not found

### Step 4: Audit and update full-body mutation path

**Impact on `objective-update-with-landed-pr` slash command** (`.claude/commands/erk/objective-update-with-landed-pr.md`)

This agent workflow currently rewrites the entire objective body markdown. When frontmatter exists, it must:
1. Parse frontmatter to get current step data
2. Mark the landed step as `done` with PR reference
3. Serialize updated frontmatter back
4. Regenerate the markdown table from frontmatter (step 1.2 dependency — for now, keep table in sync manually)
5. Update the `Current Focus` section

**Deferred to step 1.2:** Full table regeneration from frontmatter. For this step, the agent writes both frontmatter AND table (dual-write strategy to maintain backward compat during migration).

### Mutation Site Audit Summary

All roadmap mutation sites that need frontmatter awareness:

| Mutation Site | Current Method | Change Needed |
|---|---|---|
| `update_roadmap_step.py` | Regex PR cell replacement | Add frontmatter-first path (this step) |
| `objective-update-with-landed-pr.md` | Agent full-body rewrite | Update agent instructions to write frontmatter (this step) |
| `plan-save.md` Step 3.5 | Calls `update-roadmap-step` | No change (indirectly fixed) |
| `check_cmd.py` / `validate_objective()` | Read-only via `parse_roadmap()` | No change (inherits frontmatter support from Step 2) |
| `objective_update_context.py` | Read-only fetch | No change |

Read-only consumers (`parse_roadmap` callers) automatically gain frontmatter support via Step 2.

### Step 5: Tests

**Create `tests/unit/cli/commands/exec/scripts/test_objective_roadmap_frontmatter.py`**

Parser tests:
- `test_parse_valid_frontmatter` — returns correct steps
- `test_parse_no_frontmatter` — returns None
- `test_parse_invalid_yaml` — returns None
- `test_parse_missing_schema_version` — returns None
- `test_parse_wrong_schema_version` — returns None
- `test_serialize_roundtrip` — serialize → parse → same data
- `test_group_steps_by_phase` — "1.1", "1.2", "2.1" → phase 1 (2 steps), phase 2 (1 step)
- `test_group_steps_sub_phases` — "1A.1", "1B.1" → phase 1A (1 step), phase 1B (1 step)

Mutation tests:
- `test_update_step_in_frontmatter` — updates PR field for matching step
- `test_update_step_in_frontmatter_not_found` — returns None for unknown step ID
- `test_update_step_preserves_other_steps` — non-target steps unchanged

**Modify `tests/unit/cli/commands/exec/scripts/test_objective_roadmap_shared.py`**
- `test_parse_roadmap_frontmatter_preferred` — body with metadata block uses frontmatter, not table
- `test_parse_roadmap_no_frontmatter_fallback` — existing behavior preserved

**Modify `tests/unit/cli/commands/exec/scripts/test_update_roadmap_step.py`** (if exists)
- Add test for frontmatter-aware update path
- Add test for fallback to regex when no frontmatter

All existing tests must continue passing unchanged.

## Files

| File | Action |
|------|--------|
| `src/erk/cli/commands/exec/scripts/objective_roadmap_frontmatter.py` | **Create** — frontmatter parser, serializer, phase grouping, step mutation |
| `src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py` | **Modify** — add frontmatter-first logic to `parse_roadmap()` |
| `src/erk/cli/commands/exec/scripts/update_roadmap_step.py` | **Modify** — add frontmatter-aware mutation path |
| `.claude/commands/erk/objective-update-with-landed-pr.md` | **Modify** — update agent instructions for frontmatter dual-write |
| `tests/unit/cli/commands/exec/scripts/test_objective_roadmap_frontmatter.py` | **Create** — frontmatter parser + mutation tests |
| `tests/unit/cli/commands/exec/scripts/test_objective_roadmap_shared.py` | **Modify** — add frontmatter integration tests |

## Key Dependencies to Reuse

- `erk_shared.gateway.github.metadata.core`: `find_metadata_block()`, `render_metadata_block()`, `replace_metadata_block_in_body()`, `parse_metadata_blocks()`
- `erk_shared.gateway.github.metadata.types`: `MetadataBlock`, `RawMetadataBlock`
- `objective_roadmap_shared`: `RoadmapStep`, `RoadmapPhase` (existing dataclasses)
- `yaml` (PyYAML) for YAML parsing/serialization

## What This Step Does NOT Include

- Table regeneration from frontmatter (step 1.2)
- Migration CLI command (step 1.2)
- `parent_objective` field (step 1.3)
- Extended fields: `type`, `depends_on`, `issue` (step 1.4)

## Verification

1. Run existing roadmap tests — all pass (backward compat): `pytest tests/unit/cli/commands/exec/scripts/test_objective_roadmap_shared.py`
2. Run new frontmatter tests: `pytest tests/unit/cli/commands/exec/scripts/test_objective_roadmap_frontmatter.py`
3. Run ty + ruff on modified files
4. `erk objective check <existing-issue>` produces same output (no frontmatter = table fallback)