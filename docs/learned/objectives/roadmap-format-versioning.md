---
title: Roadmap Format Versioning
read_when:
  - extending the roadmap table format with new columns
  - planning backward-compatible parser changes to roadmap tables
  - understanding roadmap column format history
tripwires:
  - action: "adding columns to the roadmap table format"
    warning: "The 4→5 column migration is the established pattern. Read this doc to understand the header-based detection and auto-upgrade strategy before adding columns."
  - action: "adding step_type, issue, or depends_on fields to RoadmapNode"
    warning: "These fields were planned but never built. The parser, serializer, and all callers would need coordinated changes."
last_audited: "2026-02-17 16:00 PT"
audit_result: clean
---

# Roadmap Format Versioning

This document captures the design thinking around the roadmap table format, including the current 4-column canonical format and historical context.

## Current State: 4-Column Format (Canonical)

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, RoadmapNode -->

The `RoadmapNode` dataclass has six fields (`id`, `description`, `status`, `pr`, `depends_on`, `slug`). The `pr` field holds a PR reference (`"#123"`) for both in-progress and landed PRs and is `str | None`. The `depends_on` field holds explicit dependencies (`tuple[str, ...] | None`), and `slug` holds a kebab-case identifier (`str | None`).

The canonical table format:

```markdown
| Node | Description | Status      | PR   |
| ---- | ----------- | ----------- | ---- |
| 1.1  | Add auth    | done        | #123 |
| 1.2  | Add tests   | in-progress | -    |
```

## Legacy Format (Historical)

The old format where plan and PR shared a single column is no longer actively parsed by `parse_roadmap()`. The parser now requires v2+ YAML frontmatter and returns a legacy format error for non-v2 content.

```markdown
| Node | Description | Status | PR         |
| ---- | ----------- | ------ | ---------- |
| 1.1  | Add auth    | done   | #123       |
| 1.2  | Add tests   | -      | plan #6464 |
```

The surgical update command uses two functions: `update_node_in_frontmatter()` updates the YAML frontmatter (source of truth), while `rerender_comment_roadmap()` updates the rendered markdown table in the objective-body comment.

## Migration Strategy: Header-Based Detection

The surgical update command uses **header-based format detection** — it checks for the 4-column header (or 5-column with Depends On). This keeps format detection co-located with the data itself (no version metadata needed in the table).

Key design choices:

- **4-col header canonical**: `| Node | Description | Status | PR |`
- **5-col conditional**: When nodes have `depends_on`, the header becomes `| Node | Description | Depends On | Status | PR |`
- **Frontmatter schema v4**: The YAML frontmatter uses `schema_version: "4"` with the `nodes` key (v2 used `steps`). The parser accepts v2, v3, and v4; the renderer always emits v4.
- **v2/v3/v4 parsing**: `parse_roadmap()` accepts all three schema versions. Returns a legacy format error for non-v2/v3/v4 content (no table-parsing fallback)

## Historical: Planned 7-Column Extension (Never Built)

The original plan added three more columns: **Type** (task/milestone/research), **Issue** (GitHub issue reference), and **Depends On** (step ID dependencies). This was never implemented. If revisited, follow the same header-based detection pattern established by the 4→5 migration.

## Status Inference: Write-Time Only

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, update_node_in_frontmatter -->

Status inference exists only at **write time** in `update_node_in_frontmatter()`: when no explicit status is provided, it infers `in_progress` from a PR reference or preserves the existing status. The parser (`parse_roadmap()`) reads the explicit `status` field from YAML frontmatter with no inference — what's stored is what's returned.

## Related Documentation

- [roadmap-parser-api.md](roadmap-parser-api.md) — Data types and function reference
- [roadmap-validation.md](roadmap-validation.md) — Validation rules for roadmap content
