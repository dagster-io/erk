---
title: Pool Config Decoupling
read_when:
  - "reading pool configuration settings"
  - "looking for pool_size or pool_checkout fields in LoadedConfig"
  - "working with PoolConfig or DEFAULT_POOL_SIZE"
tripwires:
  - action: "reading pool_size from LoadedConfig or RepoConfigSchema"
    warning: "Pool fields (pool_size, pool_checkout_commands, pool_checkout_shell) were removed from LoadedConfig. Use erk_slots.config.load_pool_config(repo_root) instead."
  - action: "adding a pool config field to LoadedConfig"
    warning: "Pool config is self-contained in erk_slots. All pool-related config lives in packages/erk-slots/src/erk_slots/config.py. Do not put pool fields in LoadedConfig."
---

# Pool Config Decoupling

## What Changed

Pool configuration was decoupled from the core erk config system. Fields `pool_size`, `pool_checkout_commands`, and `pool_checkout_shell` are no longer part of `LoadedConfig` or `RepoConfigSchema`.

## Pattern: Subsystems Read Their Own Config

The decoupling follows a principle: subsystems read their config independently rather than receiving it via the central `LoadedConfig`. This makes the `erk_slots` package self-contained.

## Implementation

`PoolConfig` dataclass at `packages/erk-slots/src/erk_slots/config.py`:

```python
@dataclass(frozen=True)
class PoolConfig:
    pool_size: int               # Never None; uses DEFAULT_POOL_SIZE as fallback
    pool_checkout_commands: list[str]
    pool_checkout_shell: str | None

DEFAULT_POOL_SIZE = 4
```

`load_pool_config(repo_root)` reads from `.erk/config.toml` `[pool]` section:

- `max_slots` → `pool_size` (fallback: `DEFAULT_POOL_SIZE = 4`)
- `[pool.checkout].commands` → `pool_checkout_commands`
- `[pool.checkout].shell` → `pool_checkout_shell`

Returns `PoolConfig` with defaults if `.erk/config.toml` does not exist or `[pool]` section is absent.

## Usage

```python
from erk_slots.config import load_pool_config

pool_cfg = load_pool_config(repo_root)
pool_size = pool_cfg.pool_size  # int, never None
```

See `packages/erk-slots/src/erk_slots/common.py:43-44` for the canonical usage pattern.

## Related Documentation

- [erk_slots Package Overview](erk-slots-package.md) — Package structure and module breakdown
