---
title: Code Conventions
read_when:
  - "naming functions or variables"
  - "creating CLI commands"
  - "naming Claude artifacts"
  - "moving code between packages"
  - "creating imports"
  - "creating immutable classes or frozen dataclasses"
  - "implementing an ABC with abstract properties"
tripwires:
  - action: "writing `__all__` to a Python file"
    warning: "Re-export modules are forbidden. Import directly from where code is defined."
  - action: "adding --force flag to a CLI command"
    warning: 'Always include -f as the short form. Pattern: @click.option("-f", "--force", ...)'
  - action: "adding a function with 5+ parameters"
    warning: "Load `dignified-python` skill first. Use keyword-only arguments (add `*` after first param). Exception: ABC/Protocol method signatures and Click command callbacks."
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

## Variable Naming by Type

| Type                  | Convention               | Example                          |
| --------------------- | ------------------------ | -------------------------------- |
| Issue numbers (`int`) | `_id` suffix             | `objective_id`, `plan_id`        |
| Issue objects         | No suffix or `_issue`    | `objective`, `plan_issue`        |
| String identifiers    | `_identifier` or `_name` | `plan_identifier`, `branch_name` |

**Rationale:** When a variable holds an integer ID (like a GitHub issue number), the `_id` suffix makes the type immediately clear. This distinguishes `objective_id: int` (an issue number) from `objective: ObjectiveInfo` (an object).

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

## Speculative Feature Pattern

For features that may be removed, use this pattern for easy reversal:

### 1. Feature Constant at Module Top

```python
# SPECULATIVE: feature-name - set to False to disable
ENABLE_FEATURE_NAME = True
```

### 2. Guard Call Sites with the Constant

```python
# SPECULATIVE: feature-name - description
if ENABLE_FEATURE_NAME:
    do_speculative_thing()
```

### 3. Document in Module Docstring

```python
"""Module description.

SPECULATIVE: feature-name (objective #XXXX)
This feature is speculative. Set ENABLE_FEATURE_NAME to False to disable.
Grep for "SPECULATIVE: feature-name" to find all related code.
"""
```

### Usage

| Action               | Command                                    |
| -------------------- | ------------------------------------------ |
| **To disable**       | Set constant to `False`                    |
| **To find all code** | `grep -r "SPECULATIVE: feature-name" src/` |
| **To remove**        | Delete the module and guarded blocks       |

## AI-Generated Commit Messages

When using AI-generated commit messages (e.g., via `/erk:git-pr-push`), observe these constraints:

### Forbidden Elements

| Element            | Example                         | Reason                |
| ------------------ | ------------------------------- | --------------------- |
| Claude attribution | `🤖 Generated with Claude Code` | Noise, not meaningful |
| Metadata headers   | `---\ntool: claude\n---`        | Not standard format   |
| Excessive emoji    | `✨🚀🎉 Added feature`          | Distracting           |

### Required Elements

| Element                 | Example                                  | Reason                  |
| ----------------------- | ---------------------------------------- | ----------------------- |
| Component-level summary | `Add user authentication to API`         | Clear scope             |
| Key changes (max 5)     | `- Add login endpoint\n- Add JWT tokens` | Scannable               |
| Closes reference        | `Closes #123`                            | Auto-close linked issue |

### Example: Good Commit Message

```
Add user authentication to API

Key changes:
- Add /login endpoint with JWT token generation
- Add /logout endpoint with token invalidation
- Add middleware for token validation
- Update user model with password hashing

Closes #123
```

## Immutable Classes

### Frozen Dataclasses (Default)

For simple immutable data, use frozen dataclasses with plain field names:

```python
@dataclass(frozen=True)
class PRNotFound:
    pr_number: int
    branch: str | None = None
```

**Never use underscore-prefixed fields** like `_message` with pass-through properties. If a Protocol requires a `message` property, a frozen dataclass field named `message` satisfies it:

```python
# ❌ WRONG: Unnecessary underscore pattern
@dataclass(frozen=True)
class GitHubAPIFailed:
    _message: str

    @property
    def message(self) -> str:
        return self._message

# ✅ CORRECT: Plain field satisfies Protocol
@dataclass(frozen=True)
class GitHubAPIFailed:
    message: str
```

### Slots-Based Classes (For ABC with Abstract Properties)

When implementing an ABC that defines abstract **properties** (not methods), frozen dataclasses create a conflict: you can't have both a dataclass field and a property with the same name.

In this case, use a slots-based class with underscore-prefixed internal fields:

```python
class LocalSessionSource(SessionSource):
    """Implements SessionSource ABC which has abstract properties."""

    __slots__ = ("_session_id", "_path")

    _session_id: str
    _path: str | None

    def __init__(self, *, session_id: str, path: str | None = None) -> None:
        self._session_id = session_id
        self._path = path

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def path(self) -> str | None:
        return self._path
```

**Key points:**

- Constructor uses clean names (`session_id=`), not underscore-prefixed (`_session_id=`)
- Internal slots use underscores (`_session_id`) to avoid shadowing properties
- Immutability is by convention (underscore prefix signals "don't mutate"), not runtime enforcement
- No need for `__setattr__` overrides or `object.__setattr__()` complexity
