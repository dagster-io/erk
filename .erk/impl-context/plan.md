# Plan: Objective Node Management Improvements

## Context

During objective #8470 re-evaluation, we hit gaps in node management tooling:
- Couldn't update node descriptions after the objective scope changed
- Couldn't add new nodes programmatically (had to document in comments instead)
- Couldn't attach reasons when skipping nodes (lost the "why")

Three improvements, all building on the existing `update-objective-node` patterns.

## Changes

### 1. Add `--description`, `--slug`, `--reason` to `update-objective-node`

**Files:**
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py` — RoadmapNode + frontmatter functions
- `src/erk/cli/commands/exec/scripts/update_objective_node.py` — CLI command
- `tests/unit/cli/commands/exec/scripts/test_update_objective_node.py` — tests

**roadmap.py changes:**
- Add `reason: str | None` field to `RoadmapNode` (after `slug`, default `None`)
- Update `validate_roadmap_frontmatter()`: parse optional `reason` field from YAML
- Update `render_roadmap_block_inner()`: include `reason` in YAML output only when non-None
- Extend `update_node_in_frontmatter()` signature: add `description: str | None = None`, `slug: str | None = None`, `reason: str | None = None` kwargs. Apply via `replace()` when non-None, same pattern as existing `pr`/`status`.
- `reason` is NOT shown in rendered markdown tables (display metadata only, visible in raw YAML)

**update_objective_node.py changes:**
- Add Click options: `--description`, `--slug` (strings), `--reason` (string)
- Update validation: at least one of `--pr`, `--status`, `--description`, `--slug`, `--reason` required
- Pass through to `_replace_node_refs_in_body()` → `update_node_in_frontmatter()`

**Tests:** Add tests for `--description`, `--slug`, `--reason` flags covering: value set, value preserved when not passed, combined with status changes.

### 2. New `add-objective-node` exec script

**New file:** `src/erk/cli/commands/exec/scripts/add_objective_node.py`

**Interface:**
```
erk exec add-objective-node 8470 \
  --phase 1 \
  --description "Clean up dead modify_existing code" \
  --slug cleanup-modify-existing \
  [--status pending] \
  [--depends-on 1.2] [--depends-on 1.3] \
  [--reason "Added during objective re-evaluation"]
```

**CLI options:**
- `ISSUE_NUMBER` (argument)
- `--phase` (required, int) — phase number to add to
- `--description` (required) — node description
- `--slug` (optional) — kebab-case identifier, auto-generated from description if omitted
- `--status` (optional, default "pending")
- `--depends-on` (optional, multiple) — dependency node IDs
- `--reason` (optional) — reason for adding

**Logic:**
1. Fetch issue, parse roadmap, validate phase exists (or allow creating new phase)
2. Auto-assign node ID: find max node number in phase, increment (e.g., phase 1 has 1.1-1.3 → new node is 1.4)
3. Validate node ID doesn't already exist
4. Create new `RoadmapNode`, append to flat list after last node of same phase
5. Re-render frontmatter YAML via `render_roadmap_block_inner()`
6. Replace metadata block in issue body
7. Write back to GitHub
8. Re-render comment table if v2 format

**roadmap.py:** Add `add_node_to_frontmatter()` function — parses frontmatter, appends node after last node with matching phase prefix, re-renders. Returns updated block content + assigned node ID.

**Output:** JSON with `{success, issue_number, node_id, url}`

**Registration:** Import in `group.py`, add `exec_group.add_command(add_objective_node, name="add-objective-node")`

**New test file:** `tests/unit/cli/commands/exec/scripts/test_add_objective_node.py`
- Test adding to existing phase
- Test adding to new phase
- Test auto-ID assignment
- Test duplicate node ID rejection
- Test slug auto-generation
- Test with depends-on
- Test v2 comment table re-rendering

### 3. Auto-generate slug from description

Simple helper in `roadmap.py`:
```python
def slugify_description(description: str) -> str:
    """Convert description to kebab-case slug."""
    # lowercase, replace non-alnum with hyphens, collapse, strip
```

Used by `add-objective-node` when `--slug` is omitted.

### 4. Update objective skill

**File:** `.claude/skills/objective/SKILL.md`

Add to Quick Reference section:
- **Updating Node Details** — `erk exec update-objective-node` with `--description`, `--slug`, `--reason`
- **Adding Nodes** — `erk exec add-objective-node` with examples
- **Skipping with Reason** — `--status skipped --reason "..."` pattern

## File Summary

| File | Change |
|------|--------|
| `packages/erk-shared/.../roadmap.py` | Add `reason` to RoadmapNode, extend `update_node_in_frontmatter()`, add `add_node_to_frontmatter()`, add `slugify_description()` |
| `src/.../update_objective_node.py` | Add `--description`, `--slug`, `--reason` options |
| `src/.../add_objective_node.py` | New exec script |
| `src/.../exec/group.py` | Register `add-objective-node` |
| `tests/.../test_update_objective_node.py` | Tests for new flags |
| `tests/.../test_add_objective_node.py` | New test file |
| `.claude/skills/objective/SKILL.md` | Document new capabilities |

## Verification

1. Run unit tests: `pytest tests/unit/cli/commands/exec/scripts/test_update_objective_node.py tests/unit/cli/commands/exec/scripts/test_add_objective_node.py`
2. Run `ty` for type checking
3. Run `ruff` for linting
4. Manual test against objective #8470: add the modify_existing cleanup node and update 2.x descriptions
