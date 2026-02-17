# Plan: `--backend` CLI Flag for Runtime Override

**Part of Objective #7159, Step 2.4**

## Context

Erk supports multiple agent backends (Claude, Codex) configured in `~/.erk/config.toml`. Currently there's no way to override the backend at runtime without editing the config file. This step adds a `--backend` global CLI flag so users can run `erk --backend codex <command>` to override for a single invocation.

## Approach: Override at GlobalConfig level in CLI entry point

After `create_context()`, use `dataclasses.replace()` to bake the backend override into `GlobalConfig.interactive_agent.backend` before storing on `ctx.obj`. This means all downstream consumers (`resolve_backend()`, `with_overrides()`, `launch_interactive()`) see the override automatically with zero changes.

**Why this approach over alternatives:**
- Adding `backend_override` to `with_overrides()` only covers interactive launch commands, not capability commands — two parallel code paths
- Storing as a separate `ErkContext` field splits the source of truth, requiring every consumer to check two places

## Changes

### 1. `src/erk/cli/cli.py` — Add `--backend` global flag

Add `--backend` Click option to the `cli()` group (alongside existing `--debug`):
```python
@click.option(
    "--backend",
    type=click.Choice(["claude", "codex"], case_sensitive=False),
    default=None,
    help="Override agent backend (claude or codex)",
)
```

After `create_context()`, apply the override:
```python
# Apply backend override: CLI flag > env var > config file
effective_backend = backend or os.environ.get("ERK_BACKEND")
if effective_backend is not None:
    ctx.obj = _apply_backend_override(ctx.obj, effective_backend)
```

Add `_apply_backend_override()` helper that uses `dataclasses.replace()` on the frozen `GlobalConfig` and `InteractiveAgentConfig`. When `global_config` is None (pre-init), create a minimal GlobalConfig with the requested backend.

Also support `ERK_BACKEND` env var (validated to `"claude"` or `"codex"`).

### 2. `tests/unit/cli/test_backend_override.py` — New test file

Tests for `_apply_backend_override`:
- Override works when `global_config` exists (normal case) — backend changed, other fields preserved
- Override works when `global_config` is None (pre-init case)
- `with_overrides()` preserves an already-overridden backend (codex config stays codex through override chain)

### 3. `tests/unit/core/test_interactive_claude_config.py` — Add backend preservation test

Add test confirming `with_overrides()` preserves `backend="codex"` through override calls (ensures the `backend=self.backend` passthrough in `with_overrides()` works correctly for non-default backends).

## Files Modified

| File | Change |
|------|--------|
| `src/erk/cli/cli.py` | Add `--backend` option, `_apply_backend_override()`, env var support |
| `tests/unit/cli/test_backend_override.py` | New: unit tests for override function |
| `tests/unit/core/test_interactive_claude_config.py` | Add backend preservation test |

## Files NOT Modified (by design)

| File | Reason |
|------|--------|
| `packages/erk-shared/src/erk_shared/context/types.py` | No changes needed — override baked in before consumption |
| `src/erk/cli/commands/init/capability/backend_utils.py` | `resolve_backend()` reads from config which is already overridden |
| `packages/erk-shared/src/erk_shared/gateway/agent_launcher/real.py` | Backend validation already handles codex (raises helpful error) |

## Key Patterns to Follow

- **None-preservation**: CLI flag None means "not specified" → check env var → fall back to config
- **Frozen dataclass mutation**: Use `dataclasses.replace()` (not `object.__setattr__`)
- **Click.Choice**: Handles validation of CLI flag values automatically
- **Env var validation**: Manual validation needed since Click doesn't handle env vars through Choice

## Verification

1. Run unit tests: `pytest tests/unit/cli/test_backend_override.py tests/unit/core/test_interactive_claude_config.py`
2. Run existing backend tests: `pytest tests/unit/cli/commands/init/capability/test_backend_utils.py`
3. Run type checker on modified files
4. Manual smoke test: `erk --backend codex init capability list` should show capabilities filtered for codex backend