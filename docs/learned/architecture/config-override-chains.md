---
title: Config Override Chains
read_when:
  - "implementing CLI flags that override config values"
  - "understanding config precedence (local vs global)"
  - "checking local_config vs global_config"
  - "adding new configuration options"
---

# Config Override Chains

How CLI flags and configuration values interact with explicit precedence rules.

## Config Hierarchy

```
CLI flags                    ← HIGHEST PRIORITY (explicit user intent)
    ↓
local_config                 ← Repo-level + local user overrides (merged)
    ↓
global_config                ← User's ~/.erk/config.toml
    ↓
Default behavior             ← LOWEST PRIORITY (hardcoded defaults)
```

## Understanding local_config

The `local_config` object contains merged values from two sources:

1. **Repository config** (`.erk/config.toml` in repo root)
2. **Local user overrides** (`.erk/config.local.toml` in repo root)

Local user overrides take precedence over repository config. This allows per-repo team settings with personal customizations.

## Override Chain Pattern

When checking a config value, follow this explicit chain:

```python
def _should_prompt_learn(ctx: ErkContext) -> bool:
    """Check if learn prompt should be shown, respecting config hierarchy."""
    # Check override chain: local_config overrides global_config
    # local_config contains merged repo+local values (local wins over repo)
    if ctx.local_config.prompt_learn_on_land is not None:
        # Repo or local level override exists
        return ctx.local_config.prompt_learn_on_land

    if ctx.global_config is not None:
        if ctx.global_config.prompt_learn_on_land is not None:
            return ctx.global_config.prompt_learn_on_land

    # Default behavior
    return True
```

## CLI Flag Override

CLI flags always take highest precedence:

```python
@click.command()
@click.option("--skip-learn", is_flag=True, help="Skip learn status check")
def land(skip_learn: bool) -> None:
    # CLI flag overrides all config
    if skip_learn:
        return _land_without_learn_check(...)

    # Fall back to config chain
    if not _should_prompt_learn(ctx):
        return _land_without_learn_check(...)

    # Default: prompt for learn
    return _land_with_learn_check(...)
```

## Common Mistakes

### Checking global_config First

```python
# WRONG - checks global before local
if ctx.global_config and ctx.global_config.setting:
    return ctx.global_config.setting
if ctx.local_config.setting is not None:
    return ctx.local_config.setting
```

```python
# CORRECT - checks local first (higher precedence)
if ctx.local_config.setting is not None:
    return ctx.local_config.setting
if ctx.global_config and ctx.global_config.setting is not None:
    return ctx.global_config.setting
```

### Not Handling None Explicitly

```python
# WRONG - treats None as falsy, skipping global check
if ctx.local_config.setting:  # None is falsy!
    return ctx.local_config.setting

# CORRECT - explicit None check
if ctx.local_config.setting is not None:
    return ctx.local_config.setting
```

## Config Field Guidelines

When adding new config options:

1. **Use Optional types** - Allow None to indicate "not set"
2. **Document defaults** - Make the default behavior explicit
3. **Test all levels** - Test with global-only, local-only, and both set

```python
@dataclass(frozen=True)
class LocalConfig:
    prompt_learn_on_land: bool | None  # None = not set, fall through to global
    plans_repo: str | None             # None = not set, use default
```

## Examples in Codebase

| Config Option | Location | Default |
|---------------|----------|---------|
| `prompt_learn_on_land` | land_cmd.py | True (prompt) |
| `plans_repo` | submit_cmd.py | Current repo |
| `graphite_enabled` | navigation_helpers.py | Auto-detect |
| `interactive_claude` | objective/next_plan_cmd.py | True |

## Related Topics

- [Erk Architecture Patterns](erk-architecture.md) - Context and dependency injection
