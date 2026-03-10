# Plan: Semantic rename of plan_store ABC to ManagedPrBackend

Part of Objective #9109, Node 5.1

## Context

The plan_store ABC (`PlanBackend`) is the provider-agnostic abstraction for erk's structured PR document layer. As part of the plan→pr terminology rename (objective #9109), the user decided this ABC deserves a **semantic rename** rather than a mechanical one. `PlanBackend` becomes `ManagedPrBackend` to clearly communicate that this layer manages erk's structured draft PRs (with metadata blocks, session tracking, lifecycle stages) — not raw GitHub PRs.

Methods use prefixed names (`get_managed_pr()`, `create_managed_pr()`) to avoid confusion with raw GitHub PR operations. Generic operations (`add_comment()`, `update_metadata()`) keep their current names since the class name provides sufficient context.

## Scope

**In scope (4 core files + 10 importers of PlanBackend):**
- ABC class + method renames in `backend.py`
- Implementation class + method renames in `planned_pr.py`
- Parameter renames (`plan_id` → `pr_number`) in ABC and implementation
- Update all 10 files that import `PlanBackend`
- Update `planned_pr_lifecycle.py` and `plan_workflow.py` docstrings/comments
- Update `conversion.py` docstrings referencing "plan"
- Update `__init__.py` docstring

**Out of scope (separate future nodes):**
- Type renames (`Plan`, `PlanNotFound`, `PlanQuery`, `CreatePlanResult`, `PlanState`) — 69 importers, needs its own PR
- Package directory rename (`plan_store/` → something else) — too disruptive for one PR
- `plan-header` metadata block key — this is a serialized format identifier, not a concept name

## Renames

### Class Names
| Current | New |
|---------|-----|
| `PlanBackend` | `ManagedPrBackend` |
| `PlannedPRBackend` | `GitHubManagedPrBackend` |

### Method Names (ABC + implementation)
| Current | New | Rationale |
|---------|-----|-----------|
| `get_plan()` | `get_managed_pr()` | Core CRUD |
| `list_plans()` | `list_managed_prs()` | Core CRUD |
| `create_plan()` | `create_managed_pr()` | Core CRUD |
| `close_plan()` | `close_managed_pr()` | Core CRUD |
| `update_plan_content()` | `update_managed_pr_content()` | Scoped update |
| `update_plan_title()` | `update_managed_pr_title()` | Scoped update |
| `get_plan_for_branch()` | `get_managed_pr_for_branch()` | Branch resolution |
| `resolve_plan_id_for_branch()` | `resolve_pr_number_for_branch()` | Branch resolution |
| `find_sessions_for_plan()` | `find_sessions_for_managed_pr()` | Session discovery |
| `ensure_plan_header()` | `ensure_plan_header()` | **No change** — plan-header is a metadata block identifier |
| `get_provider_name()` | `get_provider_name()` | **No change** — generic |
| `get_metadata_field()` | `get_metadata_field()` | **No change** — generic |
| `get_all_metadata_fields()` | `get_all_metadata_fields()` | **No change** — generic |
| `get_comments()` | `get_comments()` | **No change** — generic |
| `update_metadata()` | `update_metadata()` | **No change** — generic |
| `add_comment()` | `add_comment()` | **No change** — generic |
| `add_label()` | `add_label()` | **No change** — generic |
| `post_event()` | `post_event()` | **No change** — generic |

### Parameter Renames
| Current | New | On Methods |
|---------|-----|------------|
| `plan_id: str` | `pr_number: str` | All methods that accept it (13 methods on ABC) |

## Files to Modify

### Core files (4)
1. **`packages/erk-shared/src/erk_shared/plan_store/backend.py`** — ABC class rename, method renames, param renames, docstring updates
2. **`packages/erk-shared/src/erk_shared/plan_store/planned_pr.py`** — Implementation class rename, method renames, param renames
3. **`packages/erk-shared/src/erk_shared/plan_store/planned_pr_lifecycle.py`** — Docstring updates only (references PlannedPRBackend.create_plan)
4. **`packages/erk-shared/src/erk_shared/plan_store/conversion.py`** — Docstring updates only

### Package files (1)
5. **`packages/erk-shared/src/erk_shared/plan_store/__init__.py`** — Update docstring references

### Importers of PlanBackend (10 files)
6. `src/erk/core/context.py`
7. `src/erk/core/plan_context_provider.py`
8. `src/erk/cli/commands/pr/metadata_helpers.py`
9. `packages/erk-shared/src/erk_shared/context/helpers.py`
10. `packages/erk-shared/src/erk_shared/context/context.py`
11. `packages/erk-shared/src/erk_shared/learn/tracking.py`
12. `tests/test_utils/test_context.py`
13. `tests/fakes/tests/shared_context.py`
14. `tests/unit/plan_store/test_plan_backend_interface.py`

### Callers of renamed methods (~30+ files)
15. All files that call `backend.get_plan()`, `backend.create_plan()`, `backend.close_plan()`, etc. need method name updates. These are the same ~30 files from the explore agent's analysis. Use grep to find all call sites for each renamed method.

### plan_workflow.py
16. **`packages/erk-shared/src/erk_shared/plan_workflow.py`** — Docstring/comment updates (references "plan" in context of the backend)

## Implementation Phases

### Phase A: Rename ABC and implementation classes + methods
1. Rename `PlanBackend` → `ManagedPrBackend` in `backend.py`
2. Rename all methods per the table above in `backend.py`
3. Rename `plan_id` → `pr_number` parameter on all methods in `backend.py`
4. Rename `PlannedPRBackend` → `GitHubManagedPrBackend` in `planned_pr.py`
5. Update all method overrides in `planned_pr.py` to match new ABC signatures
6. Update `__init__.py` docstring

### Phase B: Update all importers and call sites
7. Update all 10 files importing `PlanBackend` → `ManagedPrBackend`
8. Grep for every renamed method and update call sites
9. Update `planned_pr_lifecycle.py` and `conversion.py` docstrings

### Phase C: Update tests
10. Update test imports and assertions in `test_plan_backend_interface.py`
11. Update any test files that reference renamed methods

## Verification

1. Run `ty` for type checking — all renamed methods and imports must resolve
2. Run `ruff` for lint
3. Run `pytest tests/unit/plan_store/` — plan_store unit tests
4. Run `pytest tests/` — full test suite to catch any missed call sites
5. Grep for leftover references: `grep -r "PlanBackend\|PlannedPRBackend\|\.get_plan(\|\.create_plan(\|\.close_plan(\|\.list_plans(\|\.update_plan_content(\|\.update_plan_title(\|\.get_plan_for_branch(\|\.resolve_plan_id_for_branch(\|\.find_sessions_for_plan(" --include="*.py"` (should only match comments/docstrings in non-plan_store files, and the type names Plan/PlanNotFound which are out of scope)
