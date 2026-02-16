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
last_audited: "2026-02-05 00:00 PT"
audit_result: edited
---

# Code Conventions

This document defines conventions that supplement AGENTS.md. For basic naming (snake_case, PascalCase, kebab-case), Claude artifacts naming, brand names, worktree terminology, and CLI command organization, see AGENTS.md directly.

## Variable Naming by Type

| Type                  | Convention               | Example                          |
| --------------------- | ------------------------ | -------------------------------- |
| Issue numbers (`int`) | `_id` suffix             | `objective_id`, `plan_id`        |
| Issue objects         | No suffix or `_issue`    | `objective`, `plan_issue`        |
| String identifiers    | `_identifier` or `_name` | `plan_identifier`, `branch_name` |

**Rationale:** When a variable holds an integer ID (like a GitHub issue number), the `_id` suffix makes the type immediately clear. This distinguishes `objective_id: int` (an issue number) from `objective: ObjectiveInfo` (an object).

## CLI Flag Conventions

All `--force` flags must have `-f` as the short form. This provides consistent UX across all commands.

```python
@click.option("-f", "--force", is_flag=True, help="...")
```

## Import Conventions

### No Re-exports for Internal Code

**Never create re-export modules for backwards compatibility.** This is private, internal software — we can change imports freely.

When moving code between packages:

- Update all imports to point directly to the new location
- Don't create re-export files that import from the new location and re-export

**Example:** When moving `markers.py` from `erk/core/` to `erk_shared/scratch/`:

```python
# WRONG: Creating a re-export file at old location
from erk_shared.scratch.markers import PENDING_LEARN_MARKER, create_marker, delete_marker

# CORRECT: Update all consumers to import directly
from erk_shared.scratch.markers import PENDING_LEARN_MARKER, create_marker
```

### Import from Definition Site

Always import from where the code is defined, not through re-export layers:

- `from erk_shared.scratch.markers import create_marker`

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

| Action               | Command                                    |
| -------------------- | ------------------------------------------ |
| **To disable**       | Set constant to `False`                    |
| **To find all code** | `grep -r "SPECULATIVE: feature-name" src/` |
| **To remove**        | Delete the module and guarded blocks       |

## Truthiness Simplification

When checking optional values for truthiness, `if x is not None and x:` is redundant. Use just `if x:`.

Both `None` and empty string `""` are falsy in Python. If you want to distinguish between them, use explicit checks:

- `if x is not None:` — true for any non-None value including empty string
- `if x:` — true only for truthy values (non-empty strings, non-zero numbers, etc.)

For parameters like `new_pr: str | None` where `None` means "preserve existing", `""` means "clear", and `"#123"` means "set value": use `if new_pr:` to check for the "set value" case, since both `None` and `""` are falsy.

## AI-Generated Commit Messages

### Forbidden Elements

| Element            | Example                      | Reason                |
| ------------------ | ---------------------------- | --------------------- |
| Claude attribution | `Generated with Claude Code` | Noise, not meaningful |
| Metadata headers   | `---\ntool: claude\n---`     | Not standard format   |
| Excessive emoji    | `Added feature`              | Distracting           |

### Required Elements

| Element                 | Example                                  | Reason                  |
| ----------------------- | ---------------------------------------- | ----------------------- |
| Component-level summary | `Add user authentication to API`         | Clear scope             |
| Key changes (max 5)     | `- Add login endpoint\n- Add JWT tokens` | Scannable               |
| Closes reference        | `Closes #123`                            | Auto-close linked issue |

## Immutable Classes

### Frozen Dataclasses (Default)

For simple immutable data, use frozen dataclasses with plain field names:

```python
@dataclass(frozen=True)
class PRNotFound:
    pr_number: int | None = None
    branch: str | None = None
```

**Never use underscore-prefixed fields** like `_message` with pass-through properties. If a Protocol requires a `message` property, a frozen dataclass field named `message` satisfies it:

```python
# WRONG: Unnecessary underscore pattern
@dataclass(frozen=True)
class GitHubAPIFailed:
    _message: str

    @property
    def message(self) -> str:
        return self._message

# CORRECT: Plain field satisfies Protocol
@dataclass(frozen=True)
class GitHubAPIFailed:
    message: str
```

### Slots-Based Classes (For ABC with Abstract Properties)

When implementing an ABC that defines abstract **properties** (not methods), frozen dataclasses create a conflict: you can't have both a dataclass field and a property with the same name.

In this case, use a slots-based class with underscore-prefixed internal fields. See `LocalSessionSource` in `packages/erk-shared/src/erk_shared/learn/extraction/session_source.py` for the canonical example.

**Key points:**

- Constructor uses clean names (`session_id=`), not underscore-prefixed (`_session_id=`)
- Internal slots use underscores (`_session_id`) to avoid shadowing properties
- Immutability is by convention (underscore prefix signals "don't mutate"), not runtime enforcement
