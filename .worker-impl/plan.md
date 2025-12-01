# Eliminate `__all__` Re-exports and Update Imports to Canonical Locations

## Overview

Remove all 14 `__all__` re-export patterns and update ~52 files to import from canonical source locations instead of re-export facades.

## Changes by Category

### 1. Delete `src/erk/core/plan_store/` Shim Files (4 files)

These files exist solely to re-export from `erk_shared.plan_store`. Delete them entirely:

- `src/erk/core/plan_store/types.py`
- `src/erk/core/plan_store/store.py`
- `src/erk/core/plan_store/github.py`
- `src/erk/core/plan_store/fake.py`

**Update `src/erk/core/plan_store/__init__.py`**: Remove the docstring referencing the deleted submodules (keep as empty namespace marker or delete if no longer needed).

**Update 13 files** - change imports from `erk.core.plan_store.*` to `erk_shared.plan_store.*`:

| File                                                     | Change                                                                |
| -------------------------------------------------------- | --------------------------------------------------------------------- |
| `src/erk/cli/commands/implement.py`                      | `erk.core.plan_store.types` → `erk_shared.plan_store.types`           |
| `src/erk/core/context.py`                                | `erk.core.plan_store.{github,store,fake}` → `erk_shared.plan_store.*` |
| `src/erk/cli/commands/plan/list_cmd.py`                  | `erk.core.plan_store.types` → `erk_shared.plan_store.types`           |
| `tests/commands/test_dash_workflow_runs.py`              | `erk.core.plan_store.types` → `erk_shared.plan_store.types`           |
| `tests/commands/test_implement.py`                       | `erk.core.plan_store.{fake,types}` → `erk_shared.plan_store.*`        |
| `tests/commands/test_top_level_commands.py`              | `erk.core.plan_store.{fake,types}` → `erk_shared.plan_store.*`        |
| `tests/commands/test_dash.py`                            | `erk.core.plan_store.types` → `erk_shared.plan_store.types`           |
| `tests/commands/plan/test_get.py`                        | `erk.core.plan_store.{fake,types}` → `erk_shared.plan_store.*`        |
| `tests/commands/plan/test_close.py`                      | `erk.core.plan_store.{fake,types}` → `erk_shared.plan_store.*`        |
| `tests/commands/plan/test_log.py`                        | `erk.core.plan_store.{fake,types}` → `erk_shared.plan_store.*`        |
| `tests/unit/plan_store/test_fake_plan_store.py`          | `erk.core.plan_store.{fake,types}` → `erk_shared.plan_store.*`        |
| `tests/integration/test_plan_repo_root.py`               | `erk.core.plan_store.{fake,types}` → `erk_shared.plan_store.*`        |
| `tests/integration/plan_store/test_github_plan_store.py` | `erk.core.plan_store.{github,types}` → `erk_shared.plan_store.*`      |

### 2. Remove `__all__` from `erk_shared` Package Aggregations (3 files)

Modify these `__init__.py` files to remove `__all__` and all re-export imports. Keep them as empty namespace markers (or with minimal docstring):

- `packages/erk-shared/src/erk_shared/integrations/gt/__init__.py`
- `packages/erk-shared/src/erk_shared/integrations/erk_wt/__init__.py`
- `packages/erk-shared/src/erk_shared/github/issues/__init__.py`

**Update ~39 files** with imports from these aggregations. Redirect to specific submodules:

**Canonical source mapping:**
| Import | Canonical Source |
|--------|------------------|
| `GtKit`, `GitGtKit`, `GitHubGtKit` | `erk_shared.integrations.gt.abc` |
| `RealGtKit`, `RealGitGtKit`, `RealGitHubGtKit` | `erk_shared.integrations.gt.real` |
| `FakeGtKitOps`, `FakeGitGtKitOps`, `FakeGitHubGtKitOps` | `erk_shared.integrations.gt.fake` |
| `CommandResult`, `GitState`, `GitHubState` | `erk_shared.integrations.gt.types` |
| `ErkWtKit`, `IssueData`, `IssueParseResult`, `WorktreeCreationResult` | `erk_shared.integrations.erk_wt.abc` |
| `RealErkWtKit` | `erk_shared.integrations.erk_wt.real` |
| `FakeErkWtKit` | `erk_shared.integrations.erk_wt.fake` |
| `GitHubIssues` | `erk_shared.github.issues.abc` |
| `RealGitHubIssues` | `erk_shared.github.issues.real` |
| `FakeGitHubIssues` | `erk_shared.github.issues.fake` |
| `DryRunGitHubIssues` | `erk_shared.github.issues.dry_run` |
| `IssueInfo`, `CreateIssueResult` | `erk_shared.github.issues.types` |

### 3. Delete `dot-agent-kit` Shim Files (7 files)

These shims have NO consumers in the codebase. Delete them entirely:

- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/ops.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/real_ops.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/submit_branch.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/pr_update.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/prompts.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/ops.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/real_ops.py`

**Update documentation**: `docs/agent/kit-code-architecture.md` references these shims as examples - update or remove those references.

## Execution Order

1. **Update all imports first** (Categories 1 & 2 import updates)
2. **Delete shim files** (Categories 1 & 3 file deletions)
3. **Clean up `__init__.py` files** (Category 2 aggregation cleanups)
4. **Update documentation**
5. **Run tests** to verify no breakage

## Files to Modify (Complete List)

### Deletions (11 files)

- `src/erk/core/plan_store/types.py`
- `src/erk/core/plan_store/store.py`
- `src/erk/core/plan_store/github.py`
- `src/erk/core/plan_store/fake.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/ops.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/real_ops.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/submit_branch.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/pr_update.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/prompts.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/ops.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/real_ops.py`

### `__init__.py` Cleanups (4 files)

- `src/erk/core/plan_store/__init__.py` - Remove docstring about submodules
- `packages/erk-shared/src/erk_shared/integrations/gt/__init__.py` - Remove `__all__` and imports
- `packages/erk-shared/src/erk_shared/integrations/erk_wt/__init__.py` - Remove `__all__` and imports
- `packages/erk-shared/src/erk_shared/github/issues/__init__.py` - Remove `__all__` and imports

### Import Updates (~52 files)

See detailed lists in sections above.
