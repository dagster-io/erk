# Generalize dangerous flag config to cover all implicitly dangerous commands

## Context

The `--dangerous` flag is required on commands that invoke Claude with `--dangerously-skip-permissions`. Currently, only `rebase` and `reconcile-with-remote` check the `rebase_require_dangerous_flag` config to allow users to opt out. `pr address` has a hardcoded requirement with no config check and no hint about how to disable it (the bug in the screenshot). This change generalizes the config key so all three commands share consistent behavior and error messaging.

## Changes

### 1. Rename config field in schema

**`packages/erk-shared/src/erk_shared/config/schema.py`** (line 98-104)

Rename `rebase_require_dangerous_flag` to `require_dangerous_flag_for_implicitly_dangerous_operations`. Update description to: `"Require --dangerous flag for commands that invoke Claude with skip-permissions"`.

### 2. Rename field in GlobalConfig dataclass

**`packages/erk-shared/src/erk_shared/context/types.py`** (lines 236, 250, 263)

Rename all three occurrences of `rebase_require_dangerous_flag` to `require_dangerous_flag_for_implicitly_dangerous_operations`.

### 3. Update config load/save

**`packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py`** (lines 78, 138)

Update both the `data.get()` key and the `doc[]` key.

### 4. Add `Ensure.dangerous_flag()` helper

**`src/erk/cli/ensure.py`**

Add a static method to centralize the check:

```python
@staticmethod
def dangerous_flag(ctx: ErkContext, *, dangerous: bool) -> None:
    if dangerous:
        return
    require_flag = (
        ctx.global_config is None
        or ctx.global_config.require_dangerous_flag_for_implicitly_dangerous_operations
    )
    if require_flag:
        raise click.UsageError(
            "Missing option '--dangerous'.\n"
            "To disable: erk config set require_dangerous_flag_for_implicitly_dangerous_operations false"
        )
```

### 5. Update all three commands

- **`src/erk/cli/commands/pr/rebase_cmd.py`** — Replace inline check (lines 54-60) with `Ensure.dangerous_flag(ctx, dangerous=dangerous)`. Update docstring config hint.
- **`src/erk/cli/commands/pr/reconcile_with_remote_cmd.py`** — Replace inline check (lines 41-47) with `Ensure.dangerous_flag(ctx, dangerous=dangerous)`. Add `Ensure` import. Update docstring config hint.
- **`src/erk/cli/commands/pr/address_cmd.py`** — Replace hardcoded check (lines 39-40) with `Ensure.dangerous_flag(ctx, dangerous=dangerous)`. Add docstring section about disabling the flag.

### 6. Update tests

- **`tests/commands/pr/test_rebase.py`** — Update assertion string and `GlobalConfig.test()` kwarg
- **`tests/commands/pr/test_reconcile_with_remote.py`** — Same updates
- **`tests/commands/pr/test_address.py`** — Assert config hint in error output; add new test for config override (invoke without `--dangerous` when `require_dangerous_flag_for_implicitly_dangerous_operations=False`)
- **`packages/erk-shared/tests/unit/config/test_schema.py`** — Update field name strings
- **`packages/erk-statusline/tests/test_context.py`** — Update kwarg names

### 7. Update docs

- **`docs/learned/cli/commands/pr-reconcile-with-remote.md`** (line 48) — Update config key name

## Verification

1. Run `uv run pytest tests/commands/pr/test_rebase.py tests/commands/pr/test_reconcile_with_remote.py tests/commands/pr/test_address.py` — all pass
2. Run `uv run pytest packages/erk-shared/tests/unit/config/test_schema.py packages/erk-statusline/tests/test_context.py` — all pass
3. Run `uv run ruff check` and `uv run ty check` — clean
