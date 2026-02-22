# Plan: Add Slugs to Objective Nodes

## Context

Objective nodes are currently identified only by numeric IDs (`1.1`, `2.3`). The user wants each node to have a kebab-case slug inferred from its description (e.g., `add-user-model`), generated via LLM (like branch slugs). Slugs should be stable once persisted and used in CLIs.

## Design Decisions

- **LLM-based generation** via a new `NodeSlugGenerator` class (batched: one LLM call for all nodes)
- **Deterministic fallback** when LLM unavailable (strip filler words, hyphenate key terms)
- **Stable once persisted**: slugs are not regenerated when descriptions change
- **Schema version bump to `"4"`** to indicate slug field presence
- **Lazy migration**: existing v3 objectives get slugs auto-generated on first parse, persisted on next write
- **Uniqueness**: enforced within an objective (append `-2`, `-3` on collision)

## Implementation

### Step 1: Add slug utilities to naming module

**File**: `packages/erk-shared/src/erk_shared/naming.py`

Add:
- `slugify_node_description(description: str) -> str` - deterministic fallback: lowercase, strip filler words, take first 4 words, hyphenate, max 30 chars
- `make_unique_slug(slug: str, existing_slugs: set[str]) -> str` - append `-2`, `-3` etc. on collision
- `validate_node_slug(slug: str) -> ValidNodeSlug | InvalidNodeSlug` - same pattern as objective slugs, 2-30 chars

### Step 2: Create `NodeSlugGenerator` class

**New file**: `src/erk/core/node_slug_generator.py`

Mirrors `src/erk/core/branch_slug_generator.py` pattern:
- Uses `PromptExecutor.execute_prompt()` with haiku model
- System prompt: "Given a list of descriptions, return a slug for each. Output one slug per line."
- Input: newline-separated descriptions
- Output: newline-separated slugs
- Batched: one LLM call for all nodes in an objective
- Falls back to `slugify_node_description()` per-node on LLM failure
- Post-processing: validate each slug, ensure uniqueness

### Step 3: Add `slug` field to data models

**File**: `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`
- Add `slug: str | None` to `RoadmapNode` (after `id`, before `description`)

**File**: `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py`
- Add `slug: str | None` to `ObjectiveNode` (after `id`, before `description`)

### Step 4: Update YAML parsing

**File**: `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`

In `validate_roadmap_frontmatter()`:
- Accept schema versions `"2"`, `"3"`, `"4"`
- Parse optional `slug` field from each node
- When `slug` is absent (v2/v3 data), auto-generate via `slugify_node_description()` + uniqueness
- Track `seen_slugs: set[str]` across all nodes

### Step 5: Update YAML serialization

**File**: `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`

In `render_roadmap_block_inner()`:
- Add `"slug": s.slug` to node dict (after `"id"`)
- Emit `schema_version: "4"`

In `serialize_phases()`:
- Add `"slug": step.slug` to JSON output

In `find_next_node()`:
- Add `"slug": step.slug` to return dict

### Step 6: Update graph conversion functions

**File**: `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py`

Add `slug=roadmap_node.slug` / `slug=node.slug` to ObjectiveNode construction in:
- `graph_from_phases()` (line ~128)
- `graph_from_nodes()` (line ~153)
- `nodes_from_graph()` (line ~183)

In `find_graph_next_node()`:
- Add `"slug": target_node.slug` to return dict

### Step 7: Create `erk exec generate-node-slugs` command

**New file**: `src/erk/cli/commands/exec/scripts/generate_node_slugs.py`

- Takes JSON on stdin: `{"descriptions": ["Add user model", "Wire into CLI"]}`
- Uses `NodeSlugGenerator` to produce slugs via LLM
- Outputs JSON: `{"slugs": ["add-user-model", "wire-cli"], "success": true}`
- Register in exec group

### Step 8: Update `objective-render-roadmap` creation path

**File**: `src/erk/cli/commands/exec/scripts/objective_render_roadmap.py`

- Accept optional `slug` per step in JSON input
- If slug provided, validate and use it
- If slug absent, use deterministic fallback (`slugify_node_description`)
- Pass `slug=slug` to `RoadmapNode()` constructor
- Track uniqueness across all phases

### Step 9: Update `objective-create` skill

**File**: `.claude/skills/objective/SKILL.md` (and references)

- Instruct the creating agent to generate a `slug` field for each step in the roadmap JSON
- Alternatively, call `erk exec generate-node-slugs` first and merge results

### Step 10: Update CLI view display

**File**: `src/erk/cli/commands/objective/view_cmd.py`

- Add slug to Rich table display (e.g., node column shows `1.1 add-user-model`)
- Add `"slug"` to JSON output in graph nodes

### Step 11: Update all test fixtures

All files constructing `RoadmapNode(...)` or `ObjectiveNode(...)` need the `slug` parameter. Key test files:
- `packages/erk-shared/tests/unit/github/metadata/test_dependency_graph.py`
- `packages/erk-shared/tests/unit/github/metadata/test_roadmap*.py`
- `tests/unit/cli/commands/exec/scripts/test_objective_render_roadmap.py`
- `tests/unit/cli/commands/exec/scripts/test_update_objective_node.py`
- `tests/unit/cli/commands/objective/test_view_cmd.py`

### Step 12: New tests

- `packages/erk-shared/tests/unit/naming/test_node_slug.py` - test `slugify_node_description`, `make_unique_slug`, `validate_node_slug`
- `tests/unit/core/test_node_slug_generator.py` - test `NodeSlugGenerator` with `FakePromptExecutor`
- `tests/unit/cli/commands/exec/scripts/test_generate_node_slugs.py` - test the exec command
- Update existing frontmatter parsing tests for v4 schema + slug round-trip

## Verification

1. Run `erk exec objective-render-roadmap` with JSON input (with and without slugs) - verify YAML output includes slugs
2. Run `erk exec generate-node-slugs` with descriptions - verify LLM-generated slugs
3. Parse an existing v3 objective - verify slugs are auto-generated
4. Run `erk exec update-objective-node` on an objective - verify slugs survive round-trip
5. Run `erk objective view` - verify slugs appear in CLI and JSON output
6. Run full CI (pytest, ty, ruff)
