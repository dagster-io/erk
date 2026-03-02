# Auto-Remove Orphaned Artifacts During `erk artifact sync`

## Context

When erk removes an artifact from its bundle in a new version (renamed, deleted, or capability dropped), the old file/directory is left behind in target repos because `sync_artifacts()` is additive-only. This is especially problematic for **skills** which lack namespace isolation — they live at `.claude/skills/<name>/` alongside user-created skills, so directory walking alone can't distinguish erk-owned from user-owned.

**Two gaps:**
1. `find_orphaned_artifacts()` only detects orphaned *files within* currently-bundled skill/agent directories. It cannot detect **entire directories** removed from the registry (e.g., if `foo-skill` was dropped, `.claude/skills/foo-skill/` is never checked).
2. `sync_artifacts()` never calls orphan detection or removal — it only adds/updates.

**Solution:** Use `state.toml` as the ownership ledger. It records every artifact erk synced. Compare old state keys (before sync) with new synced keys (after sync). Keys in old but not new are orphaned and safe to remove. This works for skills without namespacing because user-created skills never appear in state.toml.

## Implementation

### 1. Add `artifacts_removed` field to `SyncResult`

**File:** `src/erk/artifacts/sync.py` (line 24-30)

Add `artifacts_removed: int` to the frozen dataclass. Update all 4 construction sites in `sync.py` (lines 548, 673, 680, 780) to include `artifacts_removed=0` (or the computed value at line 780).

Update 2 test mock constructions in `tests/commands/setup/init/test_hooks.py` (lines 180, 216).

### 2. Add `_key_to_orphaned_path()` helper

**File:** `src/erk/artifacts/sync.py`

New frozen dataclass `_OrphanedPath` with `path: Path` and `is_directory: bool`.

New function `_key_to_orphaned_path(key: str, project_dir: Path) -> _OrphanedPath | None` that maps state.toml keys to filesystem paths:

| Key prefix | Path | Type |
|---|---|---|
| `skills/X` | `.claude/skills/X/` | directory |
| `agents/X` | `.claude/agents/X/` | directory |
| `agents/X.md` | `.claude/agents/X.md` | file |
| `commands/erk/X` | `.claude/commands/erk/X` | file |
| `workflows/X` | `.github/workflows/X` | file |
| `actions/X` | `.github/actions/X/` | directory |
| `reviews/X` | `.erk/reviews/X` | file |
| `hooks/*` | `None` (skip) | — |

### 3. Add `_remove_orphaned_artifacts()` function

**File:** `src/erk/artifacts/sync.py`

```python
def _remove_orphaned_artifacts(
    project_dir: Path,
    *,
    old_keys: frozenset[str],
    new_keys: frozenset[str],
) -> int:
```

- Computes `orphaned_keys = old_keys - new_keys`
- Iterates sorted keys, calls `_key_to_orphaned_path()` for each
- LBYL: checks `.exists()` before `rmtree`/`unlink`
- For files: also removes empty parent directory (e.g., `commands/erk/system/` after last file removed)
- Returns count of artifacts actually removed

### 4. Wire cleanup into `sync_artifacts()`

**File:** `src/erk/artifacts/sync.py`, `sync_artifacts()` function

- Add `load_artifact_state` to the import from `erk.artifacts.state` (line 11)
- After line 688 (after early returns, before sync logic): load old state and compute `old_keys`
- After line 773 (after building `files` dict, before `save_artifact_state`): compute `new_keys`, call `_remove_orphaned_artifacts()`, capture count
- Pass `artifacts_removed` to `SyncResult` at line 780
- Enrich message: `f"Synced {total_copied} artifact files, removed {artifacts_removed} orphaned"` when `artifacts_removed > 0`

### 5. Update CLI output

**File:** `src/erk/cli/commands/artifact/sync_cmd.py` (line 50-53)

After the success message, add conditional output for removals:
```python
if result.artifacts_removed > 0:
    click.echo(
        click.style("  ", fg="yellow")
        + f"Removed {result.artifacts_removed} orphaned artifact(s)"
    )
```

### 6. Fix `find_orphaned_artifacts()` detection (Gap 1)

**File:** `src/erk/artifacts/artifact_health.py`

Add `_find_state_based_orphans()` function that:
- Loads state.toml via inline `from erk.artifacts.state import load_artifact_state`
- Builds the set of currently-bundled keys from `_get_bundled_by_type()` for all artifact types + command file enumeration
- Computes `orphaned_keys = saved_state_keys - current_keys`
- Filters out `hooks/` keys
- Checks each orphan exists on disk (LBYL)
- Returns `dict[str, list[str]]` in `OrphanCheckResult` format

Call this from `find_orphaned_artifacts()` (line 461) after existing orphan detection, merging results.

Note: uses inline import of `load_artifact_state` from `state.py` to avoid circular deps (sync.py already uses inline imports from artifact_health.py).

## Files to Modify

| File | Changes |
|---|---|
| `src/erk/artifacts/sync.py` | `SyncResult.artifacts_removed`, `_OrphanedPath`, `_key_to_orphaned_path()`, `_remove_orphaned_artifacts()`, wire into `sync_artifacts()` |
| `src/erk/artifacts/artifact_health.py` | `_find_state_based_orphans()`, call from `find_orphaned_artifacts()` |
| `src/erk/cli/commands/artifact/sync_cmd.py` | Report removal count |
| `tests/commands/setup/init/test_hooks.py` | Add `artifacts_removed=0` to 2 mock `SyncResult` constructions |

## New Test File

**File:** `tests/artifacts/test_orphan_cleanup.py`

Test cases (all use `tmp_path`, construct `ArtifactSyncConfig` with `sync_capabilities=False`):

1. **Removed skill directory cleaned up** — state.toml has `skills/old-skill`, bundle doesn't, sync removes the directory
2. **Removed command file cleaned up** — state.toml has `commands/erk/old-cmd.md`, bundle doesn't, sync removes the file
3. **Empty parent dir removed after file deletion** — `commands/erk/system/old.md` removed, empty `system/` dir cleaned up
4. **First sync (no old state) removes nothing** — no state.toml exists, `artifacts_removed == 0`
5. **Hooks never auto-removed** — state has `hooks/user-prompt-hook`, not in new keys, still `artifacts_removed == 0`
6. **Removed agent directory cleaned up** — state has `agents/old-agent`, bundle doesn't
7. **Already-deleted orphan not counted** — state has `skills/gone` but directory doesn't exist on disk, `artifacts_removed == 0`
8. **Removed workflow cleaned up** — state has `workflows/old.yml`, bundle doesn't

Add to existing `tests/artifacts/test_orphans.py`:

9. **`find_orphaned_artifacts` detects entirely-removed skill via state** — skill not in registry, but state.toml and disk both have it

## Verification

1. Run `devrun` with `pytest tests/artifacts/test_orphan_cleanup.py tests/artifacts/test_orphans.py -v`
2. Run `devrun` with `pytest tests/commands/setup/init/test_hooks.py -v` (verify mock updates)
3. Run `devrun` with `make fast-ci` for full suite
