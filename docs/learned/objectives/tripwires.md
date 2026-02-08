---
title: Objectives Tripwires
read_when:
  - "working on objectives code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from objectives/*.md frontmatter -->

# Objectives Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before accessing step_id on a RoadmapStep** → Read [Roadmap Shared Parser Architecture](roadmap-parser-api.md) first. The field is named 'id', not 'step_id'. This is a common mistake — check the actual dataclass definition.

**CRITICAL: Before adding a new validation check** → Read [Roadmap Validation Architecture](roadmap-validation.md) first. Structural checks go in parse_roadmap() and return warnings alongside data. Semantic checks go in validate_objective() and produce pass/fail results. Don't mix levels.

**CRITICAL: Before adding columns to the roadmap table format** → Read [Roadmap Format Versioning](roadmap-format-versioning.md) first. The 7-column extension was planned but never implemented. Read this doc to understand the migration strategy before adding columns.

**CRITICAL: Before adding step_type, issue, or depends_on fields to RoadmapStep** → Read [Roadmap Format Versioning](roadmap-format-versioning.md) first. These fields were planned but never built. The parser, serializer, and all callers would need coordinated changes.

**CRITICAL: Before adding structural validation to check_cmd.py** → Read [Objective Check Command — Semantic Validation](objective-roadmap-check.md) first. Structural validation (phase headers, table format) belongs in objective_roadmap_shared.py. check_cmd.py handles semantic validation only.

**CRITICAL: Before creating a learned doc that rephrases an objective's action comment lessons** → Read [Documentation Capture from Objective Work](research-documentation-integration.md) first. Objectives already capture lessons in action comments. Only create a learned doc when the insight is reusable beyond this specific objective.

**CRITICAL: Before creating a new roadmap data type without using frozen dataclass** → Read [Roadmap Shared Parser Architecture](roadmap-parser-api.md) first. RoadmapStep and RoadmapPhase are frozen dataclasses. New roadmap types must follow this pattern.

**CRITICAL: Before creating documentation for a pattern discovered during an objective before the pattern is proven in a merged PR** → Read [Documentation Capture from Objective Work](research-documentation-integration.md) first. Only document patterns proven in practice. Speculative patterns from in-progress objectives go stale. Wait until the PR lands and the pattern is validated.

**CRITICAL: Before creating or modifying roadmap step IDs** → Read [Roadmap Parser](roadmap-parser.md) first. Step IDs should use plain numbers (1.1, 2.1), not letter format (1A.1, 1B.1).

**CRITICAL: Before directly mutating issue body markdown without using either command** → Read [Roadmap Mutation Patterns](roadmap-mutation-patterns.md) first. Direct body mutation skips status computation. The surgical command writes computed status atomically; bypassing it leaves status stale. See roadmap-mutation-semantics.md.

**CRITICAL: Before expecting status to auto-update when PR column is edited manually** → Read [Roadmap Status System](roadmap-status-system.md) first. Only the update-roadmap-step command writes computed status. Manual PR edits leave status unchanged — set status to '-' to re-enable inference.

**CRITICAL: Before implementing roadmap parsing functionality** → Read [Roadmap Parser](roadmap-parser.md) first. The parser is regex-based, not LLM-based. Do not reference LLM inference.

**CRITICAL: Before importing parse_roadmap into a new consumer** → Read [Roadmap Shared Parser Architecture](roadmap-parser-api.md) first. The shared module lives in exec/scripts/ for historical reasons but is consumed by both exec scripts and CLI commands. If adding a third consumer, consider whether the module should move to a shared location.

**CRITICAL: Before inferring status from PR column when explicit status is set** → Read [Roadmap Status System](roadmap-status-system.md) first. Explicit status values (done, in-progress, pending, blocked, skipped) always take priority over PR-based inference. Only '-' or empty values trigger PR-based inference.

**CRITICAL: Before manually parsing objective roadmap markdown** → Read [Objective Check Command — Semantic Validation](objective-roadmap-check.md) first. Use `erk objective check`. It handles structural parsing, status inference, and semantic validation.

**CRITICAL: Before modifying roadmap validation without understanding the two-level architecture** → Read [Roadmap Validation Architecture](roadmap-validation.md) first. Validation is split between parse_roadmap() (structural) and validate_objective() (semantic). Read this doc to understand which level your change belongs in.

**CRITICAL: Before raising exceptions from validate_objective()** → Read [Objective Check Command — Semantic Validation](objective-roadmap-check.md) first. validate_objective() returns discriminated unions, never raises. Only CLI presentation functions (\_output_json, \_output_human) raise SystemExit.

**CRITICAL: Before treating status as a single-source value** → Read [Roadmap Status System](roadmap-status-system.md) first. Status resolution uses a two-tier system: explicit values first, then PR-based inference. Always check both the Status and PR columns.

**CRITICAL: Before using full-body update for single-cell changes** → Read [Roadmap Mutation Patterns](roadmap-mutation-patterns.md) first. Full-body updates replace the entire table. For single-cell PR updates, use surgical update (update-roadmap-step) to preserve other cells and avoid race conditions.

**CRITICAL: Before using surgical update for complete table rewrites** → Read [Roadmap Mutation Patterns](roadmap-mutation-patterns.md) first. Surgical updates only change one cell. For rewriting roadmaps after landing PRs (status + layout changes), use full-body update (objective-update-with-landed-pr).
