# Plan: Rename PlanContext and validate_plan_title (Nodes 1.5–1.6)

Part of Objective #9318, Nodes 1.5–1.6

## Context

Continuing the plan-to-PR terminology rename (Objective #9318). Nodes 1.1–1.4 were completed in PR #9319 which renamed type classes (`PlanNotFound` → `PrNotFound`, `PlanListService` → `PrListService`, etc.). Nodes 1.5–1.6 complete Phase 1 by renaming the remaining class and function.

## Node 1.5: Rename `PlanContext` → `PrContext`

**Definition site:** `src/erk/core/plan_context_provider.py:17`

**13 files with usages** (imports + references):

| File | Usage |
|------|-------|
| `src/erk/core/plan_context_provider.py` | Class definition + constructor call |
| `src/erk/core/commit_message_generator.py` | TYPE_CHECKING import, type annotations |
| `src/erk/cli/commands/pr/shared.py` | Import, function signatures |
| `src/erk/cli/commands/pr/submit_pipeline.py` | Import, dataclass field, function signatures |
| `src/erk/cli/commands/pr/rewrite_cmd.py` | Import (PlanContextProvider only) |
| `src/erk/cli/commands/exec/scripts/get_pr_context.py` | Import (PlanContextProvider only) |
| `src/erk/cli/commands/exec/scripts/set_pr_description.py` | Import (PlanContextProvider only) |
| `src/erk/cli/commands/exec/scripts/update_pr_description.py` | Import (PlanContextProvider only) |
| `tests/core/test_plan_context_provider.py` | Import, test assertions, factory helpers |
| `tests/core/test_commit_message_generator.py` | Import, test data construction |
| `tests/unit/cli/commands/pr/test_shared.py` | Import, helper function |
| `tests/unit/cli/commands/pr/submit_pipeline/test_extract_diff_and_fetch_plan_context.py` | Import, type annotations |
| `tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py` | Import, test data, docstrings |

**Approach:** Use `rename-swarm` or find-and-replace `PlanContext` → `PrContext` across all 13 files. Also update the class docstring from "Context from an erk plan" to "Context from an erk PR".

**Note:** `PlanContextProvider` is NOT renamed in this node — that's a separate concern (the provider _provides_ context, the class name describes its role). Only the `PlanContext` dataclass is renamed.

## Node 1.6: Rename `validate_plan_title()` → `validate_pr_title()`

**Definition site:** `packages/erk-shared/src/erk_shared/naming.py:134`

**3 files with usages:**

| File | Usage |
|------|-------|
| `packages/erk-shared/src/erk_shared/naming.py` | Function definition + docstring references |
| `src/erk/cli/commands/exec/scripts/plan_save.py` | Import + call site |
| `tests/core/utils/test_naming.py` | Import + 8 test function names + calls |

**Approach:** Rename the function and update all import sites, call sites, test function names (e.g., `test_validate_plan_title_valid` → `test_validate_pr_title_valid`), and docstring references.

## Implementation Steps

1. **Rename `PlanContext` → `PrContext`** across all 13 files
   - Rename class and update docstring in `plan_context_provider.py`
   - Update all imports and type annotations
   - Update test helpers and assertions

2. **Rename `validate_plan_title()` → `validate_pr_title()`** across 3 files
   - Rename function and update docstring in `naming.py`
   - Update import and call in `plan_save.py`
   - Rename test functions and update calls in `test_naming.py`

3. **Update docstrings/comments** that reference old names in definition files only (following PR #9319 pattern)

## Verification

1. Run `ty` for type checking
2. Run `ruff check` for lint
3. Run `pytest tests/core/test_plan_context_provider.py tests/core/test_commit_message_generator.py tests/core/utils/test_naming.py tests/unit/cli/commands/pr/ -x` for targeted tests
4. Run full unit test suite to catch any missed references
