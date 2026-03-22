# Plan: Rename plans_repo_labels to pr_repo_labels

**Part of Objective #9318, Node 5.7**

## Context

This is the final node (30 of 30) in the plan-to-PR terminology rename objective. All other nodes have been completed across PRs #9319, #9340, #9352, #9365, #9372, #9379, #9385, and #9390. The remaining work is renaming `plans_repo_labels` → `pr_repo_labels` in the health check module, init command, and associated tests.

The naming convention follows the established pattern: `plan` → `pr` (singular), consistent with all prior renames (e.g., `plan_store` → `pr_store`, `plan_backend` → `pr_backend`).

## Changes

### 1. Rename health check module file

- **Rename** `src/erk/core/health_checks/plans_repo_labels.py` → `pr_repo_labels.py`
- Inside the file:
  - Function: `check_plans_repo_labels()` → `check_pr_repo_labels()`
  - Parameter: `plans_repo: str` → `pr_repo: str`
  - Check result name string: `"plans-repo-labels"` → `"pr-repo-labels"` (lines 47, 54)
  - Docstring/comments: update "plans repository" → "PR repository"

### 2. Update health checks `__init__.py`

**File:** `src/erk/core/health_checks/__init__.py`
- Line 25 docstring: `plans_repo_labels - check_plans_repo_labels` → `pr_repo_labels - check_pr_repo_labels`
- Line 61 import: update module path and function name
- Line 138 comment: `"Check plans_repo labels"` → `"Check pr_repo labels"`
- Line 148 function call: `check_plans_repo_labels(...)` → `check_pr_repo_labels(...)`

### 3. Rename functions in init/main.py

**File:** `src/erk/cli/commands/init/main.py`
- `create_plans_repo_labels()` → `create_pr_repo_labels()` (line 324)
- `offer_plans_repo_label_setup()` → `offer_pr_repo_label_setup()` (line 352)
- Parameter: `plans_repo: str` → `pr_repo: str` in both functions
- All internal references to `plans_repo` variable → `pr_repo`
- Line 665 comment: `"Check if plans_repo is configured"` → `"Check if pr_repo is configured"`
- Line 670 call site: update function name

### 4. Rename test files and update contents

**Rename** `tests/unit/core/test_health_checks_plans_repo_labels.py` → `test_health_checks_pr_repo_labels.py`
- Update import path and function name
- Update all `plans_repo=` keyword args → `pr_repo=`
- Update assertion: `result.name == "plans-repo-labels"` → `"pr-repo-labels"`
- Update docstrings: "plans repository" → "PR repository"

**Rename** `tests/unit/cli/commands/init/test_create_plans_repo_labels.py` → `test_create_pr_repo_labels.py`
- Update import and function name references
- Update all `plans_repo=` keyword args → `pr_repo=`
- Update docstrings: "plans repository" → "PR repository"

### 5. Update documentation references

- `docs/user/external-plans-repo.md` line 71: `"plans-repo-labels"` → `"pr-repo-labels"`
- `docs/learned/configuration/issues-repo.md` line 78: `"plans-repo-labels"` → `"pr-repo-labels"`
- CHANGELOG.md line 1215: leave as-is (historical entry)

## Files Modified (Summary)

| File | Action |
|------|--------|
| `src/erk/core/health_checks/plans_repo_labels.py` | Rename to `pr_repo_labels.py` + update contents |
| `src/erk/core/health_checks/__init__.py` | Update import, docstring, call site |
| `src/erk/cli/commands/init/main.py` | Rename 3 functions + parameter names |
| `tests/unit/core/test_health_checks_plans_repo_labels.py` | Rename to `test_health_checks_pr_repo_labels.py` + update |
| `tests/unit/cli/commands/init/test_create_plans_repo_labels.py` | Rename to `test_create_pr_repo_labels.py` + update |
| `docs/user/external-plans-repo.md` | Update check name string |
| `docs/learned/configuration/issues-repo.md` | Update check name string |

## Verification

1. Run health check tests: `uv run pytest tests/unit/core/test_health_checks_pr_repo_labels.py -v`
2. Run init tests: `uv run pytest tests/unit/cli/commands/init/test_create_pr_repo_labels.py -v`
3. Run type checker: `uv run ty check src/erk/core/health_checks/pr_repo_labels.py src/erk/cli/commands/init/main.py`
4. Grep for any remaining `plans_repo_labels` or `check_plans_repo_labels` references
5. Run `uv run ruff check` for lint
