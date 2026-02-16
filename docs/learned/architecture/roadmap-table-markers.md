---
title: Roadmap Table Markers
read_when:
  - "modifying roadmap table detection or replacement logic"
  - "adding marker-bounded content sections to GitHub issue bodies"
  - "debugging why roadmap table updates affect wrong content"
tripwires:
  - action: "using regex to find roadmap tables without checking for markers first"
    warning: "Use extract_roadmap_table_section() to search within markers when present. Fall back to full-text regex only when markers are absent (v1 backward compatibility)."
last_audited: "2026-02-15 17:17 PT"
---

# Roadmap Table Markers

## Problem

Regex-based table detection was fragile. Any 5-column markdown table matching the pattern could be modified, potentially corrupting unrelated content in the issue body.

## Solution

HTML comment markers bound the roadmap section:

- Start: `<!-- erk:roadmap-table -->`
- End: `<!-- /erk:roadmap-table -->`

These constants are public API in `erk_shared.gateway.github.metadata.roadmap` (`ROADMAP_TABLE_MARKER_START` and `ROADMAP_TABLE_MARKER_END`).

## Where Markers Are Added

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py, format_objective_content_comment -->

`format_objective_content_comment()` in `core.py` wraps content with markers before rendering. This uses an inline import of `wrap_roadmap_tables_with_markers` from `roadmap.py` — see [inline-import-exception.md](inline-import-exception.md) for why this is justified.

## Where Markers Are Consumed

<!-- Source: src/erk/cli/commands/exec/scripts/update_roadmap_step.py, _replace_table_in_text -->

`_replace_table_in_text()` in `update_roadmap_step.py` uses `extract_roadmap_table_section()` to search only within markers when present.

## Backward Compatibility

When markers are absent (v1 objectives created before this system), the code falls back to full-text regex search. This maintains compatibility without requiring migration of existing objectives.

## Idempotency

`wrap_roadmap_tables_with_markers()` removes existing markers before adding new ones, preventing marker duplication on repeated calls.

## Related

- [circular-dependency-resolution.md](circular-dependency-resolution.md) — Why core.py uses inline import for the marker function
- [Roadmap Mutation Patterns](../objectives/roadmap-mutation-patterns.md) — Surgical vs full-body update decisions
