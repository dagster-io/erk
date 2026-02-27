---
title: Impl-Folder Discovery Algorithm
read_when:
  - "working with .erk/impl-context/ directory resolution"
  - "debugging why a plan wasn't found during implementation setup"
  - "writing tests that use branch-scoped impl-context paths"
  - "understanding the difference between impl_folder.py and impl_context.py"
tripwires:
  - action: "calling resolve_impl_dir() without passing branch_name"
    warning: "Branch-scoped lookup is skipped when branch_name is None. Always pass the current branch to get deterministic resolution. Discovery fallback scans for ANY subdirectory with plan.md, which may find the wrong plan."
    score: 6
  - action: "writing tests for branch-scoped impl-context without configuring FakeGit"
    warning: "FakeGit must be configured with current_branches={tmp_path: BRANCH} for resolve_impl_dir() to find branch-scoped directories. Without this, the branch_name parameter is None and discovery falls through to scan."
    score: 5
---

# Impl-Folder Discovery Algorithm

The implementation directory (`resolve_impl_dir()`) uses a two-step discovery strategy: branch-scoped lookup followed by a scan fallback.

## `resolve_impl_dir()` Algorithm

**Location:** `packages/erk-shared/src/erk_shared/impl_folder.py`

```
resolve_impl_dir(base_path, branch_name=...)
  1. Branch-scoped lookup (if branch_name provided):
     → base_path / .erk/impl-context / sanitized(branch_name)
     → Return if exists
  2. Discovery scan:
     → Search .erk/impl-context/ for any subdir containing plan.md or progress.md
     → Return first match
  3. Return None
```

Branch-scoped paths always take priority over discovery scan results.

## Branch Name Sanitization

`_sanitize_branch_for_dirname()` converts branch names to safe directory names by replacing `/` with `--`:

| Branch Name             | Directory Name           |
| ----------------------- | ------------------------ |
| `main`                  | `main`                   |
| `feature/test-branch`   | `feature--test-branch`   |
| `plnd/consolidate-docs` | `plnd--consolidate-docs` |

## Module Ownership

| Module            | Responsibility            | Key Functions                                                                                        |
| ----------------- | ------------------------- | ---------------------------------------------------------------------------------------------------- |
| `impl_folder.py`  | Branch-scoped directories | `resolve_impl_dir()`, `get_impl_dir()`, `create_impl_folder()`, `save_plan_ref()`, `read_plan_ref()` |
| `impl_context.py` | Flat staging directory    | `create_impl_context()`, `remove_impl_context()`, `impl_context_exists()`                            |

**Key distinction:** `impl_folder.py` handles branch-scoped paths (`.erk/impl-context/<branch>/`) used during implementation. `impl_context.py` handles flat `.erk/impl-context/` used during draft-PR creation staging, which is cleaned up before implementation begins.

## Path Computation

`get_impl_dir()` is pure path computation with no filesystem I/O:

```
get_impl_dir(base_path, branch_name="feature/test")
→ base_path / ".erk/impl-context" / "feature--test"
```

## Test Patterns

Tests that exercise branch-scoped impl-context paths must configure `FakeGit` with the `current_branches` parameter.

<!-- Source: tests/unit/cli/commands/exec/scripts/test_impl_init.py, _make_ctx -->

See `_make_ctx()` in `tests/unit/cli/commands/exec/scripts/test_impl_init.py` for the test helper pattern that configures `FakeGit` with branch tracking.

Without `current_branches`, `resolve_impl_dir()` receives `branch_name=None` and falls through to discovery scan, which may find the wrong directory or return None.

## Known Gap: Dispatch Workflow Format Mismatch

Remote dispatch workflows may create flat `.erk/impl-context/` directories (via `impl_context.py`) rather than branch-scoped ones. When `resolve_impl_dir()` runs with a branch name, it checks the branch-scoped path first, misses the flat directory, then finds it via discovery scan. This works but is fragile — the scan returns the first match, which could be wrong if multiple flat directories exist.

## Related Documentation

- [Impl-Context Staging Directory](../planning/impl-context.md) — Lifecycle of the staging directory
- [Convergence Points Architecture](convergence-points.md) — How setup paths converge at cleanup
