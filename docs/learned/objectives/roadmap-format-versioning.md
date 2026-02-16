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

## Legacy 4-Column Format (Backward Compatible)

The parser still handles the old 4-column format where plan and PR shared a single column:

```markdown
| Step | Description | Status | PR         |
| ---- | ----------- | ------ | ---------- |
| 1.1  | Add auth    | done   | #123       |
| 1.2  | Add tests   | -      | plan #6464 |
```

During parsing, 4-column `plan #NNN` values are automatically migrated to the `plan` field. The surgical update command (`_replace_step_refs_in_body()`) auto-upgrades 4-column table headers to 5-column on write.

## Migration Strategy: Header-Based Detection

The parser uses **header-based format detection** — it checks for the 5-column header first, then falls back to 4-column. This keeps format detection co-located with the data itself (no version metadata needed in the table).

Key design choices:

- **5-col header tried first**: `| Step | Description | Status | Plan | PR |`
- **4-col fallback**: `| Step | Description | Status | PR |`
- **Auto-upgrade on write**: When `_replace_step_refs_in_body()` edits a 4-col table, it upgrades the header to 5-col
- **Frontmatter schema v2**: The YAML frontmatter uses `schema_version: "2"` with separate `plan` and `pr` fields. v1 frontmatter with `pr: "plan #NNN"` is auto-migrated during parsing

## Historical: Planned 7-Column Extension (Never Built)

The original plan added three more columns: **Type** (task/milestone/research), **Issue** (GitHub issue reference), and **Depends On** (step ID dependencies). This was never implemented. If revisited, follow the same header-based detection pattern established by the 4→5 migration.

## Status Inference: A Design Quirk Worth Preserving

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, parse_roadmap -->

The parser has a dual-path status resolution: explicit status values in the Status column take priority, but if the Status column contains `-` (legacy format), status is inferred from the plan/PR columns (`#NNN` in PR = done, `#NNN` in Plan = in_progress, both empty = pending). This backward compatibility exists because early roadmaps used `-` in the Status column and relied entirely on column-based inference. Any format extension must preserve this fallback to avoid breaking existing objectives.

## Related Documentation

- [roadmap-parser-api.md](roadmap-parser-api.md) — Data types and function reference
- [roadmap-validation.md](roadmap-validation.md) — Validation rules for roadmap content
