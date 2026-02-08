---
title: Adding New Capabilities
read_when:
  - "adding reminder capabilities"
  - "creating new capability types"
  - "debugging capability registration"
  - "understanding why capabilities don't appear in hooks"
tripwires:
  - action: "capability not appearing in hooks or CLI"
    warning: "Class MUST be imported AND instantiated in registry.py _all_capabilities() tuple. Missing registration causes silent failures—class exists but is never discovered."
  - action: "creating a new capability type with custom installation logic"
    warning: "Don't subclass Capability directly unless needed. Use SkillCapability or ReminderCapability for 90% of cases—they handle state management automatically."
last_audited: "2026-02-08"
audit_result: edited
---

# Adding New Capabilities

Capabilities are optional features installed via `erk init capability add`. The system is designed around base classes that handle most implementation details automatically.

## Why Use Base Classes

Erk provides specialized base classes because capability installation follows predictable patterns:

<!-- Source: src/erk/core/capabilities/skill_capability.py, SkillCapability -->
<!-- Source: src/erk/core/capabilities/reminder_capability.py, ReminderCapability -->

- **ReminderCapability**: Stores state in `.erk/state.toml` under `[reminders]` section. No files created.
- **SkillCapability**: Installs skill files from bundled artifacts. Delegates to artifact sync system.

Both base classes handle `is_installed()`, `install()`, `uninstall()`, and state tracking. Subclasses provide only `name` and `description`.

## Registration: The Critical Step

<!-- Source: src/erk/core/capabilities/registry.py, _all_capabilities -->

Registration requires **two steps** in `registry.py`:

1. **Import** the capability class at module level
2. **Instantiate** it in the `_all_capabilities()` tuple

**Why both?** The registry uses a `@cache` decorator on `_all_capabilities()`. Import verifies the module loads; instantiation makes the capability discoverable.

### Anti-Pattern: Import Without Instantiation

```python
# registry.py
from erk.capabilities.reminders.my_reminder import MyReminderCapability  # ✓ Imported

@cache
def _all_capabilities() -> tuple[Capability, ...]:
    return (
        DevrunReminderCapability(),
        # MyReminderCapability() MISSING  # ✗ Never instantiated
    )
```

**Result:** CLI commands won't list it. Hooks won't check it. `get_capability("my-reminder")` returns `None`. The class exists but is invisible to the system.

## Decision Table: Which Base Class?

| If you're adding...                        | Extend                | Implement Properties      |
| ------------------------------------------ | --------------------- | ------------------------- |
| Context injection (hook reminder)          | `ReminderCapability`  | `reminder_name`           |
| Skill file installation                    | `SkillCapability`     | `skill_name`              |
| GitHub workflow with actions               | `Capability` (direct) | Full interface (see base) |
| `.claude/` artifact with custom sync logic | `Capability` (direct) | Full interface (see base) |
| Settings.json modification                 | `Capability` (direct) | Full interface (see base) |
| State.toml section (not reminders)         | `Capability` (direct) | Full interface (see base) |

Use base classes when possible. They eliminate boilerplate and ensure consistent behavior.

## Example: Reminder Capability

<!-- Source: src/erk/capabilities/reminders/devrun.py, DevrunReminderCapability -->

Reminder capabilities store state in `.erk/state.toml` and enable hook-based context injection. The base class handles all state management.

See `DevrunReminderCapability` for the canonical minimal implementation—two properties, zero methods.

**Key insight:** `reminder_name` determines:

- CLI name: `{reminder_name}-reminder`
- State key in `.erk/state.toml`: `reminders.installed = ["devrun"]`
- Hook detection: hooks query by `reminder_name`

## Example: Skill Capability

<!-- Source: src/erk/capabilities/skills/dignified_python.py, DignifiedPythonCapability -->

Skill capabilities install files from bundled artifacts. The base class delegates to the artifact sync system.

See `DignifiedPythonCapability`—same two-property pattern as reminders.

## Example: Direct Capability Subclass

<!-- Source: src/erk/capabilities/workflows/erk_impl.py, ErkImplWorkflowCapability -->

Direct `Capability` subclass is needed when:

- Installing multiple files/directories with custom logic
- Modifying configuration files (like `settings.json`)
- Complex preflight checks

See `ErkImplWorkflowCapability` for the full pattern: implements all abstract methods, calls `add_installed_capability()` during `install()`, declares `managed_artifacts` for artifact detection.

## Silent Failure Modes

| Failure                                             | Symptom                                          | Root Cause                               |
| --------------------------------------------------- | ------------------------------------------------ | ---------------------------------------- |
| Capability not in `erk init capability list`        | Missing from registry tuple                      | Forgot instantiation step                |
| Hook doesn't fire after install                     | Wrong `reminder_name` or not checking state file | Name mismatch between class and hook     |
| Doctor doesn't check artifacts                      | Missing `managed_artifacts` declaration          | Artifact detection relies on registry    |
| Install succeeds but `is_installed()` returns False | State tracking not called                        | Forgot `add_installed_capability()` call |

## Testing Checklist

After adding a capability:

```bash
# Verify registration
erk init capability list | grep my-capability

# Install and verify
erk init capability add my-capability
erk init capability list my-capability  # Should show "Installed: Yes"

# For reminders: check state file
cat .erk/state.toml  # Should have reminder_name in [reminders] section

# For skills: verify file installed
ls .claude/skills/my-skill/
```

## Related Topics

- [Capability System Architecture](../architecture/capability-system.md) - Complete system design and tracking
- [Bundled Artifacts System](../architecture/bundled-artifacts.md) - How skills and workflows are sourced
