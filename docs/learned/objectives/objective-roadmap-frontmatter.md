---
title: Objective Roadmap Frontmatter
read_when:
  - "working with roadmap YAML frontmatter"
  - "modifying objective roadmap step data"
  - "understanding the two-layer roadmap protocol"
tripwires:
  - action: "using find_metadata_block() to read roadmap data"
    warning: "Roadmap blocks need raw body content for YAML parsing. Use extract_raw_metadata_blocks() which returns RawMetadataBlock with .body field, not find_metadata_block() which returns MetadataBlock with parsed .data dict."
  - action: "storing phase names in frontmatter YAML"
    warning: "Phase names live only in markdown headers, not frontmatter. Frontmatter stores flat steps; phase membership is derived from step ID prefixes."
  - action: "updating roadmap frontmatter without updating the rendered table"
    warning: "During the dual-write migration period, both YAML frontmatter and markdown table must be updated together. Frontmatter is the source of truth, but the table is the rendered view. Updating one without the other causes drift."
---

# Objective Roadmap Frontmatter

Objective roadmaps use a two-layer protocol: YAML frontmatter as the source of truth for step data, with markdown tables as the rendered view. This document covers the frontmatter layer.

## Architecture: Two-Layer Protocol

<!-- Source: src/erk/cli/commands/exec/scripts/objective_roadmap_frontmatter.py -->

The roadmap system uses two representations in the same metadata block:

1. **YAML frontmatter** (source of truth): Machine-readable step data inside `---` delimiters
2. **Markdown table** (rendered view): Human-readable table below the frontmatter

During the dual-write migration period, both representations must be kept in sync. Mutations update frontmatter first, then regenerate the table.

## Schema Design: Flat Steps with Phase Derivation

<!-- Source: src/erk/cli/commands/exec/scripts/objective_roadmap_frontmatter.py -->

Frontmatter stores a flat list of steps without phase grouping. Phase membership is derived from step ID prefixes:

- `"1.1"`, `"1.2"` -> Phase 1
- `"2A.1"`, `"2A.2"` -> Phase 2A
- `"3.1"` -> Phase 3

Phase names are NOT stored in frontmatter. They live only in markdown headers (`### Phase 1: Planning`). The `_enrich_phase_names()` function in `objective_roadmap_shared.py` extracts names from headers and attaches them to parsed phase objects.

## Key Functions

### objective_roadmap_frontmatter.py (292 lines)

<!-- Source: src/erk/cli/commands/exec/scripts/objective_roadmap_frontmatter.py -->

| Function                                                            | Purpose                                                                           |
| ------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `validate_roadmap_frontmatter(data)`                                | Validates parsed YAML dict against schema, returns `(steps, errors)`              |
| `parse_roadmap_frontmatter(block_content)`                          | Parses YAML frontmatter from block content, returns `list[RoadmapStep]` or `None` |
| `serialize_steps_to_frontmatter(steps)`                             | Converts step list back to YAML frontmatter string with `---` delimiters          |
| `group_steps_by_phase(steps)`                                       | Groups flat steps into `RoadmapPhase` objects by ID prefix                        |
| `update_step_in_frontmatter(block_content, step_id, *, pr, status)` | Updates a single step's PR and status fields in frontmatter                       |

### objective_roadmap_shared.py (284 lines)

<!-- Source: src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py -->

| Function                            | Purpose                                                           |
| ----------------------------------- | ----------------------------------------------------------------- |
| `parse_roadmap(body)`               | Main entry: tries frontmatter first, falls back to table parsing  |
| `_enrich_phase_names(body, phases)` | Extracts phase names from markdown headers and attaches to phases |
| `compute_summary(phases)`           | Computes step count statistics (pending, done, in_progress, etc.) |
| `serialize_phases(phases)`          | Converts phases to JSON-serializable format                       |
| `find_next_step(phases)`            | Returns the first pending step in phase order                     |

## Parsing Flow

`parse_roadmap()` in `objective_roadmap_shared.py` orchestrates the full parsing:

1. Extract raw metadata blocks from issue body using `extract_raw_metadata_blocks()`
2. Find the `objective-roadmap` block
3. If found, parse YAML frontmatter via `parse_roadmap_frontmatter()`
4. If frontmatter succeeds, group steps into phases via `group_steps_by_phase()`
5. Enrich phases with names from markdown headers via `_enrich_phase_names()`
6. If frontmatter parsing fails, fall back to table parsing for backward compatibility

## Integration with Metadata Block Infrastructure

The roadmap frontmatter lives inside a metadata block identified by the key `objective-roadmap`. The block is extracted using `extract_raw_metadata_blocks()` from `erk_shared.gateway.github.metadata.core`, which returns `RawMetadataBlock` with a `.body` field containing the raw content between HTML comment markers.

**Important**: Do NOT use `find_metadata_block()` for roadmap data. That function returns `MetadataBlock` with a `.data` field (parsed YAML dict), which strips the frontmatter delimiters and loses the raw content needed for frontmatter parsing. See [Metadata Blocks Reference](../architecture/metadata-blocks.md) for the type distinction.

## Related Documentation

- [Roadmap Shared Parser Architecture](roadmap-parser-api.md) - Why the shared module exists
- [Roadmap Status System](roadmap-status-system.md) - Status inference logic
- [Metadata Blocks Reference](../architecture/metadata-blocks.md) - Block format and parsing functions
- [Roadmap Schema Reference](../reference/objective-roadmap-schema.md) - Formal schema specification
