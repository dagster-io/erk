---
title: Bundled Skill Capabilities
read_when:
  - "registering new bundled skills in the capability system"
  - "understanding how skills are discovered by erk init and erk artifact sync"
  - "debugging missing skill capabilities"
tripwires:
  - action: "adding a new bundled skill to codex_portable_skills()"
    warning: "New bundled skills must be added to bundled_skills() dict AND verified by drift prevention test"
  - action: "creating a skill with custom install logic"
    warning: "Skills with custom install logic need dedicated SkillCapability subclass, not bundled factory"
---

# Bundled Skill Capabilities

Skills bundled in the erk wheel need `SkillCapability` registration to be visible to `erk init` and `erk artifact sync`. Without registration, skills are invisible to the capability system.

## Problem

Skills bundled in the wheel (like `dignified-python`, `fake-driven-testing`) are discovered by `codex_portable_skills()` but had no `SkillCapability` registration. This made them invisible to:

- `erk init` (couldn't install them)
- `erk artifact sync` (couldn't detect drift)
- Capability listing commands

## Solution: Parameterized Factory

Instead of creating individual `SkillCapability` subclasses for each simple skill, a generic `BundledSkillCapability` class and a factory function handle batch registration.

### Components

**`bundled_skills()` function** -- cached dict mapping skill names to descriptions:

```python
@cache
def bundled_skills() -> dict[str, str]:
    return {
        "dignified-python": "Python coding standards...",
        "fake-driven-testing": "5-layer test architecture...",
        # ... 11 total entries
    }
```

**`BundledSkillCapability` class** -- generic SkillCapability that takes name and description as constructor parameters rather than requiring a subclass for each skill.

**`create_bundled_skill_capabilities()` factory** -- creates a list of BundledSkillCapability instances from the `bundled_skills()` dict.

### Registry Splice Pattern

The factory output is unpacked into the capabilities tuple in `src/erk/core/capabilities/registry.py`:

```python
def _all_capabilities() -> tuple[Capability, ...]:
    return (
        LearnedDocsCapability(),
        *create_bundled_skill_capabilities(),  # tuple unpacking
        TripwiresReviewDefCapability(),
        # ...
    )
```

The `*` operator unpacks the list into individual tuple items, keeping the registry declaration clean.

### Import-Time Safety

The `@cache` decorator on `bundled_skills()` defers dict creation to first use, avoiding import-time allocation.

## When to Use Bundled vs Dedicated

| Pattern                              | When to Use                                                            |
| ------------------------------------ | ---------------------------------------------------------------------- |
| Bundled factory (`bundled_skills()`) | Simple skills with no custom install logic                             |
| Dedicated `SkillCapability` subclass | Skills needing custom install behavior (e.g., `LearnedDocsCapability`) |

If a skill just needs to be copied from the wheel to the project, use the bundled factory. If it needs to generate content, check conditions, or perform custom setup during install, create a dedicated subclass.

## Drift Prevention Test

`tests/unit/core/test_capabilities.py` contains `test_all_codex_portable_skills_have_capability()` which verifies every skill in `codex_portable_skills()` has a registered capability. If a new skill is added to the portable skills list without a corresponding capability, this test fails with instructions:

> Add it to bundled_skills() in bundled.py or create a dedicated capability class

## Source Code References

| File                                     | Key Components                                                                      |
| ---------------------------------------- | ----------------------------------------------------------------------------------- |
| `src/erk/capabilities/skills/bundled.py` | `BundledSkillCapability`, `bundled_skills()`, `create_bundled_skill_capabilities()` |
| `src/erk/core/capabilities/registry.py`  | `_all_capabilities()` with tuple unpacking                                          |
| `tests/unit/core/test_capabilities.py`   | Drift prevention test                                                               |

## Related Topics

- [Capability System](../architecture/capability-system.md) -- overall capability architecture
- [Adding New Capabilities](adding-new-capabilities.md) -- step-by-step guide for new capabilities
- [Adding Skills](adding-skills.md) -- how to add skill artifacts
