# Plan: Change uv tool install/upgrade instructions to local venv

## Summary

Replace user-facing instructions that reference `uv tool install` or `uv tool upgrade` with commands that interact with the local virtual environment (`uv sync` / `uv add`).

## Files to Modify

### 1. `src/erk/core/version_check.py` (line 54)
**Current**: `"   Update: uv tool upgrade erk"`
**Change to**: `"   Update: uv sync"`

### 2. `src/erk/core/health_checks.py` (line 129)
**Current**: `"Run 'uv tool upgrade erk' to update"`
**Change to**: `"Run 'uv sync' to update"`

### 3. `src/erk/cli/commands/init/main.py` (line 427)
**Current**: `"  Note: Install erk-statusline with: uv tool install erk-statusline"`
**Change to**: `"  Note: Install erk-statusline with: uv add erk-statusline && uv sync"`

### 4. `src/erk/cli/uvx_detection.py` (line 57)
**Current**: `"To fix this, install erk in uv's tools: uv tool install erk"`
**Change to**: `"To fix this, add erk to your project: uv add erk && uv sync"`

### 5. Test Updates

**`tests/unit/core/test_version_check.py` (line 71)**
**Current**: `assert "uv tool upgrade erk" in result`
**Change to**: `assert "uv sync" in result`

**`tests/unit/cli/test_uvx_detection.py` (line 112)**
**Current**: `assert "uv tool install" in message`
**Change to**: `assert "uv add erk" in message`

## Files NOT to Modify

The following files contain `uv tool install/upgrade` but should NOT be changed:
- **Makefile** - Development tooling for reinstalling erk-tools
- **CHANGELOG.md** - Historical documentation
- **CI workflows** (`.github/`)- CI-specific installation patterns
- **dev/install-test/** - Test fixtures for install testing
- **docs/learned/ci/** - CI documentation

## Verification

1. Run unit tests for affected modules:
   - `uv run pytest tests/unit/core/test_version_check.py`
   - `uv run pytest tests/unit/cli/test_uvx_detection.py`
2. Run `make fast-ci` to ensure no regressions