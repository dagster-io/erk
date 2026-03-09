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

### 3. Add Field to GlobalConfigSchema

The Pydantic schema in `packages/erk-shared/src/erk_shared/config/schema.py` is the single source of truth for `erk config list/keys/get/set`. Without this step, the field won't appear in any CLI config commands.

```python
# In GlobalConfigSchema class
new_field: bool = Field(
    description="User-friendly description of the setting",
    json_schema_extra={"level": ConfigLevel.GLOBAL_ONLY, "cli_key": "new_field"},
)
```

The `description` field is used by `erk config keys` to show help text. The `cli_key` must match the field name unless the key uses dots (e.g., `interactive_claude.verbose`).

### 5. Update Load Logic

In the config loading code (`packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py`):

```python
# LBYL pattern: check before access
new_field = config_data.get("new_field", False)
```

### 6. Update Save Logic (if applicable)

If the field is writable via CLI commands, update the save path to persist it back to TOML.

### 7. Add Migration (if applicable)

Existing `~/.erk/config.toml` files won't have the new key. The default value in the dataclass handles this automatically for reads. If writes are needed, ensure the save logic creates the key.

## Current Fields

See `GlobalConfig` in `packages/erk-shared/src/erk_shared/context/types.py` for the current field list.

## Related Documentation

- [Config Layers](../configuration/config-layers.md) — Full config architecture
- [Conventions](../conventions.md) — Frozen dataclass requirements
