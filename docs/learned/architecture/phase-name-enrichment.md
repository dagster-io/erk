---
title: Phase Name Enrichment Pattern
read_when:
  - "debugging missing phase names in roadmap output"
  - "adding new metadata extraction from markdown headers"
  - "understanding why phase names aren't in frontmatter"
last_audited: "2026-02-15 17:17 PT"
---

# Phase Name Enrichment

## Problem

Frontmatter stores steps with IDs like "1.1", "2A.3" but not phase names. Phase names exist only in markdown headers (e.g., `### Phase 1: Planning`). After `group_steps_by_phase()` creates phase objects from step ID prefixes, the phase `name` field is empty.

## Solution

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, _enrich_phase_names -->

`_enrich_phase_names()` extracts names from phase headers in the markdown body and enriches phase objects using `dataclasses.replace()`.

## Algorithm

1. Regex matches phase headers in markdown body
2. Builds map of `(phase_number, suffix)` → `name`
3. Iterates through phases, using `dataclasses.replace()` to set name field

This is called by `parse_roadmap()` after `group_steps_by_phase()` to complete the phase data.

## Why Not Store Names in Frontmatter?

Phase names are presentation metadata, not structural data. Keeping them in markdown headers means they're visible and editable in GitHub's rendered view without requiring frontmatter parsing. The enrichment step bridges the gap between human-readable headers and structured data.

## Related

- [roadmap-utilities.md](roadmap-utilities.md) — Parent module architecture
- [Roadmap Parser API](../objectives/roadmap-parser-api.md) — Full API reference
