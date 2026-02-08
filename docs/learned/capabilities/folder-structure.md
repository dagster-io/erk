---
title: Capabilities Folder Structure
read_when:
  - "adding new capability implementations"
  - "deciding where to place capability files"
  - "understanding capability organization"
---

# Capabilities Folder Structure

The capabilities system achieves stability by separating **infrastructure** (rarely changes, in `core/capabilities/`) from **implementations** (frequently changes, in `capabilities/<type>/`).

## Why the Split Exists

The two-directory architecture solves a specific problem: infrastructure code must be stable for all capabilities to function, but new capabilities should be easy to add without touching core infrastructure.

| Layer           | Location                 | Change Frequency | Who Edits     |
| --------------- | ------------------------ | ---------------- | ------------- |
| Infrastructure  | `core/capabilities/`     | Rarely           | Core team     |
| Template bases  | `core/capabilities/*.py` | Rarely           | Core team     |
| Implementations | `capabilities/<type>/`   | Frequently       | Anyone adding |

This separation allows adding a new skill, reminder, or review without modifying `base.py`, `registry.py`, or template classes.

## Placement Decision: Type Folder vs Root

The placement question arises because some capabilities fit templates (skills, reminders, reviews) while others have unique installation logic.

**Use type folders** (`skills/`, `reminders/`, `reviews/`, `workflows/`, `agents/`) when:

1. The capability extends a template base class (`SkillCapability`, `ReminderCapability`, `ReviewCapability`)
2. Installation follows a standard pattern (copy skill directory, register hook, etc.)
3. Multiple capabilities of this type exist

**Use root level** (`capabilities/*.py`) when:

1. Installation is complex or multi-step (e.g., `HooksCapability` modifies settings.json)
2. The capability manages multiple artifact types
3. No template pattern exists for this capability's behavior

**Anti-pattern:** Creating a type folder for a single capability. Type folders exist to group similar implementations, not to organize one-offs.

<!-- Source: src/erk/capabilities/hooks.py, HooksCapability class -->
<!-- Source: src/erk/capabilities/skills/dignified_python.py, DignifiedPythonCapability class -->

Examples:

- `HooksCapability` lives at root because it modifies `.claude/settings.json` with hook entries, not copying a directory
- `DignifiedPythonCapability` lives in `skills/` because it extends `SkillCapability` and follows the standard "copy skill directory" pattern

See `HooksCapability` in `src/erk/capabilities/hooks.py` for complex installation logic vs `DignifiedPythonCapability` in `src/erk/capabilities/skills/dignified_python.py` for template-based installation.

## One File Per Capability

Each capability implementation is a single file named after the capability. This differs from Python's typical package-per-module pattern.

**Why this works:**

- **Discoverability**: `grep "class.*Capability"` finds all capabilities
- **Modularity**: File size stays small (most are 50-150 lines)
- **Growth**: Adding capability N+1 doesn't touch files for capabilities 1..N
- **Import clarity**: Dependencies are visible at the top of each file

**Anti-pattern:** Creating a `__init__.py` that imports and re-exports all capabilities. This centralizes import paths, breaking the "one canonical import path" rule.

## Explicit Registry Pattern

<!-- Source: src/erk/core/capabilities/registry.py, _all_capabilities() -->

The registry in `src/erk/core/capabilities/registry.py` instantiates all capabilities in a hardcoded tuple. This is intentional — no auto-discovery.

**Why explicit registration over auto-discovery:**

1. **Initialization order is visible** — some capabilities depend on others being registered first
2. **Import errors fail fast** — typo in capability name causes immediate import failure, not silent omission
3. **Debugging is trivial** — "Is this capability registered?" is a grep, not a filesystem walk
4. **No magic** — the `@cache` decorator makes it clear this runs once

See `_all_capabilities()` in `src/erk/core/capabilities/registry.py` for the registration pattern.

**Trade-off**: Adding a new capability requires editing `registry.py`. This is acceptable because capability additions are infrequent and the explicitness prevents registration bugs.

## Template Base Classes

<!-- Source: src/erk/core/capabilities/skill_capability.py, SkillCapability -->
<!-- Source: src/erk/core/capabilities/reminder_capability.py, ReminderCapability -->
<!-- Source: src/erk/core/capabilities/review_capability.py, ReviewCapability -->

Template base classes (`SkillCapability`, `ReminderCapability`, `ReviewCapability`) implement `Capability` ABC and provide default behavior for common patterns.

**When to use template bases:**

- The capability follows a standard installation pattern (e.g., copy directory, register in settings)
- Subclass only needs to provide metadata (`skill_name`, `description`)
- Default `install()` / `uninstall()` / `is_installed()` behavior is correct

**When to implement `Capability` ABC directly:**

- Installation requires custom logic beyond copying files
- The capability modifies shared files (e.g., `settings.json`)
- Multiple artifacts with different types are installed

See `SkillCapability` in `src/erk/core/capabilities/skill_capability.py` for the template pattern. Compare against `HooksCapability` in `src/erk/capabilities/hooks.py` which implements `Capability` directly.

## Managed Artifacts Declaration

<!-- Source: src/erk/core/capabilities/base.py, managed_artifacts property -->
<!-- Source: src/erk/core/capabilities/registry.py, get_managed_artifacts() -->

Capabilities declare which artifacts they manage via the `managed_artifacts` property. This enables `erk init` to distinguish between erk-managed artifacts (safe to regenerate) and project-specific ones (never touch).

**Why declaration instead of detection:**

- **Authoritative source**: The capability that installs an artifact knows whether it's managed
- **Safe updates**: `erk init capability add` can safely overwrite managed artifacts
- **Prevents accidents**: Won't delete project-specific skills during capability cleanup

See `managed_artifacts` property in `src/erk/core/capabilities/base.py` and `get_managed_artifacts()` in `src/erk/core/capabilities/registry.py` for the implementation pattern.

## Adding a New Capability Checklist

1. **Determine type**: Does it fit skill/reminder/review/workflow/agent pattern?
2. **Choose location**: Type folder if template applies, root if unique installation logic
3. **Create file**: `src/erk/capabilities/<type>/<name>.py` or `src/erk/capabilities/<name>.py`
4. **Implement class**: Extend template base or `Capability` ABC directly
5. **Register**: Add import and instance to `_all_capabilities()` in `registry.py`
6. **Declare managed artifacts**: Add to `managed_artifacts` property if capability owns artifacts

**Critical**: Never skip step 6. Undeclared artifacts will be treated as project-specific, causing confusing behavior during capability updates.

## See Also

- `docs/learned/capabilities/adding-skills.md` — skill-specific creation guide
- `docs/learned/capabilities/adding-new-capabilities.md` — reminder/agent creation guide
- `docs/learned/capabilities/adding-reviews.md` — review definition creation guide
- `docs/learned/capabilities/adding-workflows.md` — workflow creation guide
