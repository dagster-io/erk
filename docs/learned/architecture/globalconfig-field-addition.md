---
title: GlobalConfig Field Addition Checklist
read_when:
  - "adding a new field to GlobalConfig"
  - "extending erk's global configuration"
  - "adding a user-configurable setting to ~/.erk/config.toml"
tripwires:
  - action: "adding a field to GlobalConfig without updating the test factory"
    warning: "Update GlobalConfig.test() factory method with the new parameter. Tests using GlobalConfig.test() will silently use Python's default value, which may not match production behavior."
---

# GlobalConfig Field Addition Checklist

`GlobalConfig` is a frozen dataclass in `packages/erk-shared/src/erk_shared/context/types.py` that holds user-wide erk settings loaded from `~/.erk/config.toml`.

## Checklist

### 1. Add Field to Frozen Dataclass

```python
# In packages/erk-shared/src/erk_shared/context/types.py
@dataclass(frozen=True)
class GlobalConfig:
    # ... existing fields ...
    new_field: bool = False  # Provide sensible default
```

Fields with defaults go after fields without defaults (Python dataclass rule).

### 2. Update `.test()` Factory

```python
@staticmethod
def test(
    erk_root: Path,
    *,
    # ... existing params ...
    new_field: bool = False,  # Add with same default
) -> GlobalConfig:
    return GlobalConfig(
        # ... existing fields ...
        new_field=new_field,
    )
```

### 3. Update Load Logic

In the config loading code (`packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py`):

```python
# LBYL pattern: check before access
new_field = config_data.get("new_field", False)
```

### 4. Update Save Logic (if applicable)

If the field is writable via CLI commands, update the save path to persist it back to TOML.

### 5. Add Migration (if applicable)

Existing `~/.erk/config.toml` files won't have the new key. The default value in the dataclass handles this automatically for reads. If writes are needed, ensure the save logic creates the key.

## Current Fields

Key fields in GlobalConfig (as of this writing):

- `erk_root: Path` — path to erk installation
- `use_graphite: bool` — whether to use Graphite for PR management
- `shell_setup_complete: bool` — shell integration status
- `github_planning: bool` — GitHub-based planning enabled
- `live_dangerously: bool` — skip safety confirmations
- `show_hidden_commands: bool` — expose hidden CLI commands
- `prompt_learn_on_land: bool` — prompt for learn extraction after landing PRs
- `cmux_integration: bool` — enable cmux workspace creation on PR checkout
- `interactive_agent: InteractiveAgentConfig` — interactive agent settings

## Related Documentation

- [Config Layers](../configuration/config-layers.md) — Full config architecture
- [Conventions](../conventions.md) — Frozen dataclass requirements
