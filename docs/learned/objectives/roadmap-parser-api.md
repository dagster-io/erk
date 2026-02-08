---
title: Roadmap Shared Parser Architecture
read_when:
  - "adding a new consumer of objective_roadmap_shared.py"
  - "extending the roadmap data model with new fields"
  - "understanding why the shared parser exists separately from its consumers"
tripwires:
  - action: "creating a new roadmap data type without using frozen dataclass"
    warning: "RoadmapStep and RoadmapPhase are frozen dataclasses. New roadmap types must follow this pattern."
  - action: "accessing step_id on a RoadmapStep"
    warning: "The field is named 'id', not 'step_id'. This is a common mistake — check the actual dataclass definition."
  - action: "importing parse_roadmap into a new consumer"
    warning: "The shared module lives in exec/scripts/ for historical reasons but is consumed by both exec scripts and CLI commands. If adding a third consumer, consider whether the module should move to a shared location."
last_audited: "2026-02-08 10:24 PT"
audit_result: edited
---

# Roadmap Shared Parser Architecture

The roadmap parser is a shared module consumed by two commands with fundamentally different usage patterns. This document explains **why** the shared module exists, how its consumers differ, and the non-obvious design choices in the data model.

## Why a Shared Module?

<!-- Source: src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py -->

The `objective_roadmap_shared.py` module exists because two commands need the same parsing logic but use different subsets of it. Both `check_cmd.py` (erk objective check) and `update_roadmap_step.py` consume the shared parser, but differ in scope: `check_cmd` uses all 4 functions and both data types for full validation workflow, while `update_roadmap_step` only imports `parse_roadmap` for validation before surgical regex edits.

<!-- Source: src/erk/cli/commands/objective/check_cmd.py, validate_objective -->
<!-- Source: src/erk/cli/commands/exec/scripts/update_roadmap_step.py, _replace_step_pr_in_body -->

The key insight: `update_roadmap_step` calls `parse_roadmap` for **validation**, not for mutation. It confirms the target step ID exists in the parsed output, then performs a separate regex replacement on the raw markdown. The parsed data is thrown away. This means the parser's job is to be a source of truth about table structure, not a round-trip serializer.

## Non-Obvious Data Model Choices

### Field naming: `id` not `step_id`

The `RoadmapStep.id` field is named `id`, not `step_id`. Every consumer accesses `step.id` (e.g., `step.id` in check_cmd's consistency checks). This catches people who expect the field name to mirror the table column header "Step".

### Phase suffix for sub-phases

`RoadmapPhase` has a `suffix` field (empty string or a letter like `"A"`, `"B"`) to support sub-phase numbering (`Phase 1A`, `Phase 1B`). This is used by `check_cmd.py` for sequential ordering validation — phases are sorted by `(number, suffix)` tuple comparison, which gives correct ordering for both `1, 2, 3` and `1A, 1B, 2` patterns.

### Parser returns warnings, not errors

`parse_roadmap` returns `(phases, validation_errors)` where validation_errors are warning strings, not exceptions. The parser extracts whatever it can and reports problems alongside results. This matters because a partially-parsed roadmap is more useful than a crashed parse — `check_cmd` displays both the parsed phases and the warnings.

## Module Location Anomaly

The shared module lives in `src/erk/cli/commands/exec/scripts/` — the exec scripts directory — even though `check_cmd.py` in `src/erk/cli/commands/objective/` imports from it. This is a historical artifact: the parser was originally created for exec scripts and gained a second consumer later. The cross-package import works but is architecturally unusual. If a third consumer appears, consider promoting the module to a more neutral location.

## Relationship to Sibling Docs

This document covers the **structural architecture** of the shared parser. For specific behavioral rules:

- **Status inference logic** → [Roadmap Status System](roadmap-status-system.md)
- **Mutation-time vs parse-time semantics** → [Roadmap Mutation Semantics](../architecture/roadmap-mutation-semantics.md)
- **Surgical vs full-body update decisions** → [Roadmap Mutation Patterns](roadmap-mutation-patterns.md)
- **CLI usage and parsing rules** → [Roadmap Parser](roadmap-parser.md)
