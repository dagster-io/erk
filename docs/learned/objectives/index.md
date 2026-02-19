<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Objectives Documentation

- **[batch-objective-update.md](batch-objective-update.md)** — modifying objective node status in bulk, working with --all-unblocked dispatch, asserting on FakeGitHubIssues.updated_bodies in tests
- **[dependency-graph.md](dependency-graph.md)** — working with ObjectiveNode or DependencyGraph types, implementing dependency-aware step traversal, converting between roadmap phases and graph representations
- **[objective-create-workflow.md](objective-create-workflow.md)** — modifying the objective creation flow, understanding how objective-render-roadmap and objective-save-to-issue work together, debugging objective creation failures
- **[objective-lifecycle.md](objective-lifecycle.md)** — creating or modifying objective lifecycle code, understanding how objectives are created, mutated, and closed, adding new mutation paths to objective roadmaps, working with objective-fetch-context or auto-discovery, using --next flag on objective implement
- **[objective-roadmap-check.md](objective-roadmap-check.md)** — validating objective roadmap consistency beyond structure, understanding why check command exists separate from parsing, adding new validation checks to objective check
- **[objective-storage-format.md](objective-storage-format.md)** — understanding how objective issues store their data, creating or modifying objective creation code, working with objective metadata blocks
- **[objective-view-json.md](objective-view-json.md)** — using erk objective view --json-output, consuming structured objective data programmatically, understanding the graph output format
- **[phase-name-enrichment.md](phase-name-enrichment.md)** — working with phase names in roadmap parsing, assuming phase names are stored in YAML frontmatter, understanding how group_nodes_by_phase derives phase membership
- **[plan-reference-preservation.md](plan-reference-preservation.md)** — calling update-objective-node with --pr but without --plan, changing update_node_in_frontmatter() semantics for plan=None, updating objective roadmap step plan or PR references, debugging lost plan references in objective roadmaps
- **[research-documentation-integration.md](research-documentation-integration.md)** — deciding whether objective work should produce learned docs, choosing between manual doc capture and the learn workflow during an objective, capturing cross-cutting discoveries from multi-plan investigations
- **[roadmap-format-versioning.md](roadmap-format-versioning.md)** — extending the roadmap table format with new columns, planning backward-compatible parser changes to roadmap tables, understanding the 4-col to 5-col migration
- **[roadmap-mutation-patterns.md](roadmap-mutation-patterns.md)** — deciding between surgical vs full-body roadmap updates, choosing how to update an objective roadmap after a workflow event, understanding race condition risks in roadmap table mutations
- **[roadmap-parser-api.md](roadmap-parser-api.md)** — adding a new consumer of roadmap.py in erk_shared, extending the roadmap data model with new fields, understanding why the shared parser exists separately from its consumers
- **[roadmap-parser.md](roadmap-parser.md)** — understanding how roadmap nodes are parsed, working with objective roadmap check or update commands, debugging roadmap parsing issues, using erk objective check or erk exec update-objective-node
- **[roadmap-status-system.md](roadmap-status-system.md)** — understanding how objective roadmap status is determined, working with roadmap step status values, debugging unexpected status in an objective roadmap
- **[roadmap-validation.md](roadmap-validation.md)** — debugging roadmap validation errors or check failures, adding new validation rules to objective check or update commands, understanding why validation is split across parser and check command
