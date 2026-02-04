# Plan: Port Roadmap Data to YAML Frontmatter (Objective #6629, Step 1.1)

Part of Objective #6629, Step 1.1

## Goal

Migrate roadmap step data from regex-parsed markdown tables to YAML frontmatter within the objective issue body. `parse_roadmap()` reads from frontmatter as primary source, falling back to table parsing for backward compatibility.

## Key Design Decision: Flat Steps, No Phases in Frontmatter

Phases are a **display-only concept**. Frontmatter stores a flat list of steps. Phase membership is derived from the step ID prefix by convention (e.g., "1.2" → phase 1, "2A.1" → phase 2A). Phase names live only in the markdown `### Phase N: Name` headers and are not stored in frontmatter.

This simplifies the dependency graph (step 1.4/1.5) by operating on steps directly without phase-level constraints.

## Architecture

Two-layer protocol:
- **Transport layer**: `<!-- erk:metadata-block:objective-roadmap -->` wraps the roadmap content (same pattern as plan-header blocks)
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

### Step 3: Tests

**Create `tests/unit/cli/commands/exec/scripts/test_objective_roadmap_frontmatter.py`**
- `test_parse_valid_frontmatter` — returns correct steps
- `test_parse_no_frontmatter` — returns None
- `test_parse_invalid_yaml` — returns None
- `test_parse_missing_schema_version` — returns None
- `test_parse_wrong_schema_version` — returns None
- `test_serialize_roundtrip` — serialize → parse → same data
- `test_group_steps_by_phase` — "1.1", "1.2", "2.1" → phase 1 (2 steps), phase 2 (1 step)
- `test_group_steps_sub_phases` — "1A.1", "1B.1" → phase 1A (1 step), phase 1B (1 step)

**Modify `tests/unit/cli/commands/exec/scripts/test_objective_roadmap_shared.py`**
- `test_parse_roadmap_frontmatter_preferred` — body with metadata block uses frontmatter, not table
- `test_parse_roadmap_no_frontmatter_fallback` — existing behavior preserved

All existing tests must continue passing unchanged.

## Files

| File | Action |
|------|--------|
| `src/erk/cli/commands/exec/scripts/objective_roadmap_frontmatter.py` | **Create** — frontmatter parser, serializer, phase grouping |
| `src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py` | **Modify** — add frontmatter-first logic to `parse_roadmap()` |
| `tests/unit/cli/commands/exec/scripts/test_objective_roadmap_frontmatter.py` | **Create** — frontmatter unit tests |
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