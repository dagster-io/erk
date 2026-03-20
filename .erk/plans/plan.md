# Plan: Remove monkeypatching from test_graphite_command.py via gateway injection

## Context

`test_graphite_command.py` has 6 tests that monkeypatch `RealErkInstallation` and `shutil.which` on the `cli_group` module. This violates erk's fake-driven testing pattern (documented in `docs/learned/testing/monkeypatch-vs-fakes-decision.md`). The root cause: `_is_graphite_available` and `_set_show_hidden_from_context` in `cli_group.py` directly construct `RealErkInstallation()` and call `shutil.which("gt")` in their `ctx.obj is None` fallback path.

The fix: inject `ErkInstallation` and `Shell` gateways into `ErkCommandGroup`, and use them in the fallback paths.

## Files to modify

1. `packages/erk-shared/src/erk_shared/cli_group.py` — add gateway injection to ErkCommandGroup
2. `tests/unit/cli/test_graphite_command.py` — replace all monkeypatching with constructor injection

## Implementation

### Step 1: Add gateway params to `ErkCommandGroup.__init__`

In `cli_group.py`, add `installation` and `shell` to the constructor:

```python
from erk_shared.gateway.erk_installation.abc import ErkInstallation
from erk_shared.gateway.shell.abc import Shell

class ErkCommandGroup(click.Group):
    def __init__(
        self,
        grouped: bool = True,
        *,
        installation: ErkInstallation | None = None,
        shell: Shell | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**cast(dict[str, Any], kwargs))
        self.grouped = grouped
        self._installation = installation
        self._shell = shell
```

When `None` (all production call sites), the fallback path constructs `RealErkInstallation()` / calls `shutil.which` on demand — identical to current behavior. When provided (tests), uses the injected fakes.

### Step 2: Convert `_is_graphite_available` to a method

Move from standalone function to method on `ErkCommandGroup`, using stored gateways:

```python
def _is_graphite_available(self, ctx: click.Context) -> bool:
    if ctx.obj is not None:
        return not isinstance(ctx.obj.graphite, GraphiteDisabled)
    installation = self._installation if self._installation is not None else RealErkInstallation()
    if installation.config_exists():
        config = installation.load_config()
        if config.use_graphite:
            if self._shell is not None:
                return self._shell.get_installed_tool_path("gt") is not None
            return shutil.which("gt") is not None
    return False
```

Update the call in `format_commands` (line 127): `self._is_graphite_available(ctx)`.

### Step 3: Update `_set_show_hidden_from_context` method

Already a method on `ErkCommandGroup`. Update its fallback path:

```python
def _set_show_hidden_from_context(self, ctx: click.Context) -> None:
    if ctx.obj is not None:
        config = getattr(ctx.obj, "global_config", None)
        if config is not None and getattr(config, "show_hidden_commands", False):
            _set_ctx_show_hidden(ctx, value=True)
        return
    installation = self._installation if self._installation is not None else RealErkInstallation()
    if installation.config_exists():
        config = installation.load_config()
        if config.show_hidden_commands:
            _set_ctx_show_hidden(ctx, value=True)
```

### Step 4: Remove dead code

`_get_show_hidden_from_context` (line 30-44 in `cli_group.py`) is dead code — never called within the module. The method `_set_show_hidden_from_context` duplicates its logic. Remove it.

Also remove the now-unused module-level `_is_graphite_available` function (it's been converted to a method).

### Step 5: Rewrite tests

Replace all 6 monkeypatch tests in `test_graphite_command.py` with constructor injection.

**Before** (example — `test_is_graphite_available_falls_back_to_config_when_ctx_obj_is_none`):
```python
def test_...(monkeypatch: MonkeyPatch) -> None:
    class MockErkInstallation: ...
    monkeypatch.setattr(cli_group_module, "RealErkInstallation", MockErkInstallation)
    monkeypatch.setattr(cli_group_module.shutil, "which", lambda cmd: "/usr/bin/gt")
    assert _is_graphite_available(click_ctx) is True
```

**After**:
```python
def test_...() -> None:
    installation = FakeErkInstallation(config=GlobalConfig(..., use_graphite=True, ...))
    shell = FakeShell(installed_tools={"gt": "/usr/bin/gt"})
    group = ErkCommandGroup(grouped=False, installation=installation, shell=shell)
    click_ctx = click.Context(click.Command("test"))
    click_ctx.obj = None
    assert group._is_graphite_available(click_ctx) is True
```

**Tests to convert** (6 total):
- `test_is_graphite_available_falls_back_to_config_when_ctx_obj_is_none` — needs installation + shell
- `test_is_graphite_available_returns_false_when_config_disabled_and_ctx_obj_none` — needs installation only
- `test_is_graphite_available_returns_false_when_gt_not_installed_and_ctx_obj_none` — needs installation + shell (with no gt)
- `test_is_graphite_available_returns_false_when_no_config_and_ctx_obj_none` — needs installation (with no config)
- `test_graphite_command_visible_when_help_shown_without_ctx_obj` — needs installation + shell passed to `@click.group(cls=ErkCommandGroup, installation=..., shell=...)`
- `test_graphite_command_hidden_when_help_shown_without_ctx_obj_and_config_disabled` — needs installation passed to group

**Update imports**: Remove `from pytest import MonkeyPatch`, add `FakeErkInstallation` and `FakeShell` imports. Remove `_is_graphite_available` from import (now a method, not a standalone function).

**Tests that DON'T change** (already clean):
- Lines 83-102: test `_is_graphite_available` with `ctx.obj` present — need to be updated to call via group instance since function is now a method, but no monkeypatching change needed.

### Step 6: Note — `help_formatter.py` (out of scope)

`src/erk/cli/help_formatter.py` has the same pattern: `_get_show_hidden_from_context` directly constructs `RealErkInstallation()`. That's a `CommandWithHiddenOptions` class (different from `ErkCommandGroup`). Same fix pattern applies but it's separate scope.

## Verification

1. Run `pytest tests/unit/cli/test_graphite_command.py` — all tests pass
2. Run `pytest tests/unit/cli/test_alias.py` — no regressions in other cli_group consumers
3. Run `ruff check` + `ty check` — no lint/type errors
4. Verify zero `monkeypatch` references remain in `test_graphite_command.py`
