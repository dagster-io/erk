# Inline Roadmap JSON into objective-save-to-issue

## Context

The objective creation pipeline is fragile because it relies on Claude to: (1) construct JSON, (2) pipe it to `objective-render-roadmap`, (3) capture the output, (4) paste it into a markdown file. Claude can skip steps 2-3 and hand-write markdown tables, resulting in objectives with no YAML source of truth. This happened with #9394.

**Principle:** YAML is the source of truth for the roadmap dependency graph. Markdown tables are a rendering of it. We never parse markdown tables.

**Fix:** `objective-save-to-issue` accepts `--roadmap-json <path>` and handles YAML creation + markdown rendering internally. Delete `objective-render-roadmap`.

## Changes

### 1. Add `PhaseMetadata` dataclass and `roadmap_nodes_from_json()` to roadmap.py

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`

Add `PhaseMetadata` frozen dataclass (captures phase-level info from JSON that isn't stored in YAML: `number`, `name`, `description`, `pr_count`, `test`).

Add `roadmap_nodes_from_json(data: dict) -> tuple[list[RoadmapNode], list[PhaseMetadata], str | None]`:
- Absorbs validation logic from `_validate_input()` in `objective_render_roadmap.py`
- Absorbs RoadmapNode construction + slug generation via `slugify_node_description()`
- Returns `(nodes, phase_metadata, error_message)`

### 2. Add `render_initial_roadmap_section()` to roadmap.py

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`

Add `render_initial_roadmap_section(nodes: list[RoadmapNode], phase_metadata: list[PhaseMetadata]) -> str`:
- Renders phase headers using JSON's `pr_count` field (e.g., "### Phase 1: Steelthread (1 PR)")
- Renders markdown tables using `escape_md_table_cell()` (reuse existing pattern from `render_roadmap_tables`)
- Includes phase descriptions and test sections
- Wraps entire section in `ROADMAP_TABLE_MARKER_START` / `ROADMAP_TABLE_MARKER_END`
- Returns complete `## Roadmap` section ready to insert into comment

**Note on PR count:** `render_roadmap_tables()` computes PR count from linked PRs (0 at creation). `render_initial_roadmap_section` uses the JSON's freeform `pr_count`. After first `rerender_comment_roadmap` call, the computed count takes over. This is fine — the YAML is the source of truth, not the header text.

### 3. Modify `create_objective_issue()` signature

**File:** `packages/erk-shared/src/erk_shared/gateway/github/objective_issues.py`

Add two optional parameters:
```python
def create_objective_issue(
    ...
    roadmap_nodes: list[RoadmapNode] | None = None,
    phase_metadata: list[PhaseMetadata] | None = None,
) -> CreateObjectiveIssueResult:
```

When `roadmap_nodes` is provided:
- **Issue body (Step 4):** Build YAML block directly via `render_roadmap_block_inner(roadmap_nodes)` + `render_objective_roadmap_block()`. Skip `_build_objective_roadmap_block()`.
- **Comment (Step 6):** Assemble prose + `render_initial_roadmap_section(nodes, phase_metadata)`, then pass to `format_objective_content_comment()`. The `wrap_roadmap_tables_with_markers` inside that function is a no-op since markers already exist.

When `roadmap_nodes` is None: existing behavior unchanged (extract YAML from plan_content).

Keep `_build_objective_roadmap_block` — it's the fallback path.

### 4. Add `--roadmap-json` to `objective-save-to-issue`

**File:** `src/erk/cli/commands/exec/scripts/objective_save_to_issue.py`

Add Click option:
```python
@click.option("--roadmap-json", "roadmap_json_path", type=click.Path(exists=True, path_type=Path), default=None)
```

When provided:
1. Read JSON from file
2. Call `roadmap_nodes_from_json(data)` — validate and convert
3. On error, output JSON error and exit 1
4. Pass `roadmap_nodes=nodes, phase_metadata=phase_metadata` to `create_objective_issue()`

Plan content (prose) still loaded from scratch dir. It should not contain a `## Roadmap` section, but if it does, the fallback path handles it.

### 5. Delete `objective-render-roadmap`

- Delete `src/erk/cli/commands/exec/scripts/objective_render_roadmap.py`
- Delete `tests/unit/cli/commands/exec/scripts/test_objective_render_roadmap.py`
- Remove import + `add_command` from `src/erk/cli/commands/exec/group.py`
- Remove entry from `.claude/skills/erk-exec/reference.md`

### 6. Update `/erk:objective-create` skill

**File:** `.claude/commands/erk/objective-create.md`

Change the flow:
- Claude writes prose (no roadmap section) to `objective-body.md`
- Claude writes phases JSON to `roadmap.json` in scratch dir
- Claude calls: `erk exec objective-save-to-issue --session-id=X --slug=Y --roadmap-json=.erk/scratch/sessions/$SESSION/roadmap.json --format=display --validate`
- Remove all references to `erk exec objective-render-roadmap`
- Remove "Do NOT manually write roadmap tables" warning (no longer relevant)

### 7. Tests

**New tests in `packages/erk-shared/tests/unit/github/metadata/test_roadmap.py`:**
- `roadmap_nodes_from_json()` — valid input, missing phases, empty steps, invalid types (port existing `_validate_input` tests)
- `render_initial_roadmap_section()` — correct headers, tables, markers, test sections, depends_on column
- Round-trip: JSON → nodes → YAML → `parse_roadmap_frontmatter` → nodes match

**New tests in `tests/unit/cli/commands/exec/scripts/test_objective_save_to_issue.py`:**
- `--roadmap-json` with valid JSON → correct YAML in issue body
- `--roadmap-json` with invalid JSON → error output
- Comment roundtrip: `rerender_comment_roadmap()` is idempotent on created comment
- Without `--roadmap-json` → existing behavior preserved

### 8. Update docs

- `docs/learned/objectives/objective-create-workflow.md` — update pipeline description
- Remove references to `objective-render-roadmap` from any tripwires/docs

## Verification

1. Run existing `test_objective_save_to_issue.py` tests — all pass (backwards compat)
2. Run new tests for `roadmap_nodes_from_json` and `render_initial_roadmap_section`
3. Manual test: create an objective using updated skill, verify YAML block appears in issue body and markdown tables in comment
4. Verify `erk objective check <number>` passes on the new objective (validates roadmap is parseable)
5. Verify `erk exec update-objective-node <number> --node 1.1 --status planning` works (proves YAML source of truth is correct)
