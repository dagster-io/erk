---
title: Objectives Tripwires
read_when:
  - "working on objectives code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from objectives/*.md frontmatter -->

# Objectives Tripwires

Rules triggered by matching actions in code.

**accessing node_id on a RoadmapNode** → Read [Roadmap Shared Parser Architecture](roadmap-parser-api.md) first. The field is named 'id', not 'node_id'. This is a common mistake — check the actual dataclass definition.

**adding a new roadmap mutation site without updating this document** → Read [Objective Lifecycle](objective-lifecycle.md) first. All roadmap mutation sites must be documented in objective-lifecycle.md

**adding a new validation check** → Read [Roadmap Validation Architecture](roadmap-validation.md) first. Structural checks go in parse_roadmap() and return warnings alongside data. Semantic checks go in validate_objective() and produce pass/fail results. Don't mix levels.

**adding columns to the roadmap table format** → Read [Roadmap Format Versioning](roadmap-format-versioning.md) first. The 4→5 column migration is the established pattern. Read this doc to understand the header-based detection and auto-upgrade strategy before adding columns.

**adding step_type, issue, or depends_on fields to RoadmapNode** → Read [Roadmap Format Versioning](roadmap-format-versioning.md) first. These fields were planned but never built. The parser, serializer, and all callers would need coordinated changes.

**adding structural validation to check_cmd.py** → Read [Objective Check Command — Semantic Validation](objective-roadmap-check.md) first. Structural validation (phase headers, table format) belongs in roadmap.py (packages/erk-shared). check_cmd.py handles semantic validation only.

**assuming phase names are stored in YAML frontmatter** → Read [Phase Name Enrichment](phase-name-enrichment.md) first. Phase names come from markdown headers, not frontmatter. Read this doc.

**calling update-objective-node with --pr but without --plan** → Read [Plan Reference Preservation in Roadmap Updates](plan-reference-preservation.md) first. CLI validation requires --plan when --pr is set. Omitting --plan would silently lose the plan reference. Use --plan '#NNN' to preserve or --plan '' to explicitly clear.

**changing update_node_in_frontmatter() semantics for plan=None** → Read [Plan Reference Preservation in Roadmap Updates](plan-reference-preservation.md) first. plan=None means 'preserve existing value', not 'clear'. This three-state pattern (None=preserve, ''=clear, '#NNN'=set) is used by both CLI and gateway. Changing it breaks preservation.

**creating a learned doc that rephrases an objective's action comment lessons** → Read [Documentation Capture from Objective Work](research-documentation-integration.md) first. Objectives already capture lessons in action comments. Only create a learned doc when the insight is reusable beyond this specific objective.

**creating a new roadmap data type without using frozen dataclass** → Read [Roadmap Shared Parser Architecture](roadmap-parser-api.md) first. RoadmapNode and RoadmapPhase are frozen dataclasses. New roadmap types must follow this pattern.

**creating documentation for a pattern discovered during an objective before the pattern is proven in a merged PR** → Read [Documentation Capture from Objective Work](research-documentation-integration.md) first. Only document patterns proven in practice. Speculative patterns from in-progress objectives go stale. Wait until the PR lands and the pattern is validated.

**creating or modifying roadmap step IDs** → Read [Roadmap Parser](roadmap-parser.md) first. Step IDs should use plain numbers (1.1, 2.1), not letter format (1A.1, 1B.1).

**directly mutating issue body markdown without using either command** → Read [Roadmap Mutation Patterns](roadmap-mutation-patterns.md) first. Direct body mutation skips status computation. The surgical command writes computed status atomically; bypassing it leaves status stale. See roadmap-mutation-semantics.md.

**expecting status to auto-update when PR column is edited manually** → Read [Roadmap Status System](roadmap-status-system.md) first. Only the update-objective-node command writes computed status. Manual PR edits leave status unchanged — set status to '-' to re-enable inference.

**implementing roadmap parsing functionality** → Read [Roadmap Parser](roadmap-parser.md) first. The parser is regex-based, not LLM-based. Do not reference LLM inference.

**importing parse_roadmap into a new consumer** → Read [Roadmap Shared Parser Architecture](roadmap-parser-api.md) first. The shared module lives in erk_shared.gateway.github.metadata.roadmap and is consumed by both exec scripts and CLI commands. Import from this shared location.

**inferring status from PR column when explicit status is set** → Read [Roadmap Status System](roadmap-status-system.md) first. Explicit status values (done, in_progress, pending, blocked, skipped, planning) always take priority over PR-based inference. Only '-' or empty values trigger PR-based inference.

**looking for phase names in RoadmapNode fields** → Read [Phase Name Enrichment](phase-name-enrichment.md) first. Nodes are stored flat. Phase membership is derived from node ID prefix. Phase names come from markdown headers via enrich_phase_names().

**manually parsing objective roadmap markdown** → Read [Objective Check Command — Semantic Validation](objective-roadmap-check.md) first. Use `erk objective check`. It handles structural parsing, status inference, and semantic validation.

**manually writing roadmap YAML or metadata blocks in objective-create** → Read [Objective Create Workflow](objective-create-workflow.md) first. Use erk exec objective-render-roadmap to generate the roadmap block. The skill template must produce valid JSON input for this command.

**modifying roadmap validation without understanding the two-level architecture** → Read [Roadmap Validation Architecture](roadmap-validation.md) first. Validation is split between parse_roadmap() (structural) and validate_objective() (semantic). Read this doc to understand which level your change belongs in.

**raising exceptions from validate_objective()** → Read [Objective Check Command — Semantic Validation](objective-roadmap-check.md) first. validate_objective() returns discriminated unions, never raises. Only CLI presentation functions (\_output_json, \_output_human) raise SystemExit.

**storing objective content directly in the issue body** → Read [Objective v2 Storage Format](objective-storage-format.md) first. Objective content goes in the first comment (objective-body block), not the issue body. The issue body holds only metadata blocks (objective-header, objective-roadmap).

**treating status as a single-source value** → Read [Roadmap Status System](roadmap-status-system.md) first. Status resolution uses a two-tier system: explicit values first, then PR-based inference. Always check both the Status and PR columns.

**updating roadmap step in only one location (frontmatter or table)** → Read [Objective Lifecycle](objective-lifecycle.md) first. Must update both frontmatter AND markdown table during the dual-write migration period. Use update-objective-node which handles both atomically.

**using None/empty string interchangeably in update-objective-node parameters** → Read [Roadmap Mutation Patterns](roadmap-mutation-patterns.md) first. None=preserve existing value, empty string=clear the cell, value=set new value. Confusing these leads to accidental data loss or stale values.

**using find_next_node() for dependency-aware traversal** → Read [Dependency Graph Architecture](dependency-graph.md) first. Use DependencyGraph.next_node() instead. find_next_node() is position-based and ignores dependencies.

**using full-body update for single-cell changes** → Read [Roadmap Mutation Patterns](roadmap-mutation-patterns.md) first. Full-body updates replace the entire table. For single-cell PR updates, use surgical update (update-objective-node) to preserve other cells and avoid race conditions.

**using parse_roadmap() when strict v2 validation is needed** → Read [Roadmap Shared Parser Architecture](roadmap-parser-api.md) first. Use parse_v2_roadmap() for commands that should reject legacy format. parse_roadmap() returns a legacy error string; parse_v2_roadmap() returns None for non-v2 content.

**using plan-\* metadata block names for objective data** → Read [Objective v2 Storage Format](objective-storage-format.md) first. Metadata block names must match their entity type: plan-header/plan-body for plans, objective-header/objective-roadmap/objective-body for objectives.

**using surgical update for complete table rewrites** → Read [Roadmap Mutation Patterns](roadmap-mutation-patterns.md) first. Surgical updates only change one cell. For rewriting roadmaps after landing PRs (status + layout changes), use full-body update (objective-update-with-landed-pr).

**writing objective content directly to issue body** → Read [Objective Create Workflow](objective-create-workflow.md) first. Issue body holds only metadata blocks. Full content goes in the first comment (objective-body block). See the 3-layer storage model.

**writing regex patterns to match roadmap table rows without ^ and $ anchors** → Read [Roadmap Mutation Patterns](roadmap-mutation-patterns.md) first. All roadmap table row regex patterns MUST use ^...$ anchors with re.MULTILINE. Without anchors, patterns can match partial lines or span rows.
