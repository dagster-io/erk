# Plan: Remove `__all__` Re-exports from claude_installation

## Problem

The `claude_installation/__init__.py` uses `__all__` for re-exporting, which violates the "No Re-exports" convention in `docs/learned/conventions.md`. Every symbol should have exactly one canonical import path.

## Scope

**28 files** import from `erk_shared.extraction.claude_installation` (package-level) and need to be updated to import directly from submodules.

## Import Mapping

| Symbol | Current Import | New Import |
|--------|----------------|------------|
| `ClaudeInstallation` | `...claude_installation` | `...claude_installation.abc` |
| `FoundSession` | `...claude_installation` | `...claude_installation.abc` |
| `Session` | `...claude_installation` | `...claude_installation.abc` |
| `SessionContent` | `...claude_installation` | `...claude_installation.abc` |
| `FakeClaudeInstallation` | `...claude_installation` | `...claude_installation.fake` |
| `FakeProject` | `...claude_installation` | `...claude_installation.fake` |
| `FakeSessionData` | `...claude_installation` | `...claude_installation.fake` |
| `RealClaudeInstallation` | `...claude_installation` | `...claude_installation.real` |

## Implementation Steps

### Step 1: Update Production Code (8 files)

1. `src/erk/cli/commands/cc/session/show_cmd.py` - ClaudeInstallation → .abc
2. `src/erk/cli/commands/cc/session/list_cmd.py` - ClaudeInstallation → .abc
3. `src/erk/cli/commands/init/main.py` - RealClaudeInstallation → .real
4. `src/erk/cli/commands/exec/scripts/find_project_dir.py` - ClaudeInstallation → .abc
5. `src/erk/cli/commands/exec/scripts/list_sessions.py` - ClaudeInstallation, Session → .abc
6. `src/erk/core/capabilities/statusline.py` - check imports, route to .abc/.fake/.real
7. `src/erk/core/context.py` - ClaudeInstallation → .abc, FakeClaudeInstallation → .fake, RealClaudeInstallation → .real
8. `src/erk/core/health_checks.py` - ClaudeInstallation → .abc

### Step 2: Update erk-shared Package (7 files)

1. `packages/erk-shared/src/erk_shared/context/helpers.py` - ClaudeInstallation → .abc
2. `packages/erk-shared/src/erk_shared/context/testing.py` - ClaudeInstallation → .abc, FakeClaudeInstallation → .fake
3. `packages/erk-shared/src/erk_shared/context/context.py` - ClaudeInstallation → .abc
4. `packages/erk-shared/src/erk_shared/context/factories.py` - RealClaudeInstallation → .real
5. `packages/erk-shared/src/erk_shared/extraction/raw_extraction.py` - ClaudeInstallation → .abc
6. `packages/erk-shared/src/erk_shared/extraction/session_selection.py` - Session → .abc
7. `packages/erk-shared/src/erk_shared/sessions/discovery.py` - already uses .abc (verify)

### Step 3: Update Test Files (13 files)

1. `tests/unit/sessions/test_discovery.py` - FakeClaudeInstallation, FakeProject, FakeSessionData → .fake
2. `tests/unit/fakes/test_fake_claude_installation.py` - multiple imports → .abc, .fake
3. `tests/unit/core/test_capabilities.py` - FakeClaudeInstallation → .fake
4. `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py` - FakeClaudeInstallation → .fake
5. `tests/unit/cli/commands/exec/scripts/test_list_sessions.py` - check imports
6. `tests/unit/cli/commands/exec/scripts/test_plan_save_to_issue.py` - check imports
7. `tests/unit/cli/commands/exec/scripts/test_plan_update_issue.py` - FakeClaudeInstallation → .fake
8. `tests/unit/cli/commands/exec/scripts/test_find_project_dir.py` - FakeClaudeInstallation → .fake
9. `tests/core/test_health_checks.py` - FakeClaudeInstallation → .fake
10. `tests/unit/core/test_health_checks_statusline.py` - FakeClaudeInstallation → .fake
11. `tests/commands/cc/test_session_list.py` - check imports
12. `tests/commands/cc/test_session_show_agent_types.py` - check imports
13. `tests/commands/cc/test_session_show.py` - check imports

### Step 4: Clean Up `__init__.py`

Replace `packages/erk-shared/src/erk_shared/extraction/claude_installation/__init__.py` with a minimal docstring-only module:

```python
"""Claude installation abstraction layer.

This package provides a domain-driven interface for Claude installation operations.
Import from submodules directly:
- abc: ClaudeInstallation, Session, SessionContent, FoundSession
- fake: FakeClaudeInstallation, FakeProject, FakeSessionData
- real: RealClaudeInstallation
"""
```

## Verification

1. Run `make fast-ci` to verify all tests pass
2. Verify no imports from `erk_shared.extraction.claude_installation` (package-level) remain:
   ```bash
   rg "from erk_shared.extraction.claude_installation import" --type py
   ```
   Should return zero results.