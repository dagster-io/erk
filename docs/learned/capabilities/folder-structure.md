---
title: Capabilities Folder Structure
read_when:
  - "adding new capability implementations"
  - "deciding where to place capability files"
  - "understanding capability organization"
---

# Capabilities Folder Structure

The capabilities system separates **infrastructure** (stable, in `core/capabilities/`) from **implementations** (frequently changing, in `capabilities/<type>/`).

## Directory Layout

```
src/erk/
├── core/capabilities/       # Infrastructure (stable)
│   ├── base.py              # ABC and type definitions
│   ├── registry.py          # Capability factory (@cache)
│   ├── *_capability.py      # Template base classes (skill, reminder, review)
│
└── capabilities/            # Implementations (extend here)
    ├── skills/              # Skill capabilities
    ├── reminders/           # Reminder capabilities
    ├── reviews/             # Review capabilities
    ├── workflows/           # Workflow capabilities
    ├── agents/              # Agent capabilities
    └── *.py                 # Standalone capabilities (at root)
```

To see current files in each folder, use `ls src/erk/capabilities/<type>/`.

## Placement Decision Criteria

### When to Use Type Folders

Place capability in a type folder (`skills/`, `reminders/`, `reviews/`, `workflows/`, `agents/`) when:

1. **Template pattern applies**: The capability extends a template base class (`SkillCapability`, `ReminderCapability`, `ReviewCapability`)
2. **Multiple implementations exist**: Two or more capabilities share the same type
3. **Type-specific behavior**: The capability's behavior is defined by its type

### When to Use Root Level

Place capability at root level (`capabilities/*.py`) when:

1. **Unique behavior**: The capability has custom logic that doesn't fit template patterns
2. **Single implementation**: Only one capability of this kind exists
3. **Complex installation**: The capability manages multiple artifacts or has special requirements

## Import Patterns

Import paths follow the directory structure:

- **Type-based capabilities**: `erk.capabilities.<type>.<name>` (e.g., `erk.capabilities.skills.dignified_python`)
- **Standalone capabilities**: `erk.capabilities.<name>` (e.g., `erk.capabilities.hooks`)
- **Base classes**: `erk.core.capabilities.base` for `Capability`, `CapabilityResult`
- **Template classes**: `erk.core.capabilities.<type>_capability` (e.g., `skill_capability`)
- **Registry functions**: `erk.core.capabilities.registry` for `get_capability`, `list_capabilities`

See `src/erk/core/capabilities/registry.py` for concrete import examples.

## Adding a New Capability

1. **Determine type**: Does it fit skill/reminder/review/workflow/agent pattern?
2. **Choose location**: Type folder if template applies, root level if unique
3. **Create file**: One file per capability, named after the capability
4. **Register**: Add import and instance to `registry.py`

See type-specific guides:

- [Adding Skills](adding-skills.md)
- [Adding Reminders](adding-new-capabilities.md)
- [Adding Reviews](adding-reviews.md)
- [Adding Workflows](adding-workflows.md)

## Design Rationale

### Separation of Concerns

| Layer           | Location                            | Changes    | Owner     |
| --------------- | ----------------------------------- | ---------- | --------- |
| Infrastructure  | `core/capabilities/`                | Rarely     | Core team |
| Templates       | `core/capabilities/*_capability.py` | Rarely     | Core team |
| Implementations | `capabilities/<type>/*.py`          | Frequently | Anyone    |

### One File Per Capability

Benefits:

- **Discoverability**: File name matches capability name
- **Modularity**: Each file is small and focused
- **Growth**: Easy to add new capabilities
- **Dependencies**: Clear what each file imports

### Explicit Registry

The registry in `core/capabilities/registry.py` is the single source of truth:

- No auto-discovery magic
- Easier debugging
- Better control over initialization order
