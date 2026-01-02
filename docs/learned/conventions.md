---
title: Code Conventions
read_when:
  - "naming functions or variables"
  - "creating CLI commands"
  - "naming Claude artifacts"
  - "moving code between packages"
  - "creating imports"
tripwires:
  - action: "writing `__all__` to a Python file"
    warning: "Re-export modules are forbidden. Import directly from where code is defined."
  - action: "adding --force flag to a CLI command"
    warning: "Always include -f as the short form. Pattern: @click.option(\"-f\", \"--force\", ...)"
---

# Code Conventions

This document defines naming and code organization conventions for the erk codebase.

## Code Naming

| Element             | Convention         | Example                          |
| ------------------- | ------------------ | -------------------------------- |
| Functions/variables | `snake_case`       | `create_worktree`, `branch_name` |
| Classes             | `PascalCase`       | `WorktreeManager`, `GitOps`      |
| Constants           | `UPPER_SNAKE_CASE` | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |
| CLI commands        | `kebab-case`       | `erk create`, `erk wt list`      |

## Claude Artifacts

All files in `.claude/` (commands, skills, agents, hooks) MUST use `kebab-case`.

**Examples:**

- ✅ `/my-command` (correct)
- ❌ `/my_command` (wrong - uses underscore)

**Exception:** Python scripts within artifacts may use `snake_case` (they're code, not artifacts).

## Brand Names

Use proper capitalization for brand names:

- **GitHub** (not Github)
- **Graphite** (not graphite)
- **erk** (always lowercase, even at start of sentence)

## Worktree Terminology

Use "root worktree" (not "main worktree") to refer to the primary git worktree created with `git init`. This ensures "main" unambiguously refers to the branch name, since trunk branches can be named either "main" or "master".

In code, use the `is_root` field to identify the root worktree.

## CLI Command Organization

Plan verbs are top-level (create, get, implement), worktree verbs are grouped under `erk wt`, stack verbs under `erk stack`. This follows the "plan is dominant noun" principle for ergonomic access to high-frequency operations.

See [CLI Development](cli/) for the complete decision framework.

## CLI Flag Conventions

All `--force` flags must have `-f` as the short form. This provides consistent UX across all commands.

**Pattern:**

```python
@click.option("-f", "--force", is_flag=True, help="...")
```

## Import Conventions

### No Re-exports for Internal Code

**Never create re-export modules for backwards compatibility.** This is private, internal software—we can change imports freely.

When moving code between packages:

- ✅ **Update all imports** to point directly to the new location
- ❌ **Don't create re-export files** that import from new location and re-export

**Example:** When moving `markers.py` from `erk/core/` to `erk_shared/scratch/`:

```python
# ❌ WRONG: Creating a re-export file at erk/core/markers.py
from erk_shared.scratch.markers import (
    PENDING_EXTRACTION_MARKER,
    create_marker,
    delete_marker,
)

# ✅ CORRECT: Update all consumers to import directly
from erk_shared.scratch.markers import PENDING_EXTRACTION_MARKER, create_marker
```

**Why:** Re-exports add indirection, make the codebase harder to navigate, and create maintenance burden. Since this is internal code, we don't need backwards compatibility—just update the imports.

### Import from Definition Site

Always import from where the code is defined, not through re-export layers:

- ✅ `from erk_shared.scratch.markers import create_marker`
- ❌ `from erk.core.markers import create_marker` (if that's a re-export)
