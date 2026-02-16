---
title: Consolidated Roadmap Module Architecture
read_when:
  - "understanding the roadmap parsing and serialization module structure"
  - "adding new roadmap-related functionality"
  - "understanding why three modules were consolidated into one"
last_audited: "2026-02-15 17:17 PT"
---

# Roadmap Utilities Module

## Location

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py -->

`packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`

## Why Consolidated

Three separate modules (`objective_roadmap_shared.py`, `objective_roadmap_frontmatter.py`, and scattered parsing utilities) were consolidated into one because they:

1. Defined the same types (`RoadmapStep`, `RoadmapPhase`)
2. Operated on the same domain (objective roadmaps)
3. Required mutual imports within the same package

Consolidation eliminated duplicate type definitions and removed the need for cross-module imports within the same domain.

## Module Organization

The module is organized in dependency order:

1. **Data Types** — `RoadmapStepStatus`, `RoadmapStep`, `RoadmapPhase`
2. **Validation** — `validate_roadmap_frontmatter()`
3. **Parsing** — `parse_roadmap_frontmatter()`, `parse_roadmap()`
4. **Serialization** — `serialize_steps_to_frontmatter()`, `serialize_phases()`
5. **Utilities** — `group_steps_by_phase()`, `find_next_step()`, `compute_summary()`
6. **Markers** — `wrap_roadmap_tables_with_markers()`, `extract_roadmap_table_section()`

## Parsing Strategy

Frontmatter-first: tries YAML within `objective-roadmap` block, falls back to table parsing for v1 compatibility. This enables richer metadata (separate `plan` and `pr` fields) while maintaining backward compatibility.

## Phase Grouping

Derives phases from step ID prefixes (e.g., "1.1" → phase 1, "2A.1" → phase 2A). Phase names are enriched from markdown headers via `_enrich_phase_names()` — see [phase-name-enrichment.md](phase-name-enrichment.md).

## Related

- [roadmap-table-markers.md](roadmap-table-markers.md) — Marker system details
- [circular-dependency-resolution.md](circular-dependency-resolution.md) — Why module lives in erk_shared
- [Roadmap Parser API](../objectives/roadmap-parser-api.md) — Consumer-facing API documentation
