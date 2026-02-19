# Rename `.erk/branch-data/` to `.erk/impl-context/`

## Context

The `.erk/branch-data/` directory stores plan files (`plan.md`, `ref.json`) committed to plan branches for draft-PR-backed plans. The name "branch-data" is generic and doesn't convey its purpose. Renaming to "impl-context" aligns with erk's existing terminology (`.impl/`, `.worker-impl/`) and better describes the directory's role as implementation context.

## Changes

### 1. Source files — rename paths and variables

**`src/erk/cli/commands/exec/scripts/plan_save.py`** (lines 160-175):
- Rename variable `branch_data_dir` → `impl_context_dir` (3 occurrences)
- Update path `".erk" / "branch-data"` → `".erk" / "impl-context"`
- Update string literals `".erk/branch-data/plan.md"` and `".erk/branch-data/ref.json"` → `".erk/impl-context/..."`

**`src/erk/cli/commands/exec/scripts/plan_migrate_to_draft_pr.py`** (lines 168-172):
- Rename variable `branch_data_dir` → `impl_context_dir` (3 occurrences)
- Update path `".erk" / "branch-data"` → `".erk" / "impl-context"`
- Update string literal `".erk/branch-data/plan.md"` → `".erk/impl-context/plan.md"`

### 2. Tests — update path assertions and comments

**`tests/unit/cli/commands/exec/scripts/test_plan_save.py`** (lines 214-258):
- Update all `".erk" / "branch-data"` path constructions → `".erk" / "impl-context"`
- Update all `".erk/branch-data/..."` string literal assertions → `".erk/impl-context/..."`
- Update comments/docstrings referencing `branch-data`

### 3. Documentation — update references

**`packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py`** (lines 10-11):
- Update docstring references to `.erk/branch-data/` → `.erk/impl-context/`

**`.claude/commands/erk/migrate-plan-to-draft-pr.md`** (line 14):
- Update `.erk/branch-data/plan.md` → `.erk/impl-context/plan.md`

**`docs/learned/architecture/plan-save-branch-restoration.md`** (line 28):
- Update `.erk/branch-data/plan.md` → `.erk/impl-context/plan.md`

## Not changed

- `branch_data` variables in `tests/test_utils/graphite_helpers.py` (unrelated Graphite mock data)
- `branch=data[...]` in `command_log.py` and `real.py` (unrelated field access)
- "branch data" in `test_graphite_parsing.py` docstring (unrelated concept)

## Verification

1. Run unit tests: `uv run pytest tests/unit/cli/commands/exec/scripts/test_plan_save.py`
2. Run type checker: `uv run ty check src/erk/cli/commands/exec/scripts/plan_save.py src/erk/cli/commands/exec/scripts/plan_migrate_to_draft_pr.py`
3. Grep for stale references: `rg "branch-data" --type py --type md` — should return zero hits in the changed files