# Plan: Move Git Gateway to gateway/git/ (Phase 1 of #5930)

**Part of Objective #5930, Step 1.1**

## Goal

Move `packages/erk-shared/src/erk_shared/git/` to `packages/erk-shared/src/erk_shared/gateway/git/` and update all import sites in a single atomic PR. No backward compatibility shims.

## Scope

**Files to move (19 total):**
- Main: `__init__.py`, `abc.py`, `real.py`, `fake.py`, `dry_run.py`, `printing.py`, `lock.py`
- Sub-gateway `branch_ops/`: 6 files (abc, real, fake, dry_run, printing, __init__)
- Sub-gateway `worktree/`: 6 files (abc, real, fake, dry_run, printing, __init__)

**Import sites to update:** ~465 files, ~1,170 import occurrences

## Implementation Phases

### Phase 1: Move Files

1. Create target directories:
   ```bash
   mkdir -p packages/erk-shared/src/erk_shared/gateway/git/{branch_ops,worktree}
   ```

2. Move all files with `git mv` (preserves history):
   - Main gateway files (7)
   - `worktree/` sub-gateway (6)
   - `branch_ops/` sub-gateway (6)

3. Remove empty old directory:
   ```bash
   rm -rf packages/erk-shared/src/erk_shared/git/
   ```

### Phase 2: Update Internal Imports

Fix imports within the moved files themselves (they reference each other):

| File | Update Pattern |
|------|----------------|
| `gateway/git/abc.py` | `erk_shared.git.worktree` -> `erk_shared.gateway.git.worktree` |
| `gateway/git/real.py` | All `erk_shared.git.*` -> `erk_shared.gateway.git.*` |
| `gateway/git/fake.py` | All `erk_shared.git.*` -> `erk_shared.gateway.git.*` |
| `gateway/git/dry_run.py` | All `erk_shared.git.*` -> `erk_shared.gateway.git.*` |
| `gateway/git/printing.py` | All `erk_shared.git.*` -> `erk_shared.gateway.git.*` |
| `gateway/git/worktree/*.py` | All self-references |
| `gateway/git/branch_ops/*.py` | All self-references |

### Phase 3: Update External Imports

Bulk find-replace across codebase (process longer paths first):

1. `from erk_shared.git.worktree.` -> `from erk_shared.gateway.git.worktree.`
2. `from erk_shared.git.branch_ops.` -> `from erk_shared.gateway.git.branch_ops.`
3. `from erk_shared.git.` -> `from erk_shared.gateway.git.`
4. `from erk_shared.git import` -> `from erk_shared.gateway.git import`

**Key files to update:**
- `packages/erk-shared/src/erk_shared/context/*.py`
- `packages/erk-shared/src/erk_shared/branch_manager/*.py`
- `packages/erk-shared/src/erk_shared/gateway/graphite/*.py` (cross-gateway import)
- `src/erk/core/context.py`
- `src/erk/cli/**/*.py`
- All test files (~280 files)

### Phase 4: Update Documentation

Update import examples in:
- `docs/learned/architecture/gateway-abc-implementation.md`
- `docs/learned/architecture/erk-architecture.md`
- Other docs referencing `erk_shared.git`

## Critical Files

- `packages/erk-shared/src/erk_shared/git/abc.py` - Most widely imported (Git, WorktreeInfo)
- `packages/erk-shared/src/erk_shared/git/fake.py` - Used in ~178 test files
- `packages/erk-shared/src/erk_shared/gateway/graphite/abc.py` - Cross-gateway import to update
- `packages/erk-shared/src/erk_shared/context/context.py` - Central context definition

## Edge Cases

1. **TYPE_CHECKING imports** - Must update conditional imports under `if TYPE_CHECKING:`
2. **Runtime imports** - Some files use delayed imports to avoid circular deps (e.g., fake.py line 862)
3. **Docstrings** - Update import examples in `__init__.py` docstrings

## Verification

```bash
# Verify no old imports remain
rg "from erk_shared\.git\." --type py
rg "from erk_shared\.git import" --type py

# Verify new imports work
python -c "from erk_shared.gateway.git.abc import Git; print('OK')"

# Run CI
make all-ci
```

**Success criteria:** `make all-ci` passes, no imports from `erk_shared.git` exist.

## Commit Message

```
Move git gateway to gateway/git/ (Phase 1 of #5930)

Consolidates git gateway into erk_shared/gateway/git/ alongside
existing gateways (graphite, time, etc.).

- Move 19 files from erk_shared/git/ to erk_shared/gateway/git/
- Update ~465 import sites across all packages
- Delete old erk_shared/git/ directory
- No backward compatibility shims (clean break)
```