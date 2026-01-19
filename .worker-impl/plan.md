# Plan: Eliminate Re-exports from `__init__.py` Files

## Summary

Audit found **12 `__init__.py` files** with re-exports violating the dignified-python standard. These create duplicate import paths. Fix by:
1. Updating all callsites to use canonical imports
2. Emptying the `__init__.py` files

## Files with Re-exports

### erk-shared package (9 files)

| File | Symbols | Canonical Source |
|------|---------|------------------|
| `packages/erk-shared/src/erk_shared/core/__init__.py` | 29 symbols | `claude_executor`, `codespace_registry`, `fakes`, `plan_list_service`, `planner_registry`, `script_writer` |
| `packages/erk-shared/src/erk_shared/context/__init__.py` | `ErkContext` | `context.context` |
| `packages/erk-shared/src/erk_shared/github/issues/__init__.py` | 6 symbols | `abc`, `real`, `fake`, `dry_run`, `types` |
| `packages/erk-shared/src/erk_shared/prompt_executor/__init__.py` | 2 symbols | `abc` |
| `packages/erk-shared/src/erk_shared/gateway/gt/__init__.py` | 3 symbols | `abc`, `types`, `real` |
| `packages/erk-shared/src/erk_shared/gateway/gt/operations/__init__.py` | 5 symbols | `finalize`, `land_pr`, `pre_analysis`, `preflight`, `squash` |
| `packages/erk-shared/src/erk_shared/gateway/shell/__init__.py` | 5 symbols | `abc`, `fake`, `real` |
| `packages/erk-shared/src/erk_shared/gateway/completion/__init__.py` | 3 symbols | `abc`, `fake`, `real` |
| `packages/erk-shared/src/erk_shared/github_admin/__init__.py` | 3 symbols | `abc`, `fake` |

### erk package (3 files)

| File | Symbols | Canonical Source |
|------|---------|------------------|
| `src/erk/artifacts/__init__.py` | 2 symbols | `artifact_health` |
| `src/erk/tui/sorting/__init__.py` | 4 symbols | `types`, `logic` |
| `src/erk/core/display/__init__.py` | 2 symbols | `abc`, `real` |

## Callsite Impact

| Package | Affected Files | Primary Consumers |
|---------|----------------|-------------------|
| `erk_shared.context` | ~28 files | Test files for exec scripts |
| `erk_shared.github.issues` | ~30 files | Integration tests, dashboard commands |
| `erk_shared.prompt_executor` | ~5 files | Context modules |
| `erk_shared.core` | ~1 file | `src/erk/core/context.py` |
| Others | ~10 files | Various |

**Total: ~64 files need import updates**

## Implementation Steps

### Phase 1: High-impact packages (erk-shared)

1. **`erk_shared.context`** - Update 28 test files
   - Change: `from erk_shared.context import ErkContext`
   - To: `from erk_shared.context.context import ErkContext`

2. **`erk_shared.github.issues`** - Update 30 files
   - `GitHubIssues` → `from erk_shared.github.issues.abc import GitHubIssues`
   - `RealGitHubIssues` → `from erk_shared.github.issues.real import RealGitHubIssues`
   - `FakeGitHubIssues` → `from erk_shared.github.issues.fake import FakeGitHubIssues`
   - `DryRunGitHubIssues` → `from erk_shared.github.issues.dry_run import DryRunGitHubIssues`
   - `IssueInfo`, `CreateIssueResult` → `from erk_shared.github.issues.types import ...`

3. **`erk_shared.prompt_executor`** - Update 5 files
   - Change: `from erk_shared.prompt_executor import PromptExecutor`
   - To: `from erk_shared.prompt_executor.abc import PromptExecutor`

4. **`erk_shared.core`** - Update 1 file (`src/erk/core/context.py`)
   - Split imports to canonical sources

5. **`erk_shared.gateway.gt`** - Update callsites
   - `GtKit` → `from erk_shared.gateway.gt.abc import GtKit`
   - `RealGtKit` → `from erk_shared.gateway.gt.real import RealGtKit`
   - `CommandResult` → `from erk_shared.gateway.gt.types import CommandResult`

6. **`erk_shared.gateway.gt.operations`** - Update callsites
   - Each function from its own module

7. **`erk_shared.gateway.shell`** - Update callsites
   - `Shell` → `from erk_shared.gateway.shell.abc import Shell`
   - etc.

8. **`erk_shared.gateway.completion`** - Update callsites

9. **`erk_shared.github_admin`** - Update callsites

### Phase 2: erk package

10. **`src/erk/artifacts/__init__.py`** - Update callsites
11. **`src/erk/tui/sorting/__init__.py`** - Update callsites
12. **`src/erk/core/display/__init__.py`** - Update callsites

### Phase 3: Clean up `__init__.py` files

After all callsites updated, empty each `__init__.py` file (remove all re-exports).

## Verification

1. Run `make fast-ci` after each phase to catch import errors immediately
2. Run `make all-ci` after completion for full validation
3. Verify no remaining imports from package-level `__init__.py` with grep

## Notes

- Use `libcst-refactor` agent for batch import updates where possible
- Some files may have multiple re-export imports that need splitting
- The `from X import Y as Y` pattern is only acceptable for plugin entry points (none of these qualify)