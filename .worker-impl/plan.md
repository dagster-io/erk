# Plan: Convert --hooks to Required Capability

## Summary
Replace the `--hooks` flag on `erk init` with a "required" capability that auto-installs during init. Add infrastructure for marking capabilities as required.

## Design

### New Capability Property
Add `required` property to `Capability` ABC:
- `required = True`: Auto-install during `erk init`, don't prompt user
- `required = False` (default): Optional, install via `erk init capability add`

### HooksCapability
Create `HooksCapability` with `required = True` that:
- `is_installed()`: Checks both `has_user_prompt_hook()` AND `has_exit_plan_hook()`
- `install()`: Uses existing `add_erk_hooks()`, `write_claude_settings()`

## Files to Modify

### 1. `src/erk/core/capabilities/base.py`
Add `required` property to ABC with default `False`:
```python
@property
def required(self) -> bool:
    """If True, auto-install during erk init."""
    return False
```

### 2. `src/erk/core/capabilities/hooks.py` (NEW)
Create `HooksCapability` class following `ErkBashPermissionsCapability` pattern:
- Reuse `has_user_prompt_hook`, `has_exit_plan_hook`, `add_erk_hooks` from `claude_settings.py`
- Override `required` to return `True`

### 3. `src/erk/core/capabilities/registry.py`
- Add import for `HooksCapability`
- Add `HooksCapability()` to `_all_capabilities()`
- Add helper function: `list_required_capabilities() -> list[Capability]`

### 4. `src/erk/cli/commands/init/main.py`
- Remove `offer_claude_hook_setup()` function (lines 320-360)
- Remove call to `offer_claude_hook_setup()` in interactive flow (line 655)
- Add new logic after artifact sync: install all required capabilities
- Remove `hooks_only` parameter from `run_init()`

### 5. `src/erk/cli/commands/init/__init__.py`
- Remove `--hooks` flag (lines 18-23)
- Remove `hooks_only` parameter from function signature

### 6. Tests
- `tests/commands/setup/init/test_hooks.py`: Update/remove tests for `--hooks` flag
- Create `tests/core/capabilities/test_hooks_capability.py`: Unit tests for HooksCapability

## Implementation Order

1. Add `required` property to `Capability` ABC
2. Create `HooksCapability` with `required = True`
3. Add `list_required_capabilities()` helper to registry
4. Modify `erk init` to auto-install required capabilities
5. Remove `--hooks` flag and related code
6. Update tests

## Verification

1. Run `erk init` on a fresh repo - hooks should auto-install without prompting
2. Check capabilities display shows hooks as installed
3. Run tests: `uv run pytest tests/commands/setup/init/ tests/core/capabilities/`