---
title: Phase Name Enrichment
category: objectives
read_when:
  - "working with phase names in roadmap parsing"
  - "assuming phase names are stored in YAML frontmatter"
  - "understanding how group_nodes_by_phase derives phase membership"
tripwires:
  - action: "assuming phase names are stored in YAML frontmatter"
    warning: "Phase names come from markdown headers, not frontmatter. Read this doc."
  - action: "looking for phase names in RoadmapNode fields"
    warning: "Nodes are stored flat. Phase membership is derived from node ID prefix. Phase names come from markdown headers via enrich_phase_names()."
---

# Phase Name Enrichment

Phase names are NOT stored in YAML frontmatter. They are extracted from markdown headers at parse time via `_enrich_phase_names()`.

## How It Works

The YAML frontmatter stores nodes as a flat list with IDs like `"1.1"`, `"2A.1"`. Phase membership is derived from the ID prefix:

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, group_nodes_by_phase -->

### Step 1: `group_nodes_by_phase()` — Derive Phase Membership

Node IDs are parsed to extract a phase key `(number, suffix)`:

| Node ID  | Phase Key  | Phase Label |
| -------- | ---------- | ----------- |
| `"1.1"`  | `(1, "")`  | Phase 1     |
| `"1.2"`  | `(1, "")`  | Phase 1     |
| `"2A.1"` | `(2, "A")` | Phase 2A    |
| `"2A.2"` | `(2, "A")` | Phase 2A    |
| `"3.1"`  | `(3, "")`  | Phase 3     |

Nodes with no dot in their ID (e.g., `"1"`, `"A"`) default to phase `(1, "")`.

Phase names at this stage are placeholders: `"Phase 1"`, `"Phase 2A"`, etc.

### Step 2: `_enrich_phase_names()` — Extract Names from Headers

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, _enrich_phase_names -->

A regex scans the full issue body for markdown headers matching:

```
### Phase {number}{suffix}: {name}
```

Pattern: `^###\s+Phase\s+(\d+)([A-Z]?):\s*(.+?)(?:\s+\(\d+\s+PR\))?$`

The optional trailing `(\d+ PR)` group handles headers like `### Phase 1: Foundation (2 PR)` where PR counts are appended for display.

Extracted names replace the placeholder names in `RoadmapPhase` objects. If no matching header is found, the placeholder name is preserved.

## Why This Design

Frontmatter stores only machine-readable data (step IDs, statuses, PR references). Phase names are human-authored prose that belongs in the markdown body. This keeps frontmatter compact and avoids duplication — the markdown headers are the single source of truth for phase names.

## Implementation References

| Function                 | File                                                                    |
| ------------------------ | ----------------------------------------------------------------------- |
| `group_nodes_by_phase()` | `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py` |
| `_enrich_phase_names()`  | `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py` |
