# Plan: Add `anthropic_api_fast_path` GlobalConfig Setting

## Context

The `FallbackPromptExecutor` currently always tries the Anthropic API first (direct SDK call) before falling back to the CLI executor. This is used for branch slug generation, commit message generation, and PR address summaries. The user wants a configuration setting to control this behavior, defaulting to **off** (no API fast path).

## Changes

### 1. Add field to `GlobalConfig` (`packages/erk-shared/src/erk_shared/context/types.py`)

Add `anthropic_api_fast_path: bool = False` to the `GlobalConfig` frozen dataclass (after the other defaulted bool fields).

Update `GlobalConfig.test()` factory to include the new parameter with default `False`.

### 2. Update load logic (`packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py`)

In `load_config()` (~line 73), add:
```python
anthropic_api_fast_path=bool(data.get("anthropic_api_fast_path", False)),
```

In `save_config()` (~line 139), add:
```python
doc["anthropic_api_fast_path"] = config.anthropic_api_fast_path
```

### 3. Gate the FallbackPromptExecutor wiring (`src/erk/core/context.py`, ~line 660-671)

When `global_config.anthropic_api_fast_path` is `False`, skip `FallbackPromptExecutor` and use the CLI executor directly:

```python
if global_config is not None and global_config.anthropic_api_fast_path:
    from erk.core.anthropic_prompt_executor import AnthropicApiPromptExecutor
    from erk.core.fallback_prompt_executor import FallbackPromptExecutor
    prompt_executor: PromptExecutor = FallbackPromptExecutor(
        api_executor=AnthropicApiPromptExecutor(),
        cli_executor=cli_executor,
    )
else:
    prompt_executor = cli_executor
```

### 4. Update tests

- `tests/integration/test_real_global_config.py`: Add a test for roundtrip of `anthropic_api_fast_path` and verify default is `False`.
- `tests/integration/test_real_global_config.py`: Update `test_global_config_test_factory_method` to assert `anthropic_api_fast_path is False`.

### 5. Update doc (`docs/learned/architecture/globalconfig-field-addition.md`)

Add `anthropic_api_fast_path` to the "Current Fields" list.

## Files to Modify

- `packages/erk-shared/src/erk_shared/context/types.py` — add field + test factory
- `packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py` — load/save
- `src/erk/core/context.py` — gate FallbackPromptExecutor
- `tests/integration/test_real_global_config.py` — tests
- `docs/learned/architecture/globalconfig-field-addition.md` — doc update

## Verification

1. Run `uv run pytest tests/integration/test_real_global_config.py` — all config roundtrip tests pass
2. Run `uv run pytest tests/core/test_fallback_prompt_executor.py` — existing tests still pass
3. Verify `erk` CLI still works with default config (no API fast path)
4. Manually set `anthropic_api_fast_path = true` in `~/.erk/config.toml` and verify API path is used
