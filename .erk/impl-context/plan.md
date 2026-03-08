# Plan: Centralize repo resolution infrastructure

**Part of Objective #8832, Node 2.3: discover-repo-refactor**

## Context

The `resolve_owner_repo()`, `get_remote_github()`, and `repo_option` utilities currently live in `src/erk/cli/commands/pr/repo_resolution.py` — a PR-specific location. Phase 3 commands (pr create, pr dispatch, launch, objective plan) and the in-progress node 2.2 (objective commands) all need these same utilities. The codespace module already has a duplicate `_resolve_owner_repo()` in `src/erk/cli/commands/codespace/setup_cmd.py`, confirming the need for centralization.

This refactoring moves the repo resolution infrastructure to a shared location so all command groups can adopt the unified single-codepath pattern without importing from the PR subpackage.

## Implementation

### Step 1: Create shared repo resolution module

Create `src/erk/cli/repo_resolution.py` (at CLI level, not under commands/pr/) by moving the contents from `src/erk/cli/commands/pr/repo_resolution.py`.

**Source:** `src/erk/cli/commands/pr/repo_resolution.py` (move all 3 exports: `resolve_owner_repo`, `get_remote_github`, `repo_option`)

**Target:** `src/erk/cli/repo_resolution.py`

### Step 2: Update PR command imports (6 files)

Update all PR read commands to import from the new location:

- `src/erk/cli/commands/pr/log_cmd.py`
- `src/erk/cli/commands/pr/view_cmd.py`
- `src/erk/cli/commands/pr/check_cmd.py`
- `src/erk/cli/commands/pr/close_cmd.py`
- `src/erk/cli/commands/pr/list_cmd.py`
- `src/erk/cli/commands/pr/duplicate_check_cmd.py`

Change: `from erk.cli.commands.pr.repo_resolution import` → `from erk.cli.repo_resolution import`

### Step 3: Make old module a re-export shim (temporary)

Replace `src/erk/cli/commands/pr/repo_resolution.py` with re-exports from the new location, for any external consumers. Actually — per erk conventions ("No backwards compatibility: Break and migrate immediately, no legacy shims"), delete the old module entirely after updating all imports.

### Step 4: Eliminate codespace duplicate

Update `src/erk/cli/commands/codespace/setup_cmd.py` to use the shared `resolve_owner_repo` instead of its local `_resolve_owner_repo`. The local version uses `ctx.repo_info` (a `RepoInfo` with `owner`/`name`) while the shared version uses `ctx.repo.github` (a `GitHubRepoId` with `owner`/`repo`). Adapt the codespace command to use the shared version's interface.

### Step 5: Update test imports

Update any tests that import from the old location:

- `tests/unit/cli/commands/codespace/test_setup_cmd.py` (if it tests `_resolve_owner_repo`)

### Step 6: Delete old module

Remove `src/erk/cli/commands/pr/repo_resolution.py` entirely.

## Files to modify

| File | Action |
|------|--------|
| `src/erk/cli/repo_resolution.py` | **Create** — moved from pr/repo_resolution.py |
| `src/erk/cli/commands/pr/repo_resolution.py` | **Delete** |
| `src/erk/cli/commands/pr/log_cmd.py` | Update import |
| `src/erk/cli/commands/pr/view_cmd.py` | Update import |
| `src/erk/cli/commands/pr/check_cmd.py` | Update import |
| `src/erk/cli/commands/pr/close_cmd.py` | Update import |
| `src/erk/cli/commands/pr/list_cmd.py` | Update import |
| `src/erk/cli/commands/pr/duplicate_check_cmd.py` | Update import |
| `src/erk/cli/commands/codespace/setup_cmd.py` | Replace `_resolve_owner_repo` with shared import |
| `tests/unit/cli/commands/codespace/test_setup_cmd.py` | Update if needed |

## Reuse

- `resolve_owner_repo()` from `src/erk/cli/commands/pr/repo_resolution.py` — move as-is
- `get_remote_github()` from same — move as-is
- `repo_option` Click decorator from same — move as-is

## Verification

1. `ruff check src/erk/cli/repo_resolution.py` — no lint errors in new module
2. `ty check src/erk/` — no type errors from import changes
3. `pytest tests/commands/pr/` — all PR command tests pass
4. `pytest tests/unit/cli/commands/codespace/` — codespace tests pass
5. `erk pr list` — works from inside a git repo
6. `erk pr list --repo dagster-io/erk` — works from outside a git repo (if auth available)
7. Grep for old import path to confirm zero remaining references: `grep -r "from erk.cli.commands.pr.repo_resolution" src/ tests/`
