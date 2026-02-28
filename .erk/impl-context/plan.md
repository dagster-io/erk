# Remove Dead Code and Test-Only Symbols

## Context

Commit c9147a90d deleted 13 unused `erk exec` scripts. This left `NodeSlugGenerator` in `src/erk/core/` with zero production callers (only tests). It also exposed pre-existing test-only symbols in `erk_shared.naming` that have no production consumers: `extract_trailing_number` and `derive_branch_name_from_title`. This plan removes all of them.

## Changes

### 1. Delete `node_slug_generator.py` and its test

- **Delete** `src/erk/core/node_slug_generator.py` (entire file — `NodeSlugGenerator`, `NodeSlugResult`, `_postprocess_node_slug`)
- **Delete** `tests/core/test_node_slug_generator.py` (entire test file)

### 2. Remove stale comment in `plan_duplicate_checker.py`

- **Edit** `src/erk/core/plan_duplicate_checker.py` line 7 — remove or reword the comment `"Mirrors the NodeSlugGenerator pattern: concrete class, PromptExecutor injection, model="haiku", frozen result dataclass."`
  Replace with a self-contained description like `"Concrete class with PromptExecutor injection, model='haiku', frozen result dataclass."`

### 3. Remove node slug validation types from `erk_shared.naming`

These symbols have zero production consumers outside `node_slug_generator.py` (which is being deleted). `slugify_node_description` is NOT removed — it's still used by `objective_render_roadmap.py`.

**File:** `packages/erk-shared/src/erk_shared/naming.py`

- **Delete** private constants `_NODE_SLUG_MIN_LENGTH` (line 83) and `_NODE_SLUG_MAX_LENGTH` (line 84)
- **Delete** `ValidNodeSlug` class (lines 396-404)
- **Delete** `InvalidNodeSlug` class (lines 407-436)
- **Delete** `validate_node_slug` function (lines 439-463)
- **Keep** `slugify_node_description` (lines 466-480) — still has production callers

### 4. Remove `extract_trailing_number` from `erk_shared.naming`

Zero callers in production code. Not called internally within `naming.py`.

- **Delete** `extract_trailing_number` function (lines 763-788)

### 5. Remove `derive_branch_name_from_title` from `erk_shared.naming`

Zero callers in production code or workflows. Not called internally within `naming.py`.

- **Delete** `derive_branch_name_from_title` function (lines 964-1007)

### 6. Clean up test imports and test sections in `test_naming.py`

**File:** `tests/core/utils/test_naming.py`

- Remove imports: `InvalidNodeSlug`, `ValidNodeSlug`, `derive_branch_name_from_title`, `extract_trailing_number`, `validate_node_slug` (lines 8, 12, 17, 20, 26)
- Delete test section: `test_extract_trailing_number` (lines 178-197)
- Delete test section: `test_derive_branch_name_from_title` and `test_derive_branch_name_truncates_to_30_chars` (lines 327-372)
- Delete test section: `validate_node_slug` tests (lines 740-792) — the section header comment through `test_validate_node_slug_message_includes_rules`
- **Keep** `slugify_node_description` tests (lines 795-823) — the function is still live

## Files Modified

| File | Action |
|------|--------|
| `src/erk/core/node_slug_generator.py` | Delete |
| `tests/core/test_node_slug_generator.py` | Delete |
| `src/erk/core/plan_duplicate_checker.py` | Edit comment |
| `packages/erk-shared/src/erk_shared/naming.py` | Remove 5 symbols + 2 constants |
| `tests/core/utils/test_naming.py` | Remove imports + 3 test sections |

## Verification

1. Run affected unit tests: `uv run pytest tests/core/utils/test_naming.py -v`
2. Run the package tests: `uv run pytest packages/erk-shared/tests/unit/test_plan_utils.py -v`
3. Grep to confirm no remaining references: `grep -r "NodeSlugGenerator\|extract_trailing_number\|derive_branch_name_from_title\|validate_node_slug\|InvalidNodeSlug\|ValidNodeSlug" src/ tests/ packages/`
4. Run type checker: `uv run ty check src/erk/core/ packages/erk-shared/src/erk_shared/naming.py`
5. Run full fast-ci to confirm nothing breaks
