# Refactor `--dangerous` Flag System → `live_dangerously` Config

## Context

Commands like rebase, address, diverge-fix, and implement accept `--dangerous` / `-d` to pass `--dangerously-skip-permissions` to Claude. Without `-d`, Claude launches but without skip-permissions — meaning it prompts for every tool call. The config `require_dangerous_flag_for_implicitly_dangerous_operations` controls whether omitting `-d` is an error, but even when that gate is disabled, the `dangerous` variable stays `False` so Claude still runs without skip-permissions. There's a semantic gap: disabling the requirement doesn't actually enable dangerous mode. The user wants dangerous mode to be the default behavior, with a concise config key and an inverse `--safe` flag to opt out when needed.

**Outcome:** Config `live_dangerously: bool = True` (default). `--safe` flag overrides to safe mode. `--dangerous` / `-d` overrides to dangerous mode. `Ensure.resolve_dangerous()` returns the effective bool.

## Step 1: Rename GlobalConfig Field

**File:** `packages/erk-shared/src/erk_shared/context/types.py`

- Line 236: `require_dangerous_flag_for_implicitly_dangerous_operations: bool = True` → `live_dangerously: bool = True`
- `GlobalConfig.test()` factory (~line 244): rename the parameter and pass-through

## Step 2: Rename Schema Field

**File:** `packages/erk-shared/src/erk_shared/config/schema.py`

- Lines 98-106: Replace with:
  ```python
  live_dangerously: bool = Field(
      description="Default to dangerous mode (skip permission prompts). Use --safe to override.",
      json_schema_extra={"level": ConfigLevel.OVERRIDABLE, "cli_key": "live_dangerously"},
  )
  ```
- Also add `cmux_integration` field that's missing from schema (pre-existing gap — schema has 7 fields but GlobalConfig has 8)

## Step 3: Update Config Loading/Saving

**File:** `packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py`

- Line 78-83 (load): `live_dangerously=bool(data.get("live_dangerously", True))`
- Line 143-144 (save): `doc["live_dangerously"] = config.live_dangerously`

## Step 4: Replace `Ensure.dangerous_flag()` → `Ensure.resolve_dangerous()`

**File:** `src/erk/cli/ensure.py`

Remove `dangerous_flag` (lines 122-145). Add:

```python
@staticmethod
def resolve_dangerous(ctx: ErkContext, *, dangerous: bool, safe: bool) -> bool:
    """Resolve effective dangerous mode from flags and config.

    Priority: explicit flags > config default > True.
    """
    if dangerous and safe:
        raise click.UsageError("--dangerous and --safe are mutually exclusive")
    if dangerous:
        return True
    if safe:
        return False
    if ctx.global_config is not None:
        return ctx.global_config.live_dangerously
    return True
```

## Step 5: Update `rebase_cmd.py`

**File:** `src/erk/cli/commands/pr/rebase_cmd.py`

- Add `@click.option("--safe", is_flag=True, help="Disable dangerous mode (permission prompts enabled).")`
- Add `safe: bool` to signature
- Replace `Ensure.dangerous_flag(ctx, dangerous=dangerous)` → `effective_dangerous = Ensure.resolve_dangerous(ctx, dangerous=dangerous, safe=safe)`
- Pass `effective_dangerous` to `executor.execute_interactive(dangerous=effective_dangerous, ...)`
- Update help text: replace old config key reference with `erk config set live_dangerously false`

## Step 6: Update `address_cmd.py`

**File:** `src/erk/cli/commands/pr/address_cmd.py`

- Same pattern as Step 5
- **Fix bug on line 63:** `dangerous=True` hardcoded → `dangerous=effective_dangerous`
- Update help text

## Step 7: Update `diverge_fix_cmd.py`

**File:** `src/erk/cli/commands/pr/diverge_fix_cmd.py`

- Same pattern as Step 5
- Pass `effective_dangerous` to `stream_diverge_fix`
- Update help text

## Step 8: Update `stream_diverge_fix` Signature

**File:** `src/erk/cli/output.py`

- `stream_diverge_fix(executor, worktree_path)` → `stream_diverge_fix(executor, worktree_path, *, dangerous: bool)`
- Line 424: `dangerous=True` → `dangerous=dangerous`

## Step 9: Update `implement_shared.py`

**File:** `src/erk/cli/commands/implement_shared.py`

- In `implement_common_options`, add `--safe` option after `--dangerous`:
  ```python
  fn = click.option("--safe", is_flag=True, default=False,
      help="Disable dangerous mode (overrides live_dangerously config)")(fn)
  ```

## Step 10: Update `implement.py`

**File:** `src/erk/cli/commands/implement.py`

- Add `safe: bool` to `implement()` signature
- After yolo block, add: `effective_dangerous = Ensure.resolve_dangerous(ctx, dangerous=dangerous, safe=safe)`
- Add validation: `if yolo and safe: raise click.ClickException("--yolo and --safe are mutually exclusive")`
- Pass `effective_dangerous` instead of `dangerous` to all downstream calls

## Step 11: Update Tests

| Test File | Changes |
|-----------|---------|
| `packages/erk-shared/tests/unit/config/test_schema.py` | Replace `require_dangerous_flag_for_implicitly_dangerous_operations` → `live_dangerously` in expected field sets and order lists. Add `cmux_integration` to expected fields. Update field counts from 7 → 8. |
| `packages/erk-statusline/tests/test_context.py` | Replace `require_dangerous_flag_for_implicitly_dangerous_operations=True` → `live_dangerously=True` (3 occurrences) |
| `tests/commands/pr/test_rebase.py` | `test_pr_rebase_requires_dangerous_flag`: With `live_dangerously=True` default, command no longer requires flag — test should verify command succeeds without `--dangerous`. Add test: `live_dangerously=False` + no flag → safe mode. Add test: `--safe` overrides `live_dangerously=True`. Add test: `--dangerous --safe` → mutual exclusion error. Update config key references in assertions. |
| `tests/commands/pr/test_address.py` | Same pattern as rebase. Also verify `--safe` causes executor to receive `dangerous=False` (bug fix validation). |
| `tests/commands/pr/test_diverge_fix.py` | Same pattern as rebase. |
| Implement tests | Tests omitting `--dangerous` now get `effective_dangerous=True` from config default. Update expectations or pass `--safe` where safe mode is intended. |

## Step 12: Update Docs

- `docs/learned/reference/cli-flag-patterns.md` — update Ensure pattern, add `--safe`, update config key
- `docs/learned/cli/cli-options-validation.md` — update `Ensure.dangerous_flag` → `Ensure.resolve_dangerous`
- `docs/learned/cli/commands/pr-diverge-fix.md` — add `--safe` flag, update config key

## Verification

1. `uv run pytest tests/commands/pr/test_rebase.py tests/commands/pr/test_address.py tests/commands/pr/test_diverge_fix.py` — dangerous flag tests
2. `uv run pytest packages/erk-shared/tests/unit/config/test_schema.py` — schema tests
3. `uv run pytest packages/erk-statusline/tests/test_context.py` — statusline context tests
4. `uv run pytest tests/commands/implement/` — implement command tests
5. `uv run ruff check src/erk/cli/ensure.py src/erk/cli/commands/pr/ src/erk/cli/commands/implement.py src/erk/cli/commands/implement_shared.py`
6. `uv run ty check src/erk/cli/ensure.py`
7. Manual: `erk config list` should show `live_dangerously` instead of old key
