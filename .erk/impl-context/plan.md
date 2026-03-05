# Rename "sync" to "teleport" for remote→local branch operations

## Context

Claude Code uses "teleport" terminology for bringing a remote branch to local. Erk currently calls this pattern "sync" in the three-step sequence (fetch → checkout → pull_rebase). Renaming aligns erk's vocabulary with Claude Code.

**Scope:** Terminology-only rename for the remote→local branch pattern. Does NOT touch:
- `reconcile-with-remote` (stays as-is — it handles conflict resolution)
- `erk docs sync`, `erk artifact sync`, `pr_sync_commit` (different concepts)
- `plan_update.py` "Branch synced" (local→remote push, opposite direction)
- `wt list` sync status column (ahead/behind display, different concept)

## Changes

### 1. `src/erk/cli/commands/exec/scripts/setup_impl_from_pr.py`

- Rename `needs_sync` → `needs_teleport`
- Update docstring: "Fetch, checkout, and **teleport** a planned-PR plan branch"
- Update comments: "just sync" → "just teleport", "no sync needed" → "no teleport needed"
- Update user-facing message: "syncing with remote..." → "teleporting from remote..."
- Update error message: "Failed to sync branch" → "Failed to teleport branch"

### 2. `docs/learned/planning/planned-pr-branch-sync.md`

- Rename file to `planned-pr-branch-teleport.md`
- Update title: "Planned PR Branch Teleport"
- Update frontmatter read_when/tripwires to use "teleport" terminology
- Replace "Three-Step Sync Sequence" → "Three-Step Teleport Sequence"
- Update all references to "sync" in the body (where they mean remote→local)

### 3. Update references to the renamed doc

- `docs/learned/planning/` — any file linking to `planned-pr-branch-sync.md`
- Frontmatter/index references if auto-generated

### 4. `tests/unit/cli/commands/exec/scripts/test_setup_impl_from_pr.py`

- Update comment on line 104: "Planned-PR plan branch sync tests" → "teleport tests"
- Update comment on line 174: "syncs with remote" → "teleports from remote"

## Verification

1. Run `ruff check` and `ty check` to verify no broken references
2. Run `pytest tests/unit/cli/commands/exec/scripts/test_setup_impl_from_pr.py` to verify tests pass
3. Run `erk docs sync` to regenerate index if file was renamed
4. Grep for remaining "sync" references in setup_impl_from_pr to confirm none were missed
