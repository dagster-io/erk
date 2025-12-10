---
title: erk_shared Package
read_when:
  - "sharing code between erk and dot-agent-kit"
  - "deciding where to put new utilities"
  - "moving code between packages"
  - "understanding ErkContext architecture"
  - "using context helpers in CLI commands"
tripwires:
  - action: "importing from erk package in dot-agent-kit"
    warning: "dot-agent-kit cannot import from erk. Use erk_shared for shared code."
---

# erk_shared Package

The `erk_shared` package (`packages/erk-shared/`) contains code shared between:

- `erk` - Main CLI package
- `dot-agent-kit` - Kit CLI commands for Claude Code

## ErkContext Architecture

ErkContext (`erk_shared.context.context`) is the **unified context class** used by both:

- erk CLI commands
- dot-agent-kit CLI commands

Previously there were two separate context classes:

- `DotAgentContext` (in dot-agent-kit) - for kit commands
- `ErkContext` (in erk.core.context) - for erk commands

These have been merged into a single `ErkContext` in `erk_shared`, containing all dependencies needed by both packages. This unification eliminates:

- Duplicate context setup code
- Inconsistent dependency patterns
- Import cycle problems between packages

### Context Fields

```python
@dataclass(frozen=True)
class ErkContext:
    # Gateway integrations (properly typed)
    git: Git
    github: GitHub
    issues: GitHubIssues
    graphite: Graphite
    time: Time
    session_store: ClaudeCodeSessionStore
    plan_store: PlanStore
    prompt_executor: PromptExecutor

    # Shell/CLI integrations
    shell: Shell
    completion: Completion
    feedback: UserFeedback

    # Erk-specific (typed as Any to avoid import cycle)
    claude_executor: Any  # ClaudeExecutor at runtime
    config_store: Any     # ConfigStore at runtime
    script_writer: Any    # ScriptWriter at runtime

    # Paths
    cwd: Path

    # Repository context
    repo: RepoContext | NoRepoSentinel
    project: ProjectContext | None

    # Configuration
    global_config: GlobalConfig | None
    local_config: LoadedConfig

    # Mode flags
    dry_run: bool
    debug: bool
```

## Context Directory Structure

The context system is organized into separate modules for clarity:

```
packages/erk-shared/src/erk_shared/
├── context/           # Unified context system
│   ├── __init__.py    # Public exports
│   ├── context.py     # ErkContext dataclass
│   ├── types.py       # RepoContext, NoRepoSentinel, configs
│   ├── helpers.py     # require_* LBYL helper functions
│   ├── factories.py   # Context creation factories
│   └── testing.py     # Test helpers (context_for_test)
```

### Module Responsibilities

- **context.py**: The `ErkContext` frozen dataclass with all dependency fields
- **types.py**: Supporting types (`RepoContext`, `NoRepoSentinel`, `GlobalConfig`, `LoadedConfig`)
- **helpers.py**: LBYL helper functions for CLI commands (`require_git`, `require_cwd`, etc.)
- **factories.py**: Factory functions for creating ErkContext instances
- **testing.py**: Test utilities including `context_for_test()`

## Context Helpers Pattern (require\_\*)

The `erk_shared.context.helpers` module provides LBYL helper functions for accessing ErkContext dependencies in CLI commands:

- `require_git(ctx)` - Get Git from context
- `require_github(ctx)` - Get GitHub from context
- `require_cwd(ctx)` - Get current working directory
- `require_repo_root(ctx)` - Get repository root path
- `require_project_root(ctx)` - Get project root (or repo root if not in project)
- `require_issues(ctx)` - Get GitHubIssues
- `require_session_store(ctx)` - Get ClaudeCodeSessionStore
- `require_prompt_executor(ctx)` - Get PromptExecutor
- `get_current_branch(ctx)` - Convenience function combining cwd and git

These functions implement the LBYL pattern:

1. Check if context is initialized (LBYL)
2. Print clear error to stderr if not
3. Exit with code 1 on failure
4. Return typed dependency on success

### Usage Example

```python
import click
from erk_shared.context.helpers import require_git, require_cwd

@click.command()
@click.pass_context
def my_command(ctx: click.Context) -> None:
    git = require_git(ctx)
    cwd = require_cwd(ctx)
    branch = git.get_current_branch(cwd)
```

### Why Use Helpers Instead of Direct Access?

- **Eliminates repeated LBYL checks** in every command
- **Provides consistent error messages** across all CLI commands
- **Ensures proper typing** of returned dependencies
- **Handles sentinel values** (e.g., `NoRepoSentinel`) appropriately

Without helpers:

```python
# ❌ WRONG: Repeated LBYL in every command
@click.command()
@click.pass_context
def my_command(ctx: click.Context) -> None:
    if ctx.obj is None:
        click.echo("Error: Context not initialized", err=True)
        raise SystemExit(1)
    if isinstance(ctx.obj.repo, NoRepoSentinel):
        click.echo("Error: Not in a git repository", err=True)
        raise SystemExit(1)
    repo_root = ctx.obj.repo.root
```

With helpers:

```python
# ✅ CORRECT: Use helper function
@click.command()
@click.pass_context
def my_command(ctx: click.Context) -> None:
    repo_root = require_repo_root(ctx)
```

## Decision Framework: Where Does Code Belong?

### Put in erk_shared when:

- Code is used by both erk and dot-agent-kit
- Gateway ABCs and implementations (Git, GitHub, Graphite, etc.)
- Types used across packages (RepoContext, etc.)
- Context system (ErkContext, helpers, factories)
- Shared utilities (output formatting, extraction)

### Put in erk when:

- Code only used by erk CLI
- Erk-specific ABCs that depend on erk internals (ClaudeExecutor, ConfigStore, etc.)
- Erk CLI commands and their helpers
- Erk-specific business logic

### Put in dot-agent-kit when:

- Code only used by kit CLI commands
- Kit-specific utilities
- Kit CLI command implementations

### The "Any" Pattern for Erk-Specific ABCs

Some ABCs cannot be moved to erk_shared because they depend on erk internals (erk-specific types, configuration patterns, etc.). These are typed as `Any` in ErkContext to avoid import cycles:

```python
@dataclass(frozen=True)
class ErkContext:
    # Shared (properly typed)
    git: Git
    github: GitHub

    # Erk-specific (typed as Any to avoid import cycle)
    claude_executor: Any  # ClaudeExecutor at runtime
    config_store: Any     # ConfigStore at runtime
    script_writer: Any    # ScriptWriter at runtime
```

These fields are only accessed by erk code, not dot-agent-kit code. The `TYPE_CHECKING` block provides type hints for static analysis:

```python
if TYPE_CHECKING:
    from erk.core.claude_executor import ClaudeExecutor
    from erk.core.config_store import ConfigStore
```

## Deprecation Pattern for Moved Code

When moving code from one package to erk_shared, provide a compatibility wrapper to enable gradual migration:

```python
# Old location: dot_agent_kit/context_helpers.py
"""Compatibility wrapper for require_github_issues.

DEPRECATED: Import directly from erk_shared.context.helpers instead.
"""
from erk_shared.context.helpers import require_issues

def require_github_issues(ctx: click.Context) -> GitHubIssues:
    """DEPRECATED - use require_issues from erk_shared."""
    return require_issues(ctx)
```

This allows gradual migration without breaking existing code. Once all call sites are migrated, remove the compatibility wrapper.

## When to Use erk_shared

| Situation                 | Location                  |
| ------------------------- | ------------------------- |
| Code only used by erk CLI | `src/erk/`                |
| Code only used by kit CLI | `packages/dot-agent-kit/` |
| Code used by both         | `packages/erk-shared/`    |

## Package Structure

```
packages/erk-shared/src/erk_shared/
├── context/       # Unified context system (ErkContext, helpers, factories)
├── git/           # Git abstraction (abc, real, fake, dry_run)
├── github/        # GitHub integration
├── graphite/      # Graphite integration
├── integrations/  # Shell, completion, feedback, time
├── scratch/       # Scratch storage and markers
├── extraction/    # Extraction utilities
└── output/        # Output formatting
```

## Import Rules

1. **erk can import from erk_shared** ✅
2. **dot-agent-kit can import from erk_shared** ✅
3. **dot-agent-kit cannot import from erk** ❌

## Moving Code to erk_shared

When code needs to be shared:

1. Move the code to appropriate `erk_shared` submodule
2. Update ALL imports to use `erk_shared` directly
3. Do NOT create re-export files (see [No Re-exports Policy](../conventions.md#no-re-exports-for-internal-code))
