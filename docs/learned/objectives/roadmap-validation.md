---
title: Roadmap Validation Architecture
read_when:
  - "debugging roadmap validation errors or check failures"
  - "adding new validation rules to objective check or update commands"
  - "understanding why validation is split across parser and check command"
tripwires:
  - action: "modifying roadmap validation without understanding the two-level architecture"
    warning: "Validation is split between parse_roadmap() (structural) and validate_objective() (semantic). Read this doc to understand which level your change belongs in."
  - action: "adding a new validation check"
    warning: "Structural checks go in parse_roadmap() and return warnings alongside data. Semantic checks go in validate_objective() and produce pass/fail results. Don't mix levels."
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
---

# Roadmap Validation Architecture

## Why Two Levels?

Roadmap validation is deliberately split across two layers because they serve different purposes and have different failure modes:

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, parse_roadmap -->

**Structural validation** (in `parse_roadmap()`) answers: "Can we extract data from this markdown?" It runs during every roadmap operation — parsing, updating, checking — and returns warnings alongside whatever data it could extract. Parsing is lenient: it continues past malformed phases and collects errors rather than aborting.

<!-- Source: check_cmd.py, validate_objective -->

**Semantic validation** (in `validate_objective()`) answers: "Is this roadmap internally consistent?" It only runs during `erk objective check` and produces pass/fail check results. It depends on structural parsing succeeding first — if no phases parse, semantic checks are skipped and the command returns early.

This separation matters because the update command needs structural parsing but not semantic validation. A step PR update shouldn't fail because phase numbering is out of order in an unrelated phase.

## Structural vs Semantic: Decision Table

| Question                                | Level                | Why                                                 |
| --------------------------------------- | -------------------- | --------------------------------------------------- |
| Can we find phase headers?              | Structural           | Without phases, no data can be extracted            |
| Does the table have the right columns?  | Structural           | Column structure determines if rows can be parsed   |
| Are step IDs in preferred format?       | Structural (warning) | Doesn't block parsing, just flags for humans        |
| Does a "done" step have a PR reference? | Semantic             | Requires cross-field reasoning about data integrity |
| Are status and PR columns consistent?   | Semantic             | Requires understanding the status inference rules   |
| Is phase numbering sequential?          | Semantic             | Requires comparing across phases                    |

## The Consistency Invariants

The semantic checks in `validate_objective()` enforce invariants that connect the status system to the PR column:

1. **References imply status**: A step with PR `#NNN` should resolve to `done`; a step with plan `#NNN` should resolve to `in_progress`. If explicit status contradicts the plan/PR columns, the check fails.

2. **Status implies PR**: A step with status `done` must have a PR reference. "Done" without evidence of what was done is an orphaned status.

3. **Phase ordering**: Phases must be sequentially numbered. This catches copy-paste errors in roadmap editing (e.g., two `Phase 2` sections).

These invariants interact with the status inference system documented in [Roadmap Status System](roadmap-status-system.md). The update command avoids violating invariant #1 by resetting the status cell to `-` when changing the PR cell, letting inference derive the correct status.

<!-- Source: update_roadmap_step.py, _replace_step_refs_in_body -->

See `_replace_step_refs_in_body()` in `update_roadmap_step.py` for the status-reset-on-update logic.

## Anti-Patterns

**Adding semantic validation to `parse_roadmap()`** — WRONG. The parser should extract data and report structural warnings, not enforce business rules. Semantic checks in the parser would block the update command from operating on partially-valid roadmaps.

**Skipping re-inference after PR cell updates** — WRONG. The update command writes a computed display status for human readability, but the parser will re-infer status on next read. If these diverge, the check command catches it. This is why the update command resets status to `-` rather than trying to set an explicit status value.

**Treating parser warnings as errors** — WRONG. The parser returns `(phases, warnings)` as a tuple. Warnings don't prevent data extraction. Callers that abort on warnings (instead of just the empty-phases case) are unnecessarily strict.

## Error Handling Pattern

Both validation layers use a cascading LBYL pattern: each check gates the next, so later checks can assume earlier preconditions hold. The check command checks issue existence → label → roadmap parsability → consistency rules, returning early at each failure point. The update command follows the same cascade: issue exists → roadmap parses → step found → replacement succeeds.

This is why `validate_objective()` returns `ObjectiveValidationError` (couldn't even start) vs `ObjectiveValidationSuccess` (ran checks, some may have failed) — the discriminated union separates "validation couldn't run" from "validation ran and found problems."

## Implementation Reference

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, parse_roadmap -->

- Structural validation: `parse_roadmap()` in `erk_shared.gateway.github.metadata.roadmap`

<!-- Source: check_cmd.py, validate_objective -->

- Semantic validation: `validate_objective()` in `check_cmd.py`

<!-- Source: update_roadmap_step.py, update_roadmap_step -->

- Update-time validation: `update_roadmap_step()` in `update_roadmap_step.py`

## Related Documentation

- [Roadmap Parser](roadmap-parser.md) — Parser usage, status inference, and command reference
- [Roadmap Status System](roadmap-status-system.md) — Two-tier status resolution specification
- [Roadmap Mutation Patterns](roadmap-mutation-patterns.md) — Why updates reset status to `-`
