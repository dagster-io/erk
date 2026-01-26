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

Create `src/erk/capabilities/skills/my_skill.py`.

See `src/erk/capabilities/skills/dignified_python.py` for the canonical pattern. Skill capabilities require only two properties:

- `skill_name` - The directory name under `.claude/skills/`
- `description` - Human-readable description

### Step 2: Register in Registry

In `src/erk/core/capabilities/registry.py`:

1. Add import at top of file
2. Add instance to the `_all_capabilities()` tuple

See `src/erk/core/capabilities/registry.py` for the registration pattern.

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

## Example

See `src/erk/capabilities/skills/dignified_python.py` for a complete example (~16 lines).

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
