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

**accessing phase names from graph operations without calling enrich_phase_names()** → Read [Phase Name Enrichment](phase-name-enrichment.md) first. Phase names come from markdown headers, not from the parser. After graph_from_phases(), call enrich_phase_names(graph, issue_body) to populate phase names. Without enrichment, phase.name is None.

**adding a new exec command without registering in the exec group** → Read [Objective Exec Command Consolidation](exec-command-consolidation.md) first. New exec scripts must be registered in the Click exec command group and follow the existing pattern: Click command with typed options, LBYL validation, structured result TypedDict.

**adding a new roadmap mutation site without updating this document** → Read [Objective Lifecycle](objective-lifecycle.md) first. All roadmap mutation sites must be documented in objective-lifecycle.md

**adding a new validation check** → Read [Roadmap Validation Architecture](roadmap-validation.md) first. Structural checks go in parse_roadmap() and return warnings alongside data. Semantic checks go in validate_objective() and produce pass/fail results. Don't mix levels.

**adding a required parameter to objective-apply-landed-update without fallback discovery** → Read [Objective Exec Command Consolidation](exec-command-consolidation.md) first. The script auto-fills missing parameters from git/plan state. New parameters should follow the same pattern: explicit flag first, then auto-discovery fallback.

**adding columns to the roadmap table format** → Read [Roadmap Format Versioning](roadmap-format-versioning.md) first. Read this doc to understand the header-based detection and rendering strategy before adding columns.

**adding structural validation to check_cmd.py** → Read [Objective Check Command — Semantic Validation](objective-roadmap-check.md) first. Structural validation (phase headers, table format) belongs in roadmap.py (packages/erk-shared). check_cmd.py handles semantic validation only.

**assuming phase names are stored in YAML frontmatter** → Read [Phase Name Enrichment](phase-name-enrichment.md) first. Phase names come from markdown headers, not frontmatter. Read this doc.

**calling update-objective-node or plan-save inside objective-plan workflow without creating roadmap-step marker first** → Read [Objective Lifecycle](objective-lifecycle.md) first. The roadmap-step marker must be created before entering plan mode. If missing, plan-save cannot call update-objective-node, and the objective roadmap table silently fails to update. Create the marker immediately after the user selects a node (step 5 of objective-plan), before gathering code context.

**checking allowed-status tuples without terminal states** → Read [Objective Check Command — Semantic Validation](objective-roadmap-check.md) first. Always include `done` and `skipped` in allowed-status checks. Omitting terminal states produces false positives for completed nodes.

**creating a learned doc that rephrases an objective's action comment lessons** → Read [Documentation Capture from Objective Work](research-documentation-integration.md) first. Objectives already capture lessons in action comments. Only create a learned doc when the insight is reusable beyond this specific objective.

**creating a new roadmap data type without using frozen dataclass** → Read [Roadmap Shared Parser Architecture](roadmap-parser-api.md) first. RoadmapNode and RoadmapPhase are frozen dataclasses. New roadmap types must follow this pattern.

**creating documentation for a pattern discovered during an objective before the pattern is proven in a merged PR** → Read [Documentation Capture from Objective Work](research-documentation-integration.md) first. Only document patterns proven in practice. Speculative patterns from in-progress objectives go stale. Wait until the PR lands and the pattern is validated.

**creating or modifying roadmap step IDs** → Read [Roadmap Parser](roadmap-parser.md) first. Step IDs should use plain numbers (1.1, 2.1), not letter format (1A.1, 1B.1).

**directly mutating issue body markdown without using either command** → Read [Roadmap Mutation Patterns](roadmap-mutation-patterns.md) first. Direct body mutation skips status computation. The surgical command writes computed status atomically; bypassing it leaves status stale. See roadmap-mutation-semantics.md.

**expecting status to auto-update when PR column is edited manually** → Read [Roadmap Status System](roadmap-status-system.md) first. Only the update-objective-node command writes computed status. Manual PR edits leave status unchanged — set status to '-' to re-enable inference.

**implementing roadmap parsing functionality** → Read [Roadmap Parser](roadmap-parser.md) first. The parser is regex-based, not LLM-based. Do not reference LLM inference.

**importing parse_roadmap into a new consumer** → Read [Roadmap Shared Parser Architecture](roadmap-parser-api.md) first. The shared module lives in erk_shared.gateway.github.metadata.roadmap and is consumed by both exec scripts and CLI commands. Import from this shared location.

**inferring done status from PR reference alone** → Read [Roadmap Status System](roadmap-status-system.md) first. Explicit status always wins. PR → infers in_progress (NOT done). No plan-based inference exists anymore.

**inferring status from PR column when explicit status is set** → Read [Roadmap Status System](roadmap-status-system.md) first. Explicit status values (done, in_progress, pending, blocked, skipped, planning) always take priority over PR-based inference. Only '-' or empty values trigger PR-based inference.

**looking for phase names in RoadmapNode fields** → Read [Phase Name Enrichment](phase-name-enrichment.md) first. Nodes are stored flat. Phase membership is derived from node ID prefix. Phase names come from markdown headers via enrich_phase_names().

**looping next_node() for fan-out dispatch** → Read [Dependency Status Resolution](dependency-status-resolution.md) first. Use pending_unblocked_nodes() for fan-out dispatch. next_node() only returns a single node.

**manually parsing objective roadmap markdown** → Read [Objective Check Command — Semantic Validation](objective-roadmap-check.md) first. Use `erk objective check`. It handles structural parsing, status inference, and semantic validation.

**manually setting objective_issue in plan header without using update_plan_header_objective_issue()** → Read [Objective-Plan Backlinks](objective-plan-backlinks.md) first. Use update_plan_header_objective_issue() to set the backlink. It handles metadata block detection and formatting.

**manually writing roadmap YAML or metadata blocks in objective-create** → Read [Objective Create Workflow](objective-create-workflow.md) first. Use erk exec objective-render-roadmap to generate the roadmap block. The skill template must produce valid JSON input for this command.

**modifying roadmap validation without understanding the two-level architecture** → Read [Roadmap Validation Architecture](roadmap-validation.md) first. Validation is split between parse_roadmap() (structural) and validate_objective() (semantic). Read this doc to understand which level your change belongs in.

**overwriting an existing objective_issue backlink with a different value** → Read [Objective-Plan Backlinks](objective-plan-backlinks.md) first. \_set_plan_backlink() refuses to overwrite existing backlinks to prevent accidental plan reuse across objectives. It warns and skips instead.

**passing None for optional discovery flags and assuming defaults** → Read [Objective Exec Command Consolidation](exec-command-consolidation.md) first. Optional discovery flags (--plan, --objective, --pr) have complex fallback chains. Test edge cases where the fallback source is unavailable (branch deleted, plan not found, PR not created).

**raising exceptions from validate_objective()** → Read [Objective Check Command — Semantic Validation](objective-roadmap-check.md) first. validate_objective() returns discriminated unions, never raises. Only CLI presentation functions (\_output_json, \_output_human) raise SystemExit.

**referencing a 'plan' field on RoadmapNode** → Read [Roadmap Format Versioning](roadmap-format-versioning.md) first. The plan field was removed (PR #8128). RoadmapNode has: id, description, status, pr, depends_on, slug. Plan references are no longer tracked in the roadmap.

**running objective-fetch-context on master without --branch** → Read [Objective Lifecycle](objective-lifecycle.md) first. Auto-discovery fails on non-plan branches. Pass `--branch` explicitly when on master.

**storing objective content directly in the issue body** → Read [Objective v2 Storage Format](objective-storage-format.md) first. Objective content goes in the first comment (objective-body block), not the issue body. The issue body holds only metadata blocks (objective-header, objective-roadmap).

**treating planning status as a terminal status for dependency satisfaction** → Read [Dependency Graph Architecture](dependency-graph.md) first. planning is NOT in \_TERMINAL_STATUSES — nodes with planning status do NOT satisfy dependencies.

**treating status as a single-source value** → Read [Roadmap Status System](roadmap-status-system.md) first. Status resolution uses a two-tier system: explicit values first, then PR-based inference. Always check both the Status and PR columns.

**updating objective from multiple concurrent plan completions** → Read [Objective Lifecycle](objective-lifecycle.md) first. When multiple nodes in an objective complete simultaneously, concurrent updates can race. Check objective state before updating to avoid overwriting recent changes.

**updating roadmap step in only one location (frontmatter or table)** → Read [Objective Lifecycle](objective-lifecycle.md) first. Must update both frontmatter AND markdown table during the dual-write migration period. Use update-objective-node which handles both atomically.

**using None/empty string interchangeably in update-objective-node parameters** → Read [Roadmap Mutation Patterns](roadmap-mutation-patterns.md) first. None=preserve existing value, empty string=clear the cell, value=set new value. Confusing these leads to accidental data loss or stale values.

**using ObjectiveValidationSuccess.graph without checking issue_body for enrichment** → Read [Dependency Graph Architecture](dependency-graph.md) first. ObjectiveValidationSuccess includes issue_body specifically for phase name enrichment. Pass result.issue_body to enrich_phase_names() when you need phase names in display contexts.

**using erk objective inspect** → Read [Objective Lifecycle](objective-lifecycle.md) first. inspect command was removed in PR #7385. Use `erk objective view` or `/local:objective-view` instead.

**using find_next_node() for dependency-aware traversal** → Read [Dependency Graph Architecture](dependency-graph.md) first. Use DependencyGraph.next_node() instead. find_next_node() is position-based and ignores dependencies.

**using full-body update for single-cell changes** → Read [Roadmap Mutation Patterns](roadmap-mutation-patterns.md) first. Full-body updates replace the entire table. For single-node PR updates, use surgical update (update-objective-node) to preserve other cells and avoid race conditions.

**using graph_from_phases() when nodes have explicit depends_on fields** → Read [Dependency Status Resolution](dependency-status-resolution.md) first. Prefer build_graph() over graph_from_phases(). build_graph() detects explicit depends_on and delegates to graph_from_nodes() when appropriate.

**using parse_roadmap() when strict v2 validation is needed** → Read [Roadmap Shared Parser Architecture](roadmap-parser-api.md) first. Use parse_v2_roadmap() for commands that should reject legacy format. parse_roadmap() returns a legacy error string; parse_v2_roadmap() returns None for non-v2 content.

**using plan-\* metadata block names for objective data** → Read [Objective v2 Storage Format](objective-storage-format.md) first. Metadata block names must match their entity type: plan-header/plan-body for plans, objective-header/objective-roadmap/objective-body for objectives.

**using surgical update for complete table rewrites** → Read [Roadmap Mutation Patterns](roadmap-mutation-patterns.md) first. Surgical updates only change one node. For rewriting roadmaps after landing PRs (status + layout changes), use full-body update (system:objective-update-with-landed-pr).

**writing objective content directly to issue body** → Read [Objective Create Workflow](objective-create-workflow.md) first. Issue body holds only metadata blocks. Full content goes in the first comment (objective-body block). See the 3-layer storage model.
