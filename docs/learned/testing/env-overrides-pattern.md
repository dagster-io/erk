---
title: env_overrides Pattern for erk_isolated_fs_env
read_when:
  - "writing tests that need custom environment variables"
  - "testing erk init commands that depend on HOME"
  - "using erk_isolated_fs_env fixture with env_overrides"
tripwires:
  - action: "using monkeypatch to set HOME in init command tests"
    warning: "Use erk_isolated_fs_env(runner, env_overrides={'HOME': '{root_worktree}'}) instead."
last_audited: "2026-02-17 00:00 PT"
audit_result: clean
---

# env_overrides Pattern for erk_isolated_fs_env

The `erk_isolated_fs_env` fixture supports an `env_overrides` parameter with template interpolation for setting environment variables in test contexts.

## Fixture Signature

<!-- Source: tests/test_utils/env_helpers.py, erk_isolated_fs_env -->

See `erk_isolated_fs_env()` in `tests/test_utils/env_helpers.py`. Accepts a `CliRunner` and optional `env_overrides: dict[str, str] | None` keyword argument, yielding an `ErkIsolatedFsEnv`.

## Template Interpolation

<!-- Source: tests/test_utils/env_helpers.py, erk_isolated_fs_env template interpolation -->

Values containing `{root_worktree}` are interpolated with the actual root worktree path at runtime. See the template resolution logic in `erk_isolated_fs_env()` in `tests/test_utils/env_helpers.py` — it replaces `{root_worktree}` in override values and applies them via `patch.dict(os.environ, ...)`.

## Usage Pattern

```python
with erk_isolated_fs_env(runner, env_overrides={"HOME": "{root_worktree}"}) as env:
    result = runner.invoke(cli, ["init", ...], env=env.env)
```

This is essential for `erk init` tests where the command reads/writes to `~/.config/erk/` and needs HOME pointing to the test directory.

## Why Not monkeypatch?

The `env_overrides` approach is preferred over `monkeypatch.setenv("HOME", ...)` because:

1. **Scoped to the test context** - environment is restored automatically when the context manager exits
2. **Template interpolation** - `{root_worktree}` resolves to the actual temp directory path
3. **Composable** - works alongside the rest of `erk_isolated_fs_env`'s setup (git init, config, etc.)

## Related Topics

- [Parameter Injection Pattern](parameter-injection-pattern.md) - Broader pattern for test-time dependency injection
- [Monkeypatch Elimination Checklist](monkeypatch-elimination-checklist.md) - Migration guide from monkeypatch to injection
