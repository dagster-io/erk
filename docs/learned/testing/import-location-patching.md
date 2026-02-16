---
description: Patches must target import location, not definition site
read_when:
  - test patches failing after module refactoring
  - AttributeError in monkeypatch statements
  - function moved between modules
tripwires:
  - action: "removing imports from a module"
    warning: "Grep test files for monkeypatch statements targeting this module. All patches must be converted to parameter injection or retargeted."
last_audited: "2026-02-16 00:00 PT"
audit_result: new
---

# Import Location for Test Patches

## The Rule

When patching functions in tests, target the **import location** (where the function is called), not the **definition site** (where the function is defined).

## Example

Function `get_bundled_claude_dir()` defined in `erk.artifacts.artifact_health` but imported and called in `erk.cli.commands.artifact.check`:

```python
# CORRECT - patch at import location
mocker.patch("erk.cli.commands.artifact.check.get_bundled_claude_dir")

# WRONG - patch at definition site
mocker.patch("erk.artifacts.artifact_health.get_bundled_claude_dir")
```

## Why

Python's import system binds names at import time. The call site uses its local binding, not the original module's.

## When Functions Move

After refactoring:

1. Find where function is now imported
2. Update patches to target new import location
3. Or convert to parameter injection (preferred)
