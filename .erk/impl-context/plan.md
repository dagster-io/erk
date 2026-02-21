# Convert ERK_PLAN_BACKEND to Config Setting

## Context

`ERK_PLAN_BACKEND` is currently an environment variable that controls whether erk uses GitHub issues (`"github"`) or draft PRs (`"draft_pr"`) for plan storage. This is the only plan configuration that lives outside the config system. Converting it to a proper config setting makes it discoverable via `erk config keys/list/get/set` and eliminates the env var contamination problem documented in `docs/learned/testing/environment-variable-isolation.md`.

The env var will remain as a high-priority override for CI workflows (which have no `~/.erk/config.toml`).

## Plan

### 1. Move `PlanBackendType` to `types.py` to avoid circular imports

**File:** `packages/erk-shared/src/erk_shared/context/types.py`
- Add `PlanBackendType = Literal["draft_pr", "github"]`
- Re-export from `packages/erk-shared/src/erk_shared/plan_store/__init__.py` for backward compat

### 2. Add `plan_backend` field to `GlobalConfig`

**File:** `packages/erk-shared/src/erk_shared/context/types.py`
- Add `plan_backend: PlanBackendType = "github"` to `GlobalConfig` dataclass
- Add `plan_backend` parameter to `GlobalConfig.test()` factory

### 3. Add `plan_backend` to config schema

**File:** `packages/erk-shared/src/erk_shared/config/schema.py`
- Add field to `GlobalConfigSchema`:
  ```python
  plan_backend: str = Field(
      description="Plan storage backend: 'github' (issues) or 'draft_pr' (draft PRs)",
      json_schema_extra={"level": ConfigLevel.GLOBAL_ONLY, "cli_key": "plan_backend"},
  )
  ```

### 4. Update config load/save

**File:** `packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py`
- `load_config()`: Read `plan_backend` from TOML, validate to `"github"`/`"draft_pr"`, default `"github"`
- `save_config()`: Write `plan_backend` to TOML (only if non-default, matching the interactive-agent pattern)

### 5. Refactor `get_plan_backend()` to three-tier resolution

**File:** `packages/erk-shared/src/erk_shared/plan_store/__init__.py`

```python
def get_plan_backend(global_config: GlobalConfig | None = None) -> PlanBackendType:
    """Resolve plan backend: env var > config > default ("github")."""
    env_value = os.environ.get("ERK_PLAN_BACKEND")
    if env_value is not None:
        if env_value in ("draft_pr", "github"):
            return cast(PlanBackendType, env_value)
        return "github"
    if global_config is not None:
        return global_config.plan_backend
    return "github"
```

Backward-compatible: callers passing no args get existing behavior.

### 6. Thread `global_config` to CLI callers

Pass `ctx.global_config` (or the in-scope `global_config` variable) to `get_plan_backend()` at these sites:

- `src/erk/core/context.py:612` — `global_config` already in scope
- `src/erk/cli/commands/exec/scripts/plan_save.py:427` — has `ctx`
- `src/erk/cli/commands/wt/create_cmd.py` — has `ctx`
- `src/erk/cli/commands/implement_shared.py` — has `ctx`
- `src/erk/cli/commands/branch/create_cmd.py` — has `ctx`
- `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py` — has `ctx`
- `src/erk/cli/commands/plan/list_cmd.py` — has `ctx`

### 7. Update statusline

**File:** `packages/erk-statusline/src/erk_statusline/statusline.py`
- Load `GlobalConfig` via `RealErkInstallation` (it already does similar for graphite)
- Pass to `get_plan_backend(global_config)`

### 8. Update test context factory

**File:** `packages/erk-shared/src/erk_shared/context/testing.py`
- Add `plan_backend: PlanBackendType = "github"` parameter to `context_for_test()`
- Replace `get_plan_backend()` env var read with the explicit parameter
- Eliminates the env var contamination problem entirely for tests

### 9. Update tests

- `tests/unit/plan_store/test_get_plan_backend.py` — Rewrite to test three-tier resolution (env > config > default)
- `tests/unit/cli/commands/exec/scripts/test_plan_save.py` — Use `plan_backend` param instead of env var fixture
- `tests/commands/test_create.py` — Remove `env_overrides={"ERK_PLAN_BACKEND": "github"}` (default is already "github")
- `packages/erk-statusline/tests/test_statusline.py` — Use config injection instead of env var manipulation

### 10. GitHub workflows — no changes needed

`plan-implement.yml` and `learn.yml` set `ERK_PLAN_BACKEND` env var, which takes priority in the three-tier resolution. CI has no config file and doesn't need one.

## Verification

1. `erk config keys` shows `plan_backend` with description
2. `erk config get plan_backend` returns current value
3. `erk config set plan_backend draft_pr` persists to `~/.erk/config.toml`
4. Setting `ERK_PLAN_BACKEND` env var overrides config value
5. Run full test suite to confirm no regressions
