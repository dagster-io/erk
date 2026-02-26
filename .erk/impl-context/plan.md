# Plan: Rewrite impl-context and impl-folder-lifecycle docs (O#8197 nodes 4.1 + 4.2)

**Objective:** #8197 — Consolidate .impl/ into branch-scoped .erk/impl-context/\<branch\>/
**Nodes:** 4.1 (rewrite-impl-context-doc) + 4.2 (rewrite-lifecycle-doc)

## Context

Phases 1-3 of objective #8197 migrated the codebase from a dual-directory system (`.impl/` + `.erk/impl-context/`) to a unified branch-scoped directory at `.erk/impl-context/<branch>/`. Two key documentation files are now stale and describe the old architecture:

1. **`docs/learned/planning/impl-context.md`** — Still describes `.erk/impl-context/` as a "temporary staging directory" with a copy-to-`.impl/` lifecycle
2. **`docs/learned/architecture/impl-folder-lifecycle.md`** — Still documents two separate folders with a `cp -r` copy step

Both need complete rewrites to describe the single-directory lifecycle.

## Changes

### 1. Rewrite `docs/learned/planning/impl-context.md`

**Current state:** Describes `.erk/impl-context/` as staging → copy to `.impl/` → cleanup. References "Step 2d convergence point", deferred cleanup, and the old five-setup-path architecture.

**New content should cover:**

- **Title**: Update to "Branch-Scoped Implementation Directories" (or similar — no longer just "staging")
- **Overview**: `.erk/impl-context/<branch>/` is the single directory for all implementation state. Branch-scoped via `get_impl_dir()`. Gitignored locally, force-committed when shipping to remote.
- **Frontmatter**: Update `read_when` triggers and `tripwires` to reflect new architecture:
  - Remove tripwires about "Step 2d convergence point" (no longer exists as described)
  - Remove tripwires about copy step
  - Update tripwires about cleanup to reflect `git rm --cached` pattern
  - Keep tripwire about LBYL guard (still valid)
- **Lifecycle section** — Three scenarios:
  1. **Plan save (shipping to remote)**: `build_impl_context_files()` creates content → committed to branch via `git add -f` → visible in PR diff
  2. **Local implementation**: `create_impl_folder(branch_name=...)` creates `.erk/impl-context/<branch>/plan.md` + `ref.json` → gitignored, invisible to git → read by implementation agent
  3. **Remote implementation**: Branch checkout has committed files → `git rm --cached -rf .erk/impl-context/` untracks but keeps on disk → implementation agent reads directly → no copy step
- **Key functions**: Reference `get_impl_dir()`, `resolve_impl_dir()`, `create_impl_folder()` from `impl_folder.py` and `create_impl_context()`, `build_impl_context_files()` from `impl_context.py`
- **Cleanup section**: Worktree reuse via `cleanup_worktree_artifacts()` removes entire `.erk/impl-context/` tree
- **Related docs**: Update links (remove references to draft-pr-plan-backend.md etc. which don't exist)

**Source files to reference for accuracy:**
- `packages/erk-shared/src/erk_shared/impl_folder.py` — `get_impl_dir()`, `resolve_impl_dir()`, `IMPL_DIR_RELATIVE`
- `packages/erk-shared/src/erk_shared/impl_context.py` — `create_impl_context()`, `build_impl_context_files()`
- `src/erk/cli/commands/exec/scripts/plan_save.py` — plan save flow
- `src/erk/cli/commands/exec/scripts/cleanup_impl_context.py` — cleanup flow
- `src/erk/cli/commands/slot/common.py:494-515` — `cleanup_worktree_artifacts()`

### 2. Rewrite `docs/learned/architecture/impl-folder-lifecycle.md`

**Current state:** Documents two folders (`.erk/impl-context/` committed + `.impl/` local) with a `cp -r` copy step. 56 lines, entirely stale.

**New content should cover:**

- **Title**: Keep "Implementation Folder Lifecycle" (still accurate)
- **Frontmatter**: Update `read_when` to remove `.impl/` references
- **Single directory**: `.erk/impl-context/<branch>/` — properties table (created by, purpose, contains, lifecycle, committed status varies by context)
- **Branch scoping**: Explain `_sanitize_branch_for_dirname()` (`/` → `--`)
- **Resolution strategy**: Document `resolve_impl_dir()` 4-step discovery (branch-scoped → legacy `.impl/` → discovery → None)
- **Git visibility lifecycle**: Gitignored locally → `git add -f` to ship → `git rm --cached` to untrack on remote
- **Why branch-scoped**: Branch switching never leaves stale artifacts (each branch has its own directory)
- **Related docs**: Link to impl-context.md (planning), impl-context-api.md (architecture)

### 3. Update `docs/learned/architecture/impl-context-api.md` (minor)

**Current state:** References "Unlike `.impl/` (ephemeral, local, never committed)" in the header. The three-function API documentation is still accurate but the framing needs updating.

**Changes:**
- Update opening paragraph to remove `.impl/` contrast
- Update "Two-Phase Deferred Cleanup" section to describe `git rm --cached` instead of `git rm -rf`
- Update "Related Documentation" links

## Verification

1. Read all three modified files and verify no references to `.impl/` as a working directory remain
2. Verify frontmatter `read_when` and `tripwires` are internally consistent
3. Grep modified files for "\.impl/" to confirm no stale references
4. Check that all referenced source file paths are accurate (impl_folder.py, impl_context.py, etc.)
