---
title: Metadata Module API Reference
read_when:
  - "importing metadata functions for objectives or plans"
  - "working with metadata blocks (objective-header, objective-roadmap, plan-header)"
  - "parsing or rendering roadmap YAML"
  - "updating objective comments or issue bodies"
  - "encountering import errors for metadata functions"
tripwires:
  - action: "guessing import paths for metadata functions"
    warning: "All metadata functions live under erk_shared.gateway.github.metadata. Read this doc for exact paths."
    pattern: "from erk\\..*metadata"
  - action: "importing roadmap functions from core.py"
    warning: "Roadmap functions (parse, render, update) are in roadmap.py, not core.py. core.py handles generic metadata blocks."
    pattern: "from.*core.*import.*roadmap"
---

# Metadata Module API Reference

Quick-reference for the public API surface of `packages/erk-shared/src/erk_shared/gateway/github/metadata/`.

## Module Structure

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/ -->

See the `metadata/` package in `packages/erk-shared/src/erk_shared/gateway/github/` for the three-module structure: `core.py` (generic block operations), `roadmap.py` (roadmap-specific parsing/rendering/mutation), and `dependency_graph.py` (DAG operations).

## core.py - Generic Metadata Block Operations

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py -->

See `core.py` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/` for the full public API. Key functions: `find_metadata_block()`, `extract_metadata_value()`, `replace_metadata_block_in_body()`, and objective-specific helpers like `extract_objective_header_comment_id()`, `extract_objective_slug()`, `render_objective_body_block()`.

## roadmap.py - Roadmap Parsing, Rendering, Mutation

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py -->

See `roadmap.py` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/` for the full public API. Key types: `RoadmapNode`, `RoadmapPhase`, `RoadmapNodeStatus`. Key functions: `parse_roadmap()`, `render_roadmap_tables()`, `update_node_in_frontmatter()`, `enrich_phase_names()`. Table markers: `ROADMAP_TABLE_MARKER_START`, `ROADMAP_TABLE_MARKER_END`.

## dependency_graph.py - DAG Operations

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py -->

See `dependency_graph.py` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/` for the full public API. Key types: `ObjectiveNode`, `DependencyGraph`. Key functions: `build_graph()`, `graph_from_phases()`, `phases_from_graph()`, `find_graph_next_node()`. `DependencyGraph` has instance methods: `unblocked_nodes()`, `pending_unblocked_nodes()`, `next_node()`, `is_complete()`.

## Common Patterns

### Parse roadmap from issue body

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, parse_roadmap -->

Call `parse_roadmap(issue.body)` to get a tuple of `(phases, errors)`. If `phases` is empty, the errors list describes what went wrong. See `parse_roadmap()` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py` for the full signature. For caller examples, see `check_cmd.py` in `src/erk/cli/commands/objective/`.

### Update a node in frontmatter YAML

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py, extract_raw_metadata_blocks -->
<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, update_node_in_frontmatter -->
<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py, replace_metadata_block_in_body -->

Extract raw metadata blocks with `extract_raw_metadata_blocks(issue.body)`, find the block with `key == "objective-roadmap"`, then call `update_node_in_frontmatter()` on its body to modify a node's status/PR fields. Finally, splice the updated content back into the issue body with `replace_metadata_block_in_body()`. See `extract_raw_metadata_blocks()` and `replace_metadata_block_in_body()` in `core.py`, and `update_node_in_frontmatter()` in `roadmap.py` under `packages/erk-shared/src/erk_shared/gateway/github/metadata/`. For caller examples, see `submit_pipeline.py` in `src/erk/cli/commands/pr/` and `objective_link_pr.py` in `src/erk/cli/commands/exec/scripts/`.

### Render tables for a comment

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, enrich_phase_names -->
<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, render_roadmap_tables -->

Call `enrich_phase_names(comment_body, phases)` to restore phase display names from the comment body text, then pass the enriched phases to `render_roadmap_tables()` to produce the markdown table output. See `enrich_phase_names()` and `render_roadmap_tables()` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`.

### Get objective comment ID

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py, extract_objective_header_comment_id -->

Call `extract_objective_header_comment_id(issue.body)` to retrieve the comment ID stored in the objective-header metadata block. Returns `int | None` — check for `None` before using the ID to fetch the comment. See `extract_objective_header_comment_id()` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py`.
