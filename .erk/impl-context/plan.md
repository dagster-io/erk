# Make additional capabilities required and hide them from user-facing lists

## Context

Several bundled skill capabilities are broadly useful and should auto-install silently during `erk init`. Required capabilities should be invisible to users — they're system infrastructure, not optional enhancements. Currently all capabilities (required and optional) appear in `erk init capability list` and the Step 3 output of `erk init`.

## Changes

### 1. `src/erk/capabilities/skills/bundled.py` — make 5 skills required

Add a `_REQUIRED_BUNDLED_SKILLS` frozenset and override `required` on `BundledSkillCapability`:

```python
_REQUIRED_BUNDLED_SKILLS: frozenset[str] = frozenset({
    "erk-diff-analysis",
    "erk-exec",
    "objective",
    "pr-operations",
    "pr-feedback-classifier",
})
```

Override in `BundledSkillCapability`:
```python
@property
def required(self) -> bool:
    return self._skill_name in _REQUIRED_BUNDLED_SKILLS
```

### 2. `src/erk/core/capabilities/registry.py` — add `list_optional_capabilities()`

New function that filters out required capabilities, for use in all user-facing contexts:

```python
def list_optional_capabilities() -> list[Capability]:
    return sorted(
        [c for c in _all_capabilities() if not c.required],
        key=lambda c: c.name,
    )
```

### 3. `src/erk/cli/commands/init/capability/list_cmd.py` — hide required from list

- `_check_all()` (line 112): switch from `list_capabilities()` to `list_optional_capabilities()`
- `_check_capability()` error path (line 51): switch to `list_optional_capabilities()`

### 4. `src/erk/cli/commands/init/capability/add_cmd.py` — hide required from error hint

- Line 45: switch `list_capabilities()` to `list_optional_capabilities()` in the "Available capabilities" error output

### 5. `src/erk/cli/commands/init/capability/remove_cmd.py` — hide required from error hint

- Line 44: switch `list_capabilities()` to `list_optional_capabilities()` in the "Available capabilities" error output

### 6. `src/erk/cli/commands/init/main.py` — hide required from Step 3 display

- Line 682: switch `list_capabilities()` to `list_optional_capabilities()` for the Step 3 "Capabilities:" display

No changes to `list_capabilities()` itself or `list_required_capabilities()` — internal code keeps full access.

## Files to modify

1. `src/erk/capabilities/skills/bundled.py`
2. `src/erk/core/capabilities/registry.py`
3. `src/erk/cli/commands/init/capability/list_cmd.py`
4. `src/erk/cli/commands/init/capability/add_cmd.py`
5. `src/erk/cli/commands/init/capability/remove_cmd.py`
6. `src/erk/cli/commands/init/main.py`

## Verification

- `erk init capability list` should NOT show the 5 newly-required skills, nor any other required capabilities (workflows, hooks, etc.)
- `erk init` Step 3 should only show optional capabilities
- `erk init` still silently auto-installs all required capabilities
- `pytest tests/ -k capability` passes
