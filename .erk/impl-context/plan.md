# Rename RoadmapNode `reason` field to `comment`

## Context

The `RoadmapNode` dataclass has a field called `reason` that holds optional text explaining why a node is in a particular state. The user wants to rename this to `comment` to better reflect its purpose in the objective YAML.

This is a mechanical rename across ~30 locations in production code, CLI commands, tests, and documentation.

## Files to Modify

### 1. Core dataclass & parser — `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`
- **Line 40**: Rename field `reason` → `comment` in `RoadmapNode` dataclass
- **Line 152-155**: Rename `raw_reason` → `raw_comment`, update validation string `'reason'` → `'comment'`
- **Line 165**: `reason=raw_reason` → `comment=raw_comment`
- **Line 220**: `any_has_reason` → `any_has_comment`, `s.reason` → `s.comment`
- **Lines 232-233**: `"reason"` key → `"comment"`, `s.reason` → `s.comment`
- **Line 330**: `update_node_in_frontmatter()` parameter `reason:` → `comment:`
- **Line 341**: Update docstring
- **Lines 379-380**: `reason` → `comment` in replacements dict
- **Line 401**: `add_node_to_frontmatter()` parameter `reason:` → `comment:`
- **Line 415**: Update docstring
- **Line 455**: `reason=reason` → `comment=comment`
- **Line 701**: `serialize_phases()` — `"reason": step.reason` → `"comment": step.comment`

### 2. Dependency graph — `packages/erk-shared/src/erk_shared/gateway/github/metadata/dependency_graph.py`
- **Line 204**: `reason=None` → `comment=None`

### 3. Update objective node CLI — `src/erk/cli/commands/exec/scripts/update_objective_node.py`
- CLI option `--reason` → `--comment`, dest `new_reason` → `new_comment`
- Function parameters and calls: `reason=` → `comment=`
- Help text and error messages

### 4. Add objective node CLI — `src/erk/cli/commands/exec/scripts/add_objective_node.py`
- CLI option `--reason` → `--comment`
- Function parameter and call

### 5. Objective render roadmap — `src/erk/cli/commands/exec/scripts/objective_render_roadmap.py`
- **Line 188**: `reason=None` → `comment=None`

### 6. Tests
- `tests/unit/cli/commands/exec/scripts/test_update_objective_node.py` — update all `reason=` kwargs, `--reason` CLI args, test function names
- `tests/unit/cli/commands/exec/scripts/test_add_objective_node.py` — update `--reason` CLI arg and assertions

### 7. Documentation — `docs/learned/objectives/roadmap-parser-api.md`
- Update all references to `reason` field → `comment`

## Approach

Use a combination of targeted `Edit` calls for production code and the `libcst-refactor` agent for bulk parameter renames across test files. The YAML key in serialized output changes from `"reason"` to `"comment"`.

**Note**: Hard rename only — no backwards compatibility for `reason`. Existing objectives with `reason:` in YAML will need manual backfill (user will handle separately).

## Verification

1. Run `ruff check` and `ty` via devrun agent
2. Run unit tests for affected test files via devrun agent
3. Run `make fast-ci` via devrun agent
