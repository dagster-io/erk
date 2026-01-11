---
title: Capability System Architecture
read_when:
  - creating new erk init capabilities
  - understanding how erk init works
  - adding installable features
---

# Capability System Architecture

The capability system enables optional features to be installed via `erk init capability add <name>`.

## Core Components

### Base Class (`src/erk/core/capabilities/base.py`)

All capabilities inherit from the `Capability` ABC:

```python
class Capability(ABC):
    # Required properties
    name: str                    # CLI identifier (e.g., "tripwires-review")
    description: str             # Short description for list output
    scope: CapabilityScope       # "project" or "user"
    installation_check_description: str  # What is_installed() checks
    artifacts: list[CapabilityArtifact]  # Files/dirs created

    # Required methods
    is_installed(repo_root: Path | None) -> bool
    install(repo_root: Path | None) -> CapabilityResult

    # Optional
    required: bool = False       # Auto-install during erk init
    preflight(repo_root) -> CapabilityResult  # Pre-flight checks
```

### Registry (`src/erk/core/capabilities/registry.py`)

Hardcoded tuple of all capability instances:

```python
@cache
def _all_capabilities() -> tuple[Capability, ...]:
    return (
        LearnedDocsCapability(),
        DignifiedPythonCapability(),
        # ... more capabilities
    )
```

Query functions:

- `get_capability(name)` - Get by name
- `list_capabilities()` - All capabilities
- `list_required_capabilities()` - Only required=True

### Scopes

**Project Scope**: Requires git repository, installed relative to repo_root

- Examples: learned-docs, dignified-python, erk-hooks

**User Scope**: Can be installed anywhere, relative to home directory

- Example: statusline (modifies ~/.claude/settings.json)

## Capability Types

| Type     | Base Class        | Example                     | Installs                     |
| -------- | ----------------- | --------------------------- | ---------------------------- |
| Skill    | `SkillCapability` | `DignifiedPythonCapability` | .claude/skills/              |
| Workflow | `Capability`      | `DignifiedReviewCapability` | .github/workflows/ + prompts |
| Settings | `Capability`      | `HooksCapability`           | Modifies settings.json       |
| Docs     | `Capability`      | `LearnedDocsCapability`     | docs/learned/                |

## Creating a New Capability

1. Create class in `src/erk/core/capabilities/`
2. Implement required properties and methods
3. Add to `_all_capabilities()` tuple in registry.py
4. Add tests in `tests/core/capabilities/`

## CLI Commands

- `erk init capability list` - Show all capabilities
- `erk init capability check <name>` - Check installation status
- `erk init capability add <name>` - Install capability
