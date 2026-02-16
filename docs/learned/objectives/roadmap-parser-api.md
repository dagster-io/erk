---
title: Roadmap Shared Parser Architecture
read_when:
  - "adding a new consumer of roadmap.py in erk_shared"
  - "extending the roadmap data model with new fields"
  - "understanding why the shared parser exists separately from its consumers"
tripwires:
  - action: "creating a new roadmap data type without using frozen dataclass"
    warning: "RoadmapStep and RoadmapPhase are frozen dataclasses. New roadmap types must follow this pattern."
  - action: "accessing step_id on a RoadmapStep"
    warning: "The field is named 'id', not 'step_id'. This is a common mistake — check the actual dataclass definition."
  - action: "importing parse_roadmap into a new consumer"
    warning: "The shared module lives in erk_shared.gateway.github.metadata.roadmap and is consumed by both exec scripts and CLI commands. Import from this shared location."
  - action: "using parse_roadmap() when strict v2 validation is needed"
    warning: "Use parse_v2_roadmap() for commands that should reject legacy format. parse_roadmap() returns a legacy error string; parse_v2_roadmap() returns None for non-v2 content."
last_audited: "2026-02-08 10:24 PT"
audit_result: edited
---

# Roadmap Shared Parser Architecture

The roadmap parser is a shared module consumed by two commands with fundamentally different usage patterns. This document explains **why** the shared module exists, how its consumers differ, and the non-obvious design choices in the data model.

## Why a Shared Module?

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py -->

The `roadmap.py` module in `erk_shared.gateway.github.metadata` exists because two commands need the same parsing logic but use different subsets of it. Both `check_cmd.py` (erk objective check) and `update_roadmap_step.py` consume the shared parser, but differ in scope: `check_cmd` uses all 4 functions and both data types for full validation workflow, while `update_roadmap_step` only imports `parse_roadmap` for validation before surgical regex edits.

<!-- Source: src/erk/cli/commands/objective/check_cmd.py, validate_objective -->
<!-- Source: src/erk/cli/commands/exec/scripts/update_roadmap_step.py, _replace_step_refs_in_body -->

The key insight: `update_roadmap_step` calls `parse_roadmap` for **validation**, not for mutation. It confirms the target step ID exists in the parsed output, then performs a separate regex replacement on the raw markdown. The parsed data is thrown away. This means the parser's job is to be a source of truth about table structure, not a round-trip serializer.

## Non-Obvious Data Model Choices

### Field naming: `id` not `step_id`

The `RoadmapStep.id` field is named `id`, not `step_id`. Every consumer accesses `step.id` (e.g., `step.id` in check_cmd's consistency checks). This catches people who expect the field name to mirror the table column header "Step".

### Phase suffix for sub-phases

`RoadmapPhase` has a `suffix` field (empty string or a letter like `"A"`, `"B"`) to support sub-phase numbering (`Phase 1A`, `Phase 1B`). This is used by `check_cmd.py` for sequential ordering validation — phases are sorted by `(number, suffix)` tuple comparison, which gives correct ordering for both `1, 2, 3` and `1A, 1B, 2` patterns.

### Parser returns warnings, not errors

`parse_roadmap` returns `(phases, validation_errors)` where validation_errors are warning strings, not exceptions. The parser extracts whatever it can and reports problems alongside results. This matters because a partially-parsed roadmap is more useful than a crashed parse — `check_cmd` displays both the parsed phases and the warnings.

## Module Location History

The shared module now lives in `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`. It was originally located in `src/erk/cli/commands/exec/scripts/` when created for exec scripts, then moved to the shared package as it gained multiple consumers across both exec scripts and CLI commands.

## Undocumented Helpers

### `extract_raw_metadata_blocks()` (from core.py)

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py, extract_raw_metadata_blocks -->

Extracts all metadata blocks from text using HTML comment markers. Returns `list[RawMetadataBlock]` where each block has `.key` (str) and `.body` (raw string content). Used by `parse_roadmap()` to locate the `objective-roadmap` block before passing its body to frontmatter parsing.

### `replace_metadata_block_in_body()` (from core.py)

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py, replace_metadata_block_in_body -->

```python
def replace_metadata_block_in_body(body: str, key: str, new_block_content: str) -> str
```

Replaces an entire metadata block's content in the body. Finds the block by key and substitutes the content between the HTML comment markers. Used during roadmap mutations to replace the frontmatter block after updating step data.

### `_enrich_phase_names()` (from roadmap.py)

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, _enrich_phase_names -->

```python
def _enrich_phase_names(body: str, phases: list[RoadmapPhase]) -> list[RoadmapPhase]
```

Extracts phase names from markdown headers (e.g., `### Phase 1: Planning`) and replaces placeholder names in parsed `RoadmapPhase` objects. Called by `parse_roadmap()` after frontmatter parsing because frontmatter stores flat steps without phase names. Uses regex pattern `^###\s+Phase\s+(\d+)([A-Z]?):\s*(.+?)` to match headers.

### Separate plan and pr fields on RoadmapStep

`RoadmapStep` has separate `plan` and `pr` fields (both `str | None`). The `plan` field holds a plan issue reference (e.g., `"#6464"`), while `pr` holds a landed PR reference (e.g., `"#123"`). This replaces the old convention where `pr` held both formats (`"plan #456"` vs `"#123"`). The parser reads these as separate YAML fields from v2 frontmatter — no table-based migration occurs during parsing.

## Dual-Parser Pattern

The module exposes two parsing entry points:

### `parse_roadmap(body)` — Lenient Parser

Returns `(phases, validation_errors)`. Always returns a tuple. For v2 YAML frontmatter, parses and returns phases. For non-v2 content, returns `([], [legacy_format_error])`. This is the standard parser used by most consumers.

### `parse_v2_roadmap(body)` — Strict v2 Parser

Returns `(phases, validation_errors) | None`. Returns `None` when the body is not in v2 format (no metadata block, no `<details>` wrapper, or non-v2 schema version). Use this when the caller needs to distinguish "not v2 format" from "v2 format with errors" — for example, commands that should reject legacy format explicitly rather than receiving an error string.

## Relationship to Sibling Docs

This document covers the **structural architecture** of the shared parser. For specific behavioral rules:

- **Status inference logic** → [Roadmap Status System](roadmap-status-system.md)
- **Mutation-time vs parse-time semantics** → [Roadmap Mutation Semantics](../architecture/roadmap-mutation-semantics.md)
- **Surgical vs full-body update decisions** → [Roadmap Mutation Patterns](roadmap-mutation-patterns.md)
- **CLI usage and parsing rules** → [Roadmap Parser](roadmap-parser.md)
