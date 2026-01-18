# Plan: Delete erk-sh-bootstrap Package

## Context

`erk-sh-bootstrap` was Layer 2 of the 3-layer shell integration architecture. With shell integration removed in PR #5151, this package is no longer needed.

**What erk-sh-bootstrap did:**
- Zero-dependency PyPI package enabling `uvx erk-sh-bootstrap` command
- Found project-local erk in `.venv/bin/erk` and delegated to it via `os.execv()`
- Published separately to PyPI as version 1.0.0

## Changes Required

### Phase 1: Delete Package Directory
- **DELETE**: `packages/erk-sh-bootstrap/` (entire directory)
  - `src/erk_sh_bootstrap/cli.py` - Main implementation
  - `src/erk_sh_bootstrap/__init__.py` - Module init
  - `tests/test_cli.py` - Package tests
  - `pyproject.toml` - Package config
  - `README.md` - Package docs

### Phase 2: Update Root Configuration
- **EDIT**: `pyproject.toml`
  - Remove `"packages/erk-sh-bootstrap"` from `tool.uv.workspace.members`
  - Remove `erk-sh-bootstrap = { workspace = true }` from `tool.uv.sources`
  - Remove `"packages/erk-sh-bootstrap/tests"` from `tool.pytest.ini_options.testpaths`

### Phase 3: Regenerate Lock File
- **RUN**: `uv lock` to update `uv.lock` (removes erk-sh-bootstrap entries automatically)

### Phase 4: Update Documentation
- **DELETE**: `docs/learned/architecture/shell-integration-architecture.md` (entire file - documents deleted shell integration)
- **EDIT**: `docs/learned/glossary.md` - Remove "erk-sh-bootstrap" entry (lines 217-231)
- **EDIT**: `docs/learned/architecture/index.md` - Remove reference to shell-integration-architecture.md
- **RUN**: `erk docs sync` to regenerate tripwires.md and index files

### Phase 5: CHANGELOG Entry
- No CHANGELOG modification needed (this is cleanup, not a user-facing change)

## Files Summary

**Delete:**
- `packages/erk-sh-bootstrap/` (entire directory)
- `docs/learned/architecture/shell-integration-architecture.md`

**Edit:**
- `pyproject.toml` - Remove workspace member and source
- `docs/learned/glossary.md` - Remove glossary entry
- `docs/learned/architecture/index.md` - Remove doc reference

**Regenerate:**
- `uv.lock` - Via `uv lock`
- `docs/learned/tripwires.md` - Via `erk docs sync`

## Verification

1. Run `uv lock` successfully
2. Run `make fast-ci` - all tests pass
3. Verify `packages/erk-sh-bootstrap/` no longer exists
4. Verify no remaining references to `erk-sh-bootstrap` in codebase