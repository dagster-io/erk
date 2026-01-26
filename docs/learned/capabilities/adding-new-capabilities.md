---
title: Adding New Capabilities
read_when:
  - "adding reminder capabilities"
  - "creating new capability types"
  - "debugging capability registration"
tripwires:
  - action: "using `is_reminder_installed()` in hook check"
    warning: "Capability class MUST be defined in reminders/ folder AND registered in registry.py @cache tuple. Incomplete registration causes silent hook failures."
---

# Adding New Capabilities

Capabilities in erk follow a 3-file pattern. This guide covers how to add new capability types, with emphasis on the reminder capability pattern.

## The 3-File Pattern

Adding a new capability requires changes to 3 files:

| File                                    | Purpose                                      |
| --------------------------------------- | -------------------------------------------- |
| `src/erk/capabilities/<type>/<name>.py` | Define the capability class                  |
| `src/erk/core/capabilities/registry.py` | Register capability in `_all_capabilities()` |
| `user_prompt_hook.py`                   | Hook checks for installed capabilities       |

## Example: Adding a Reminder Capability

### Step 1: Define the Capability Class

Create `src/erk/capabilities/reminders/my_reminder.py`.

See `src/erk/capabilities/reminders/devrun.py` for the canonical pattern. Reminder capabilities require only two properties:

- `reminder_name` - The marker file name
- `description` - Human-readable description

### Step 2: Register in Registry

In `src/erk/core/capabilities/registry.py`:

1. Add import at top
2. Add instance to the `_all_capabilities()` tuple

### Step 3: Hook Integration

The `user_prompt_hook.py` uses `is_reminder_installed()` to check if capabilities are active. For reminder capabilities, this check is automatic via the `ReminderCapability` base class.

## Registration Checklist

When adding a new capability:

- [ ] Class defined in appropriate folder (`reminders/` for reminders)
- [ ] Class imported in `registry.py`
- [ ] Instance added to `_all_capabilities()` tuple
- [ ] Hook integration tested (capability actually fires)

## Silent Failure Modes

Capabilities can fail silently if registration is incomplete:

| Missing Step                    | Symptom                                 |
| ------------------------------- | --------------------------------------- |
| Class file not created          | Import error in registry                |
| Not registered in `registry.py` | `is_reminder_installed()` returns False |
| Wrong `reminder_name` return    | Hook checks wrong marker file           |

## Testing Capability Registration

```bash
# List all capabilities
erk init capability list

# Check if specific capability is installed
erk init capability status my-reminder
```

## Capability Types

| Type     | Base Class           | Purpose                            |
| -------- | -------------------- | ---------------------------------- |
| Reminder | `ReminderCapability` | Context injection in prompts       |
| Skill    | `Capability`         | Skill file management              |
| Hook     | `Capability`         | Hook installation/configuration    |
| Workflow | `Capability`         | GitHub Actions workflow management |

## Related Documentation

- [Erk Hooks](../hooks/erk.md) - How hooks consume capability state
- [Capability System Architecture](../architecture/capability-system.md) - Full capability system docs
