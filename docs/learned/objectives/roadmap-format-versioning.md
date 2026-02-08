---
title: Roadmap Format Versioning
read_when:
  - extending the roadmap table format with new columns
  - planning backward-compatible parser changes to roadmap tables
  - understanding why the roadmap uses a simple 4-column format
tripwires:
  - action: "adding columns to the roadmap table format"
    warning: "The 7-column extension was planned but never implemented. Read this doc to understand the migration strategy before adding columns."
  - action: "adding step_type, issue, or depends_on fields to RoadmapStep"
    warning: "These fields were planned but never built. The parser, serializer, and all callers would need coordinated changes."
---

# Roadmap Format Versioning

This document captures the design thinking around extending the roadmap table format and why the current 4-column format has persisted unchanged.

## Current State: 4-Column Format Only

<!-- Source: src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py, RoadmapStep -->

The `RoadmapStep` dataclass has exactly four fields (`id`, `description`, `status`, `pr`). The parser in `parse_roadmap()` only handles 4-column tables. Despite earlier planning for a 7-column extension (adding Type, Issue, Depends On), **this extension was never implemented** — no code for 7-column parsing, no additional fields on the dataclass, no dual-format detection.

The current table format (this is a data format example, permitted under the One Code Rule):

```markdown
| Step | Description | Status | PR |
|------|-------------|--------|----|
| 1.1  | Add auth    | done   | #123 |
```

## Planned 7-Column Extension (Never Built)

The original plan added three columns: **Type** (task/milestone/research), **Issue** (GitHub issue reference), and **Depends On** (step ID dependencies). The migration strategy was:

- **Header-based format detection**: The parser would check the table header to decide which format to parse — no version metadata or config needed. This keeps format detection co-located with the data itself.
- **Defaults for missing columns**: When parsing 4-column tables into a 7-column data structure, missing fields would get defaults (`step_type="task"`, `issue=None`, `depends_on=None`).
- **Per-phase format mixing**: Different phases within the same objective could use different column counts, enabling gradual migration.
- **Smart serialization**: Output 4-column format unless any step has non-default extended values, minimizing unnecessary format changes.

## Why This Matters for Future Extension

If the 7-column format (or any format extension) is revisited, these are the cross-cutting touchpoints:

| Component | What changes | Why |
|-----------|-------------|-----|
| `RoadmapStep` dataclass | New fields needed | All consumers type-check against this |
| `parse_roadmap()` | Header detection + row parsing | Must handle both old and new formats |
| `_replace_step_pr_in_body()` | Regex for row matching | Currently assumes exactly 4 pipe-delimited cells |
| `serialize_phases()` | Output format selection | Must decide when to emit extended columns |
| `objective check` validation | New semantic checks | e.g., dependency cycle detection, valid step_type values |
| Objective issue templates | Updated table headers | New objectives should use the extended format |

<!-- Source: src/erk/cli/commands/exec/scripts/update_roadmap_step.py, _replace_step_pr_in_body -->

The regex-based row replacement in `_replace_step_pr_in_body()` is particularly fragile to column count changes — it hard-codes a 4-cell pattern match. Any format extension must update this regex or replace it with a more flexible approach.

## Status Inference: A Design Quirk Worth Preserving

<!-- Source: src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py, parse_roadmap -->

The parser has a dual-path status resolution: explicit status values in the Status column take priority, but if the Status column contains `-` (legacy format), status is inferred from the PR column (`#NNN` = done, `plan #NNN` = in_progress, empty = pending). This backward compatibility exists because early roadmaps used `-` in the Status column and relied entirely on PR-based inference. Any format extension must preserve this fallback to avoid breaking existing objectives.

## Related Documentation

- [roadmap-parser-api.md](roadmap-parser-api.md) — Data types and function reference
- [roadmap-validation.md](roadmap-validation.md) — Validation rules for roadmap content
