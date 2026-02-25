# Plan: Remove plan docs/learn and delete plan group

**Part of Objective #7978, Nodes 4.1 + 4.2**

## Context

Objective #7978 "Unify CLI Under erk pr with Universal Lifecycle Stages" has moved all plan commands to `erk pr` (nodes 1.1–3.4, all done). The `plan` CLI group now only contains three remnants:

1. **`erk plan docs`** (extract/unextract/unextracted) — manages `docs-extracted` label on issues. Unused: no skills, commands, workflows, or docs reference these. Safe to delete.
2. **`erk plan learn complete`** — DEPRECATED, unconditionally raises ClickException
3. **`erk plan duplicate-check`** — semantic duplicate detection via LLM. Active feature, needs relocation.

## Approach

### Phase 1: Move `duplicate-check` to `erk pr`

**Move file:**
- `src/erk/cli/commands/plan/duplicate_check_cmd.py` → `src/erk/cli/commands/pr/duplicate_check_cmd.py`

**Update `src/erk/cli/commands/pr/__init__.py`:** Import and register `duplicate_check_plan` as `duplicate-check`.

**Update help text/examples** in the moved file: `erk plan duplicate-check` → `erk pr duplicate-check`.

### Phase 2: Delete plan group and all remaining files

**Update `src/erk/cli/cli.py`:**
- Remove import: `from erk.cli.commands.plan import plan_group` (line 29)
- Remove registration: `cli.add_command(plan_group)` (line 201)

**Delete entire directory:** `src/erk/cli/commands/plan/` — this removes:
- `__init__.py` (plan group definition)
- `duplicate_check_cmd.py` (already moved)
- `docs/__init__.py`, `docs/extract_cmd.py`, `docs/unextract_cmd.py`, `docs/unextracted_cmd.py` (unused)
- `learn/__init__.py`, `learn/complete_cmd.py` (deprecated)

**Clean up constants in `src/erk/cli/constants.py`:** Remove `DOCS_EXTRACTED_LABEL`, `DOCS_EXTRACTED_LABEL_DESCRIPTION`, `DOCS_EXTRACTED_LABEL_COLOR` (only consumed by deleted commands).

### Phase 3: Fix stale references

**`src/erk/cli/commands/navigation_helpers.py`** lines 35 and 55: Update references from `erk plan learn raw` to `erk learn` (the active top-level replacement).

### Phase 4: Update tests

- `tests/commands/plan/test_duplicate_check.py` — update CLI invocation from `["plan", "duplicate-check", ...]` to `["pr", "duplicate-check", ...]`
- `tests/commands/plan/docs/test_docs.py` — DELETE (tests deleted commands)
- `tests/commands/plan/learn/test_complete.py` — DELETE (tests deprecated command)
- Clean up empty `__init__.py` files in `tests/commands/plan/docs/` and `tests/commands/plan/learn/` if their test files are deleted

Note: The physical move of `tests/commands/plan/test_duplicate_check.py` → `tests/commands/pr/` is node 4.3's scope.

## Files Modified

| File | Action |
|------|--------|
| `src/erk/cli/commands/pr/__init__.py` | Add duplicate-check import + registration |
| `src/erk/cli/commands/pr/duplicate_check_cmd.py` | NEW (moved from plan/, update examples) |
| `src/erk/cli/cli.py` | Remove plan_group import and registration |
| `src/erk/cli/constants.py` | Remove DOCS_EXTRACTED_* constants |
| `src/erk/cli/commands/navigation_helpers.py` | Fix stale `erk plan learn` reference |
| `src/erk/cli/commands/plan/` | DELETE entire directory |
| `tests/commands/plan/docs/` | DELETE directory (tests for deleted commands) |
| `tests/commands/plan/learn/` | DELETE directory (tests for deprecated command) |
| `tests/commands/plan/test_duplicate_check.py` | Update CLI invocation paths |

## Verification

1. `erk pr --help` — should show `duplicate-check`
2. `erk --help` — should NOT show `plan` group
3. `erk pr duplicate-check --help` — should work with updated examples
4. Run fast CI (pytest + ty + ruff) to confirm no broken imports or test failures
