# Plan: Rewrite impl-context and impl-folder-lifecycle docs (Objective #8197, Nodes 4.1 + 4.2)

## Context

Objective #8197 consolidated the old two-directory model (`.erk/impl-context/` staging + `.impl/` working dir) into a single `.erk/impl-context/` root with branch-scoped subdirectories. Phases 1-3 updated all source code, exec scripts, CLI commands, CI workflows, and tests. Phase 4 updates documentation.

Two docs are entirely organized around the now-obsolete two-directory model and need full rewrites:
- `docs/learned/planning/impl-context.md` — describes staging dir lifecycle
- `docs/learned/architecture/impl-folder-lifecycle.md` — describes the two-folder model

## Key Implementation Facts (from source code)

The current system has **two distinct uses** of `.erk/impl-context/`:

1. **Staging directory** (flat, committed): `impl_context.py` creates `.erk/impl-context/{plan.md, ref.json}` during plan-save for draft PRs. Committed to branch so PRs have visible diffs. Cleaned up by `erk exec cleanup-impl-context` before implementation.

2. **Branch-scoped impl directory** (local, never committed): `impl_folder.py` creates `.erk/impl-context/<sanitized-branch>/{plan.md, ref.json, ...}` during implementation setup. In `.gitignore`. Contains additional files: `run-info.json`, `local-run-state.json`.

Key API surface:
- `IMPL_DIR_RELATIVE = ".erk/impl-context"` (impl_folder.py)
- `get_impl_dir(base_path, branch_name=)` → pure path computation
- `resolve_impl_dir(base_path, branch_name=)` → 4-step discovery (branch-scoped → legacy `.impl/` → discovery scan → None)
- `create_impl_folder()` → creates branch-scoped dir with `plan.md`
- `save_plan_ref()` → writes `ref.json` (canonical name; `read_plan_ref()` also checks `plan-ref.json` and `issue.json` for legacy)
- `setup_impl_from_pr.py` replaced old `setup_impl_from_issue.py`
- `impl_type` completely removed from codebase

## Changes

### 1. Rewrite `docs/learned/planning/impl-context.md` (Node 4.1)

**Current state:** Describes the staging dir with stale references to `.impl/` copy step, `setup_impl_from_issue.py`, "five setup paths", and "Step 2d" convergence point.

**New content:** Rewrite to describe the staging directory lifecycle accurately:
- Title: keep "Impl-Context Staging Directory"
- Update `read_when` — remove the `.impl/` transfer bullet
- Update tripwires:
  - Remove references to `setup_impl_from_issue.py` (now `setup_impl_from_pr.py`)
  - Remove "Step 2d" references — cleanup is now `erk exec cleanup-impl-context`
  - Keep the PR-contains-impl-context tripwire (still valid)
  - Keep the `create_impl_context()` LBYL tripwire (still valid)
  - Keep the git pull --rebase after cleanup tripwire (still valid)
- Creation section: update to reflect current `plan_save.py` flow (same conceptually, verify source refs)
- Cleanup section: replace "Step 2d" / "five setup paths" with `erk exec cleanup-impl-context` (Python command that does shutil.rmtree + git add + commit + push)
- Remove references to `setup_impl_from_issue.py:202` — the file was renamed to `setup_impl_from_pr.py`
- Historical section: keep but update framing (the fix is now via a dedicated cleanup command, not a convergence step)
- Prevention section: update to match current API surface

### 2. Rewrite `docs/learned/architecture/impl-folder-lifecycle.md` (Node 4.2)

**Current state:** Entirely organized around the two-folder model with a comparison table, copy step section, and "Why Two Folders?" section. All content is stale.

**New content:** Complete rewrite to describe the unified single-root model:
- Title: "Implementation Directory Lifecycle" (singular)
- Update `read_when` — replace `.impl/` references with `.erk/impl-context/`
- Describe the two uses under one root:
  - Staging (flat, committed) — draft PR visibility
  - Branch-scoped (subdirectory, local) — implementation working dir
- Directory structure diagram showing both:
  ```
  .erk/impl-context/
  ├── plan.md          ← staging (committed, draft PR visibility)
  ├── ref.json         ← staging (committed)
  └── feature--task/   ← branch-scoped (local, .gitignore)
      ├── plan.md
      ├── ref.json
      ├── run-info.json
      └── local-run-state.json
  ```
- Full lifecycle: plan-save → staging committed → setup-impl reads staging + creates branch-scoped → cleanup-impl-context removes staging → implementation uses branch-scoped dir → PR submission reads ref.json
- Key modules: `impl_context.py` (staging) vs `impl_folder.py` (branch-scoped)
- Legacy compatibility: `resolve_impl_dir()` still checks `.impl/` as fallback
- Remove: comparison table, copy step, "Why Two Folders?"

### Files to modify

| File | Action |
|------|--------|
| `docs/learned/planning/impl-context.md` | Rewrite body + update frontmatter tripwires |
| `docs/learned/architecture/impl-folder-lifecycle.md` | Full rewrite |

### Source files for reference (read-only)

| File | Purpose |
|------|---------|
| `packages/erk-shared/src/erk_shared/impl_context.py` | Staging dir API |
| `packages/erk-shared/src/erk_shared/impl_folder.py` | Branch-scoped impl dir API |
| `src/erk/cli/commands/exec/scripts/cleanup_impl_context.py` | Cleanup command |
| `src/erk/cli/commands/exec/scripts/setup_impl_from_pr.py` | Setup from draft PR |
| `src/erk/cli/commands/exec/scripts/setup_impl.py` | Consolidated setup |

## Verification

1. Run `erk docs sync` to regenerate tripwires index from updated frontmatter
2. Grep `docs/learned/planning/impl-context.md` for any remaining `.impl/` references (should be zero except in legacy context)
3. Grep `docs/learned/architecture/impl-folder-lifecycle.md` for stale references
4. Verify frontmatter YAML is valid (no syntax errors)
