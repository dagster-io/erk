---
title: Adding Skill Capabilities
read_when:
  - "adding skill capabilities"
  - "creating new skills for external projects"
  - "understanding SkillCapability pattern"
---

# Adding Skill Capabilities

Skills are capabilities that install Claude skill directories to external projects. They follow the `SkillCapability` template pattern.

## Overview

Skill capabilities:

- Install `.claude/skills/<name>/` directories
- Are project-level (require repo context)
- Use the `SkillCapability` base class
- Require only 2 property implementations

## File Location

```
src/erk/capabilities/skills/<skill_name>.py
```

## Implementation

### Step 1: Create the Capability File

Create `src/erk/capabilities/skills/my_skill.py`:

```python
"""MySkillCapability - description of what this skill does."""

from erk.core.capabilities.skill_capability import SkillCapability


class MySkillCapability(SkillCapability):
    """Brief description of the skill."""

    @property
    def skill_name(self) -> str:
        return "my-skill"

    @property
    def description(self) -> str:
        return "Human-readable description for CLI output"
```

### Step 2: Register in Registry

In `src/erk/core/capabilities/registry.py`:

1. Add import at top:

```python
from erk.capabilities.skills.my_skill import MySkillCapability
```

2. Add instance to `_all_capabilities()` tuple:

```python
@cache
def _all_capabilities() -> tuple[Capability, ...]:
    return (
        # ... existing capabilities ...
        MySkillCapability(),
    )
```

### Step 3: Bundle the Skill Content

The skill content must exist in the bundled artifacts:

```
src/erk/bundled/.claude/skills/my-skill/
├── my-skill.md           # Main skill document
└── [additional files]    # Optional supporting files
```

## What SkillCapability Provides

The base class handles:

- `name` property (returns `skill_name`)
- `scope` property (returns `"project"`)
- `artifacts` property (tracks the skill directory)
- `managed_artifacts` property (declares as managed)
- `is_installed()` (checks if directory exists)
- `install()` (copies from bundled artifacts)
- `uninstall()` (removes the directory)

You only implement:

- `skill_name` - The directory name under `.claude/skills/`
- `description` - Human-readable description

## Example: DignifiedPythonCapability

```python
"""DignifiedPythonCapability - Python coding standards skill."""

from erk.core.capabilities.skill_capability import SkillCapability


class DignifiedPythonCapability(SkillCapability):
    """Python coding standards skill (LBYL, modern types, ABCs)."""

    @property
    def skill_name(self) -> str:
        return "dignified-python"

    @property
    def description(self) -> str:
        return "Python coding standards (LBYL, modern types, ABCs)"
```

This installs:

- `.claude/skills/dignified-python/` directory
- CLI name: `dignified-python`

## Testing

```bash
# List capabilities to verify registration
erk init capability list

# Check if installed
erk init capability status my-skill

# Install
erk init capability install my-skill

# Uninstall
erk init capability uninstall my-skill
```

## Checklist

- [ ] File created at `src/erk/capabilities/skills/<name>.py`
- [ ] Class extends `SkillCapability`
- [ ] `skill_name` property returns the skill directory name
- [ ] `description` property returns human-readable text
- [ ] Import added to `registry.py`
- [ ] Instance added to `_all_capabilities()` tuple
- [ ] Bundled content exists at `src/erk/bundled/.claude/skills/<name>/`

## Related Documentation

- [Folder Structure](folder-structure.md) - Where capability files go
- [Adding New Capabilities](adding-new-capabilities.md) - General capability pattern
