# Plan: Remove `__all__` Re-exports from claude_installation

> **Replans:** #4700

## What Changed Since Original Plan

- Previous PR #4702 was closed without merging
- All 28 files still need updating - no work has been applied
- The original plan was accurate; this is a fresh implementation

## Investigation Findings

### Current State

The `__init__.py` still has `__all__` with 8 re-exported symbols. This violates the "No Re-exports" convention in `docs/learned/conventions.md`.

### Import Mapping

| Symbol | New Import Path |
|--------|-----------------|
| `ClaudeInstallation` | `.abc` |
| `FoundSession` | `.abc` |
| `Session` | `.abc` |
| `SessionContent` | `.abc` |
| `RealClaudeInstallation` | `.real` |
| `FakeClaudeInstallation` | `.fake` |
| `FakeProject` | `.fake` |
| `FakeSessionData` | `.fake` |

## Implementation Steps

### Step 1: Update erk-shared Package (7 files)

1. `packages/erk-shared/src/erk_shared/context/context.py` - ClaudeInstallation from .abc
2. `packages/erk-shared/src/erk_shared/context/factories.py` - RealClaudeInstallation from .real
3. `packages/erk-shared/src/erk_shared/context/helpers.py` - ClaudeInstallation from .abc
4. `packages/erk-shared/src/erk_shared/context/testing.py` - ClaudeInstallation from .abc, FakeClaudeInstallation from .fake
5. `packages/erk-shared/src/erk_shared/extraction/raw_extraction.py` - ClaudeInstallation from .abc
6. `packages/erk-shared/src/erk_shared/extraction/session_context.py` - ClaudeInstallation from .abc
7. `packages/erk-shared/src/erk_shared/extraction/session_selection.py` - Session from .abc

### Step 2: Update Production Code (8 files)

1. `src/erk/cli/commands/cc/session/list_cmd.py` - ClaudeInstallation from .abc
2. `src/erk/cli/commands/cc/session/show_cmd.py` - ClaudeInstallation from .abc
3. `src/erk/cli/commands/exec/scripts/find_project_dir.py` - ClaudeInstallation from .abc
4. `src/erk/cli/commands/exec/scripts/list_sessions.py` - ClaudeInstallation, Session from .abc
5. `src/erk/cli/commands/init/main.py` - RealClaudeInstallation from .real
6. `src/erk/core/capabilities/statusline.py` - ClaudeInstallation from .abc, RealClaudeInstallation from .real
7. `src/erk/core/context.py` - ClaudeInstallation from .abc, Real from .real, Fake from .fake
8. `src/erk/core/health_checks.py` - ClaudeInstallation from .abc

### Step 3: Update Test Files (13 files)

1. `tests/commands/cc/test_session_list.py` - Fake types from .fake
2. `tests/commands/cc/test_session_show_agent_types.py` - Fake types from .fake
3. `tests/commands/cc/test_session_show.py` - Fake types from .fake
4. `tests/core/test_health_checks.py` - FakeClaudeInstallation from .fake
5. `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py` - FakeClaudeInstallation from .fake
6. `tests/unit/cli/commands/exec/scripts/test_find_project_dir.py` - FakeClaudeInstallation from .fake
7. `tests/unit/cli/commands/exec/scripts/test_list_sessions.py` - Fake types from .fake
8. `tests/unit/cli/commands/exec/scripts/test_plan_save_to_issue.py` - Fake types from .fake
9. `tests/unit/cli/commands/exec/scripts/test_plan_update_issue.py` - FakeClaudeInstallation from .fake
10. `tests/unit/core/test_capabilities.py` - FakeClaudeInstallation from .fake
11. `tests/unit/core/test_health_checks_statusline.py` - FakeClaudeInstallation from .fake
12. `tests/unit/fakes/test_fake_claude_installation.py` - FoundSession from .abc, Fake types from .fake
13. `tests/unit/sessions/test_discovery.py` - Fake types from .fake

### Step 4: Clean Up `__init__.py`

Replace `packages/erk-shared/src/erk_shared/extraction/claude_installation/__init__.py` with:

```python
"""Claude installation abstraction layer.

This package provides a domain-driven interface for Claude installation operations.
All filesystem details are hidden behind the ClaudeInstallation ABC.

Import directly from submodules:
- .abc: ClaudeInstallation, Session, FoundSession, SessionContent
- .real: RealClaudeInstallation
- .fake: FakeClaudeInstallation, FakeProject, FakeSessionData
"""
```

## Verification

1. Run `make fast-ci` to verify all tests pass
2. Verify no package-level imports remain:
   ```bash
   rg "from erk_shared.extraction.claude_installation import" --type py
   ```
   Should return zero results.