---
title: Roadmap Format Versioning
read_when:
  - extending the roadmap table format with new columns
  - planning backward-compatible parser changes to roadmap tables
  - understanding the 4-col to 5-col migration
tripwires:
  - action: "adding columns to the roadmap table format"
    warning: "The 4→5 column migration is the established pattern. Read this doc to understand the header-based detection and auto-upgrade strategy before adding columns."
  - action: "adding step_type, issue, or depends_on fields to RoadmapStep"
    warning: "These fields were planned but never built. The parser, serializer, and all callers would need coordinated changes."
---

# Roadmap Format Versioning

This document captures the design thinking around extending the roadmap table format, including the completed 4→5 column migration and historical context.

## Current State: 5-Column Format (Canonical)

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, RoadmapStep -->

The `RoadmapStep` dataclass has five fields (`id`, `description`, `status`, `plan`, `pr`). The `plan` and `pr` fields are separate: `plan` holds a plan issue reference (`"#6464"`), while `pr` holds a landed PR reference (`"#123"`). Both are `str | None`.

The canonical table format:

```markdown
| Step | Description | Status      | Plan  | PR   |
| ---- | ----------- | ----------- | ----- | ---- |
| 1.1  | Add auth    | done        | -     | #123 |
| 1.2  | Add tests   | in-progress | #6464 | -    |
```

## Legacy 4-Column Format (Historical)

The old 4-column format where plan and PR shared a single column is no longer actively parsed by `parse_roadmap()`. The parser now requires v2 YAML frontmatter and returns a legacy format error for non-v2 content.

```markdown
| Step | Description | Status | PR         |
| ---- | ----------- | ------ | ---------- |
| 1.1  | Add auth    | done   | #123       |
| 1.2  | Add tests   | -      | plan #6464 |
```

The surgical update command (`_replace_step_refs_in_body()`) still handles both 4-column and 5-column table formats in the rendered markdown table (objective-body comment), but the source of truth is always YAML frontmatter.

## Migration Strategy: Header-Based Detection

The surgical update command uses **header-based format detection** — it checks for the 5-column header first, then falls back to 4-column. This keeps format detection co-located with the data itself (no version metadata needed in the table).

Key design choices:

- **5-col header canonical**: `| Step | Description | Status | Plan | PR |`
- **4-col handled on write**: When editing a 4-col table in the rendered view, the table is auto-upgraded to 5-col
- **Frontmatter schema v2**: The YAML frontmatter uses `schema_version: "2"` with separate `plan` and `pr` fields
- **v2-only parsing**: `parse_roadmap()` returns a legacy format error for non-v2 content (no table-parsing fallback)

## Historical: Planned 7-Column Extension (Never Built)

The original plan added three more columns: **Type** (task/milestone/research), **Issue** (GitHub issue reference), and **Depends On** (step ID dependencies). This was never implemented. If revisited, follow the same header-based detection pattern established by the 4→5 migration.

## Status Inference: Write-Time Only

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, update_step_in_frontmatter -->

Status inference exists only at **write time** in `update_step_in_frontmatter()`: when no explicit status is provided, it infers `done` from a PR reference, `in_progress` from a plan reference, or preserves the existing status. The parser (`parse_roadmap()`) reads the explicit `status` field from YAML frontmatter with no inference — what's stored is what's returned.

## Related Documentation

- [roadmap-parser-api.md](roadmap-parser-api.md) — Data types and function reference
- [roadmap-validation.md](roadmap-validation.md) — Validation rules for roadmap content
